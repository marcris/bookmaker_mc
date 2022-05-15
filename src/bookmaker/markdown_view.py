#!/usr/bin/env python
# -*- coding: utf8 -*-

import codecs
import gi

from .sync_scroll import SyncScroll

gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')
from gi.repository import Gtk, Gdk, Pango, GtkSource

from mistune import *
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html

from .derivation import plugin_derivation
from .my_extra import plugin_my_extra
from .my_table import plugin_my_table
from .my_footnotes import plugin_my_footnotes

item_no = 0

class MyRenderer(HTMLRenderer):

    def __init__(self):
        super(MyRenderer, self).__init__()

    # render images horizontally centered in the page
    # Note that the css class "center" is defined in each html file (see pre_view.py)
    def image(self, src, alt="", title=None):
        s = '<img src="' + src + '" alt="' + alt + '" class="center"'
        if title:
            s += ' title="' + escape_html(title) + '"'
        return s + ' />'

    def block_image(self, src, alt="", title=None):
        s = '<img src="' + src + '" alt="' + alt + '" class="center"'
        if title:
            s += ' title="' + escape_html(title) + '"'
        return s + ' />'

    # render code blocks highlighted by Pygments
    def block_code(self, code, lang=None):
        if lang == 'mermaid':
            return '<div class="mermaid">'+code+'</div>'
        elif lang:
            lexer = get_lexer_by_name(lang)#, stripall=True)
            formatter = html.HtmlFormatter()
            return highlight(code, lexer, formatter)
        else:
            return escape(code)

    def inline_html(self, html):
        return html # i.e. literal html, not escaped


class MARKDOWNview(Gtk.ScrolledWindow):
    # Define markdown processing with mistune 2 and Pygments

    def __init__(self, toc):
        super(self.__class__, self).__init__()

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        self.is_dirty = False   # Flag belongs to MV

        self.TV = toc  # File details belong to TV
        self.project_directory = self.TV.project_directory
        self.filename_tail = self.TV.filename_tail

        self.textbuffer = GtkSource.Buffer()
        self.textview = GtkSource.View.new_with_buffer(self.textbuffer)
        
        self.tag_bold = self.textbuffer.create_tag("bold",
            weight=Pango.Weight.BOLD)
        self.tag_italic = self.textbuffer.create_tag("italic",
            style=Pango.Style.ITALIC)
        self.tag_underline = self.textbuffer.create_tag("underline",
            underline=Pango.Underline.SINGLE)
        self.tag_found = self.textbuffer.create_tag("found",
            background="yellow")

        self.textbuffer.set_max_undo_levels(9)
        self.textbuffer.set_undo_manager(None)

        self.textbuffer.connect("changed", self.text_modified)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.connect("key_press_event", self.on_key_function)

        # Use a nice monospace font
        fontdesc = Pango.FontDescription("monospace 10")
        self.textview.modify_font(fontdesc)

        self.textview.set_size_request(80, 768)
        self.add(self.textview)

        self.markdown = create_markdown(
            escape=True,
            renderer=MyRenderer(),
            plugins=['url', 'strikethrough', plugin_my_footnotes, plugin_my_table, plugin_derivation, plugin_my_extra],
            # Note: 'derivation' and 'my_extra' added for this application; others are standard
            # in mistune 2.
            # Note 2: Added plugin_my_table in place of the standard one so I can modify the
            # HTML generated.
            # Note 3: Ditto for plugin_my_footnotes.
        )


    def set_PV(self, PV):
        self.PV = PV

    def render_text2html(self, text):
        return self.markdown(text)   # HTMLRenderer is used by default (mistune 2)

    def text_modified(self, widget):
        self.is_dirty = True

        if not self.PV.syncscroll_instance:
            self.PV.syncscroll_instance = SyncScroll(self, self.PV)

        self.PV.reload(self.render_text2html(self.textbuffer.get_property("text")))

        return True

    def save(self, project_directory, filename_tail):
        # The file details supplied are of the file to be saved. TV's file details are not relevant
        try:
            print ("Saving " + project_directory + "/" + filename_tail + ".md")
            with codecs.open(project_directory + "/" + filename_tail + ".md", "w") as f:
                start = self.textbuffer.get_start_iter()
                end = self.textbuffer.get_end_iter()
                f.write(self.textbuffer.get_text(start, end, False))

            # Now write the correspondingly modified xhtml to the book directory
            self.PV.save_rendered_html(project_directory, filename_tail)

        except Exception as e:
            print ("Failed to write modified {0}".format(project_directory + "/" + filename_tail + ".md"))
            print (repr(e))

    def save_if_dirty(self, project_directory, filename_tail):
        # Called when opening a new section
        # The new text goes into the same textbuffer, so changes would be lost.
        if self.is_dirty:
            self.save(project_directory, filename_tail)
            print(f'saved modified {project_directory}/{filename_tail}.md')
        else:
            print(f'Didn\'t bother saving unchanged {project_directory}/{filename_tail}.md')



    def wrap_selection(self, start_wrapper, end_wrapper):
        try:
            (start_iter, end_iter) = self.textbuffer.get_selection_bounds()
        except ValueError:
            print("No selection")
        else:
            end_mark = self.textbuffer.create_mark(None, end_iter)
            self.textbuffer.insert(start_iter, start_wrapper)
            end_iter = self.textbuffer.get_iter_at_mark(end_mark)
            self.textbuffer.insert(end_iter, end_wrapper)
            self.textbuffer.delete_mark(end_mark)
        

 

    def on_key_function(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        # print "Key %s (%d) was pressed" % (keyname, event.keyval)
        # if event.state & gtk.gdk.CONTROL_MASK:
        #     print "Control was being held down"
        # if event.state & gtk.gdk.MOD1_MASK:
        #     print "Alt was being held down"
        # if event.state & gtk.gdk.SHIFT_MASK:
        #     print "Shift was being held down"

        # if event.state & Gdk.ModifierType.CONTROL_MASK:
            # if event.keyval == 122:  # so it was CTRL-z
                # self.textbuffer.undo()

testcode="""
```py
def main(args):
    class Customer(object):

        def __init__(self, name, balance):
            self.name = name        # customer's name (string)
            self.balance = balance  # current balance (float)

        def withdraw(self, amount):
            if amount > self.balance:
                raise ValueError("You don't have that much in your account")
            self.balance -= amount
            return self.balance

        def deposit(self, amount):
            self.balance += amount
            return self.balance
```
"""
