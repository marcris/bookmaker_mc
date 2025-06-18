import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
# pyrefly: ignore  # missing-module-attribute
from gi.repository import Gdk, Gtk, GtkSource, Pango

import os
import mistune

from mistune.renderers import HTMLRenderer
from mistune.util import escape, escape_html
# from pygments import highlight
# from pygments.formatters import html
# from pygments.lexers import get_lexer_by_name
from pygments import highlight
from pygments.lexers import get_lexer_by_name
# pyrefly: ignore  # missing-module-attribute
from pygments.formatters import HtmlFormatter
# from markdown.extensions.codehilite import CodeHiliteExtension
# import MarkdownBlankLine

# pyrefly: ignore  # import-error
import shared

# pyrefly: ignore  # import-error
from derivation import plugin_derivation
# pyrefly: ignore  # import-error
from my_extra import plugin_my_extra
# pyrefly: ignore  # import-error
from my_footnotes import plugin_my_footnotes
# pyrefly: ignore  # import-error
from my_image import plugin_my_image
# pyrefly: ignore  # import-error
from my_table import plugin_my_table
# pyrefly: ignore  # import-error
from my_adm import plugin_my_adm

# pyrefly: ignore  # import-error
from pre_view import PREview
# pyrefly: ignore  # import-error
from sync_scroll import SyncScroll



# class CustomHtmlFormatter(HtmlFormatter):
#     def __init__(self, lang_str='', **options):
#         super().__init__(**options)
#         # lang_str has the value {lang_prefix}{lang}
#         # specified by the CodeHilite's options
#         self.lang_str = lang_str
#
#     def _wrap_code(self, source):
#         yield 0, f'<code class="{self.lang_str}">'
#         yield from source
#         yield 0, '</code>'


class MyHtmlFormatter(HtmlFormatter):
#   @staticmethod

    def __init__(self):
        super().__init__()
        self.wrapcode = False

    def _wrap_code(self, source):
        yield 0, '<code>'
        for i, t in source:
            if i == 1:
                # it's a line of formatted code
                t += '<br>'
            yield i, t
        yield 0, '</code>'

    def wrap(self, source, outfile):
        """
        Wrap the ``source``, which is a generator yielding
        individual lines, in custom generators. See docstring
        for `format`. Can be overridden.
        """
        output = source
#        if self.wrapcode:
        output = self._wrap_div(output)

        return output


class MyRenderer(HTMLRenderer):

    def __init__(self):
        super(MyRenderer, self).__init__()

    def image(self, src, alt="", title=None):
        # render images horizontally centered in the page
        # Note that the css class "center" is defined in each html file (see pre_view.py)
        # Decided I don't like forced center'd images; see below
        # Decided I don't like left-justified ones either; changed the CSS for class="center"
        # to get a 50px margin-left; much better. Should change the class name now?

        # Changed the class name to indent50px; see above
        # print(f'image_src: {src}')
        # print(f'image: {os.path.abspath(src)}')

        # shutil.copy2(os.path.abspath(src), "../../_backup/_images")

        #s = f'<img src="{src}" alt="{alt}" class="indent50px"'
        s = f'<img src="{src}" alt="{alt}" class="center"'
        if title:
            s += f' title="{escape_html(title)}"'
        return f'{s} />'

    def block_image(self, src, alt="", title=None):
        print(f'block_image: {os.path.abspath(src)}')

        self.image(src, alt="", title=None)

    # render code blocks highlighted by Pygments
    # pyrefly: ignore  # bad-override
    def block_code(self, code, lang=None):
        if lang == 'mermaid':
            return f'<div class="mermaid">{code}</div>'
        elif lang:
            lexer = get_lexer_by_name(lang)  # , stripall=True)
            formatter = MyHtmlFormatter()
            return f'{highlight(code, lexer, formatter)}'
        else:
            return escape(code)

    def codespan(self, text):
        return f'<code>{text}</code>'


# class my_block_code_formatter(html.HtmlFormatter):
#     def wrap(self, source):
#         return self._wrap_code(source)
#
#     def _wrap_code(self, source):  # sourcery skip: yield-from
#         # yield 0, '<code>'
#         for i, t in source:
#             # if i == 1:
#             #     # it's a line of formatted code
#             #     t += '<br>'
#             yield i, t
#         # yield 0, '</code>'
#
#     def inline_html(self, html):
#         return html  # i.e. literal html, not escaped


class MARKDOWNview(Gtk.ScrolledWindow):
    def __init__(self):
        # pyrefly: ignore  # invalid-argument
        super(self.__class__, self).__init__()

        # self.clipboard = Gtk.Clipboard.get(Gtk.SELECTION_CLIPBOARD)
        self.preview = PREview()
        self.preview.syncscroll_instance = SyncScroll(self, self.preview)

        self.is_dirty = False  # Flag belongs to MV

        self.textbuffer = GtkSource.Buffer()
        self.textview = GtkSource.View.new_with_buffer(self.textbuffer)

        self.tag_bold = self.textbuffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.tag_italic = self.textbuffer.create_tag("italic", style=Pango.Style.ITALIC)
        self.tag_underline = self.textbuffer.create_tag(
            "underline", underline=Pango.Underline.SINGLE
        )
        self.tag_found = self.textbuffer.create_tag("found", background="yellow")

        self.textbuffer.set_max_undo_levels(9)
        self.textbuffer.set_undo_manager(None)

        self.textbuffer.connect("changed", self.text_modified)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.connect("key_press_event", self.on_key_function)

        # Use a nice monospace font
        fontdesc = Pango.FontDescription.from_string("monospace 10")
        # DeprecationWarning: Gtk.Widget.modify_font is deprecated
        self.textview.modify_font(fontdesc)

        self.textview.set_size_request(80, 768)
        self.add(self.textview)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # self.markdown = markdown.Markdown(extensions=[
        #     'admonition',
        #     'fenced_code',
        #     # BlankLineExtension(),
        #     CodeHiliteExtension(pygments_formatter=CustomHtmlFormatter)
        # ])

        self.markdown = mistune.create_markdown(
            escape=True,
            renderer=MyRenderer(),
            plugins=['url', 'strikethrough', plugin_my_image, plugin_my_footnotes, plugin_my_table, plugin_derivation, plugin_my_extra, plugin_my_adm,],
            # Note: 'derivation' and 'my_extra' added for this application; others are standard
            # in mistune 2.
            # Note 2: Added plugin_my_table in place of the standard one so I can modify the
            # HTML generated.
            # Note 3: Ditto for plugin_my_footnotes.
        )

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

    def render_text2html(self, text):
        return self.markdown(text)

    def text_modified(self, widget):
        self.is_dirty = True

        # Update the preview frame and the xhtml file
        self.preview.load_rendered(
            self, self.render_text2html(self.textbuffer.get_property("text"))
        )

        return True # to say the signal has been handled

    def save(self, filename_tail):
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        text = self.textbuffer.get_text(start, end, False)

        if text is not None:
            print(f'Saving modified {shared.markdown_directory}/{filename_tail}')
            with open(f"{shared.markdown_directory}/{filename_tail}", "w") as f:
                try:
                    f.write(text)
                except Exception as e:
                    print(
                        f"Failed to write modified {shared.markdown_directory}/{filename_tail}"
                    )
                    print(repr(e))


    #@shared.print_caller_name(4)
    def save_if_dirty(self, filename_tail):
        # Called when opening a new section
        # The new text goes into the same textbuffer, so changes would be lost.
        if self.is_dirty:
            self.save(filename_tail)
            self.is_dirty = False
        else:
            print(f'Didn\'t bother saving unchanged {shared.markdown_directory}/{filename_tail}')

    def wrap_selection(self, start_wrapper, end_wrapper):
        try:
            (start_iter, end_iter) = self.textbuffer.get_selection_bounds()
        except ValueError:
            print("No selection")
        else:
            end_mark = self.textbuffer.create_mark(None, end_iter, left_gravity=False)
            self.textbuffer.insert(start_iter, start_wrapper)
            end_iter = self.textbuffer.get_iter_at_mark(end_mark)
            self.textbuffer.insert(end_iter, end_wrapper)
            self.textbuffer.delete_mark(end_mark)


