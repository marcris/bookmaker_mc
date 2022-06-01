#!/usr/bin/python3

import os
import shutil
import sys
import platform
import signal
from collections import deque


print('')
print('Now in BookMaker.py')
print(f'sys.path = {sys.path}')
print(f'sys.executable = {sys.executable}')

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gdk', '3.0')
# gi.require_version('Pango', '1.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gio, Gtk, GdkPixbuf, GLib

from . import about
from .toc_view import TOCview
from .markdown_view import MARKDOWNview
from .pre_view import PREview

from pathlib import Path

# The following declaration allows the application to be invoked from anywhere
# and access its database and .glade files etc. relative to its source directory.
from os.path import dirname

def where_am_i():  # use to find ancillary files e.g. .glade files
    return dirname(__file__)


UPSTART_LOGO = where_am_i() + '/logo.svg'


class RecentBooksDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Choose from Recent Books", transient_for=parent, flags=0)
        self.set_default_size(200, 200)
        vbox = self.get_content_area()

        self.parent = parent

        for item in parent.recentbooks:
            if os.path.exists(item):
                button = Gtk.Button(item)
                vbox.add(button)
                button.connect("clicked", self.on_open_recent_book)

        spacer = Gtk.Label("")
        vbox.add(spacer)

        button = Gtk.Button("... or some other book")
        vbox.add(button)
        button.connect("clicked", self.on_selectprojectfolder_clicked)

        self.show_all()

    def on_open_recent_book(self, button):
        self.response(Gtk.ResponseType.OK)
        self.parent.on_open_recent_book(button)

    def on_selectprojectfolder_clicked(self, button):
        self.response(Gtk.ResponseType.OK)
        self.parent.on_selectprojectfolder_clicked()



class AppWindow(Gtk.ApplicationWindow):

    def on_destroy(self, widget):
        print("Caught destroy event")
        print("i.e. Main window destroyed; quit application")
        self.app.quit()

    def on_delete_event(self, widget, *data):
        print("Caught main window delete event")
        print("i.e. Main window close button clicked; ask user what to do")

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Do you really want to close?")
        dialog.format_secondary_text(
            "(Your current changes will be saved automatically)")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            print("QUESTION dialog closed by clicking YES button")
            print("i.e. user really does want to close")
            print("     so save changes as promised and return False")
        else:
            if response == Gtk.ResponseType.NO:
                print("QUESTION dialog closed by clicking NO")
            elif response == Gtk.ResponseType.DELETE_EVENT:
                print("QUESTION dialog closed by clicking X")
            print("i.e. user didn't really want to close; return True")
            return True  # means we have dealt with signal; no action required

        self.MV.save_if_dirty(self.TV.project_directory, self.TV.filename_tail)
        return False  # means go ahead with the Gtk.main_quit action

    def last_chance_saloon(self, signalnum, frame):
        # Handler for SIGTERM which will save work as a last resort
        # i.e. if user requests shutdown while there are edits outstanding.
        self.out.write(f'signal {signalnum} received')
        self.MV.save_if_dirty(self.TV.project_directory, self.TV.filename_tail)
        self.out.write(f'calling original_handler')
        self.out.flush()
        self.original_handler(signalnum, frame)

    def __init__(self, app, *args, **kwargs):
        Gtk.Window.__init__(self, application=app)
        # super().__init__(app, **kwargs)

        # Register handler for SIGTERM which will save work as a last resort
        # i.e. if user requests shutdown while there are edits outstanding.
        self.out = open('log.txt', 'w')

        self.original_handler = signal.signal(signal.SIGHUP, self.last_chance_saloon)

        self.app = app
        self.connect('destroy', self.on_destroy)
        self.connect('delete-event', self.on_delete_event)

        print(f'This is {about.NAME} version {about.VERSION} using Python {platform.python_version()}')

        self.vbox = Gtk.VBox()

        # Position execution in the directory where the current file
        # (BookMaker.py) is situated, so builder.get_object can find
        # the ui_*.xml files.
        os.chdir(Path(__file__).parents[0])

        self.builder = Gtk.Builder()
        self.builder.add_from_file("ui_menu.xml")
        self.vbox.add(self.builder.get_object("menubar"))

        self.builder.add_from_file("ui_toolbar.xml")
        self.vbox.add(self.builder.get_object("toolbar"))

        hbox = Gtk.HBox()
        self.vbox.add(hbox)  # add the hbox which will contain the toc/markdown/preview

        # Get the GdkScreen associated with the ApplicationWindow
        # Get the associated GdkDisplay (group of screens on one workstation)
        # Get the particular GdkMonitor within the GdkDisplay
        # Get the GdkMonitor's geometry (usable display rectangle)
        rect = self.get_screen().get_display().get_monitor(0).get_geometry()
        rect.height -= 28  # allow for panel height (approx)
        print(f"Size = {rect.width} x {rect.height}")

        # Let's size the working area (hbox) to 0.75 of the available desktop
        hbox.set_size_request(rect.width * 0.75, rect.height * 0.75)

        # Now size the subwindows within their hbox. The total width of the
        # three subwindows must add up to the width of the hbox.

        # Size the Table of Contents
        toc = TOCview(self)  # TOCview needs transient base for dialogs
        toc.set_size_request(rect.width * 0.15, -1)

        self.TV = toc
        hbox.add(toc)

        # Size the Markdown editing area
        self.MV = MARKDOWNview(toc)  # needs to reference toc for project directory/file details
        self.MV.set_size_request(rect.width * 0.25, -1)
        hbox.add(self.MV)

        self.TV.set_MV(self.MV)

        # Size the preview display area
        self.PV = PREview(toc)
        self.PV.set_size_request(rect.width * 0.35, -1)
        hbox.add(self.PV)

        # Now add the statusbar
        self.builder.add_from_file("ui_statusbar.xml")
        self.builder.connect_signals(self)

        self.statusbar = self.builder.get_object("statusbar")

        # its context_id - not shown in the UI but needed to uniquely identify the source of a message
        self.context_id = self.statusbar.get_context_id("example")

        self.vbox.add(self.statusbar)

        # we push a message onto the statusbar's stack
        self.statusbar.push(
            self.context_id, "Waiting for you to do something...")

        self.add(self.vbox)  # add the whole vbox to the window

        self.MV.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        #         self.PV.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        self.MV.set_PV(self.PV)
        self.MV.syncscroll_instance = None
        # SyncScroll(self.MV, self.PV)

        # Set up for File | Open recent...
        gsettings = Gtk.Settings.get_default()	# system's default settings
        # We're not using GTK's recent files mechanism
        gsettings.set_property("gtk-recent-files-enabled", False)

        self.gsettings = self.TV.gsettings	# BookMaker's private settings
        # Instead we'll keep a record in settings 'project-dirs'
        self.recentbooks = deque([], maxlen=9)
        self.recentbooks.extend(self.gsettings.get_value('project-dirs').unpack())
        print(self.recentbooks)

        menu = self.builder.get_object("recent-chooser-menu")
        for item in self.recentbooks:
            menuitem = Gtk.MenuItem(item)
            menu.prepend(menuitem)
            menuitem.connect("activate", self.on_open_recent_book)

        # Set up the actions to make the menu/toolbar "live" before
        # we populate the toc/markdown/preview.

        # The "win.selectprojectfolder" action
        selectprojectfolder_action = Gio.SimpleAction.new("selectprojectfolder", None)
        selectprojectfolder_action.connect("activate", self.on_selectprojectfolder_clicked)
        self.add_action(selectprojectfolder_action)

        # The "win.openrecent" action
        recentprojectfolder_action = Gio.SimpleAction.new("openrecent", None)
        recentprojectfolder_action.connect("activate", self.on_openrecent_clicked)
        self.add_action(recentprojectfolder_action)

        # The "win.exporttoepub" action
        exporttoepub_action = Gio.SimpleAction.new("exporttoepub", None)
        exporttoepub_action.connect("activate", self.on_exporttoepub_clicked)
        self.add_action(exporttoepub_action)

        # The "win.exporttopdf" action  # experimental only
        # Commented out so action not defined -> greyed out in menu
        exporttopdf_action = Gio.SimpleAction.new("exporttopdf", None)
        exporttopdf_action.connect("activate", self.on_exporttopdf_clicked)
        self.add_action(exporttopdf_action)

        # The "win.undo/redo" actions
        undo_action = Gio.SimpleAction.new("undo", None)
        undo_action.connect("activate", self.on_undo_clicked)
        self.add_action(undo_action)

        redo_action = Gio.SimpleAction.new("redo", None)
        redo_action.connect("activate", self.on_redo_clicked)
        self.add_action(redo_action)

        # The "win.copy/paste/cut" actions
        copy_action = Gio.SimpleAction.new("copy", None)
        copy_action.connect("activate", self.on_copy_clicked)
        self.add_action(copy_action)

        paste_action = Gio.SimpleAction.new("paste", None)
        paste_action.connect("activate", self.on_paste_clicked)
        self.add_action(paste_action)

        cut_action = Gio.SimpleAction.new("cut", None)
        cut_action.connect("activate", self.on_cut_clicked)
        self.add_action(cut_action)

        # The "win.bold/italic/underline" actions
        bold_action = Gio.SimpleAction.new("bold", None)
        bold_action.connect("activate", self.on_bold_clicked)
        self.add_action(bold_action)

        italic_action = Gio.SimpleAction.new("italic", None)
        italic_action.connect("activate", self.on_italic_clicked)
        self.add_action(italic_action)

        underline_action = Gio.SimpleAction.new("uline", None)
        underline_action.connect("activate", self.on_uline_clicked)
        self.add_action(underline_action)

        # The "win.as_python/as_text" actions
        # The relevant icons for the toolbar are designed externally
        # and placed in ~/.icons/icon_py.png and ~/.icons/icon_text.png
        as_python_action = Gio.SimpleAction.new("as_python", None)
        as_python_action.connect("activate", self.on_as_python_clicked)
        self.add_action(as_python_action)

        as_text_action = Gio.SimpleAction.new("as_text", None)
        as_text_action.connect("activate", self.on_as_text_clicked)
        self.add_action(as_text_action)

        # The "win.insert-image" action
        image_action = Gio.SimpleAction.new("insert_image", None)
        image_action.connect("activate", self.on_insert_image_clicked)
        self.add_action(image_action)

        # The "win.about" action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_clicked)
        self.add_action(about_action)


    # Callbacks for "win" actions

    def on_newproject_clicked(self):
        print("newproject clicked")
        # The new project_directory will be created under the current projects_base
        # (see toc_view/choose_project_folder()).
        # We rely on the user to use the facility to create a directory in the
        # Gtk.FileChooserDialog and then select that directory.
        with self.TV.choose_project_folder() as project_directory:
            if not project_directory:  # if file chooser returned None (Cancel) don't change anything
                print('User cancelled project selection')
                return

            # ... otherwise set up our book project structure

            # ... including the basics open assumes to be there
            print(f'Creating project {project_directory}')
            self.open_book_project(project_directory)

    def on_selectprojectfolder_clicked(self):
        print("selectprojectfolder clicked")
        with self.TV.choose_project_folder() as project_directory:
            if not project_directory:  # if file chooser returned None (Cancel) don't change anything
                print('User cancelled project selection')
                return

            # ... otherwise set up our book project structure
            self.open_book_project(project_directory)

    def on_openrecent_clicked(self, action, parameter):
        print("openrecent clicked")

    def on_item_activated(self, parameter):
        print('item activated')
        filename = Path(parameter.get_current_item().get_uri_display())
        print(f'filename clicked was {filename}')
        self.open_book_project(str(filename))

    def open_book_project(self, project_directory):
        # First close down the current book safely. (Current file details still held by TV)
        self.MV.save_if_dirty(self.TV.project_directory, self.TV.filename_tail)
        print(os.getcwd(), os.path.exists(project_directory))
        if not os.path.exists(project_directory):
            raise FileNotFoundError(f'"{project_directory}" - no such book exists')

        self.project_directory = project_directory
        self.book_directory = project_directory + "/_book"

        self.book_css_directory = os.path.join(self.book_directory, '_css')
        # If necessary, make the _book/_css directory and put our project css in it
        css_resources = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'css_resources')
        shutil.copytree(css_resources, self.book_css_directory, dirs_exist_ok=True)

        self.epub_directory = project_directory + "/_epub"  # created/emptied if user does "export to epub"
        self.pdf_directory = project_directory + "/_pdf"  # created/emptied if user does "export to pdf"

        # The new directory/file details will belong to TV as convention
        self.TV.project_directory = project_directory
        self.TV.filename_tail = 'README'

        self.TV.book_directory = self.book_directory
        self.TV.css_directory = css_resources

        # Display the table of contents and open the default (README) file
        book_resources = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'book_resources')
        if not os.path.exists(os.path.join(project_directory, 'README.md')):
            # This is a new book
            shutil.copy(os.path.join(book_resources, 'README.md'), project_directory)
            shutil.copy(os.path.join(book_resources, 'SUMMARY.md'), project_directory)

        print(f'Display the table of contents')
        os.chdir(self.project_directory)  # Always work in the project directory

        opening_section = self.TV.table_of_contents()
        print(f'User asked to open {opening_section}')

        self.set_title("BookMaker - " + project_directory)

        self.recentbooks.clear()    # clear and rebuild the deque
        self.recentbooks.extend(self.gsettings.get_value('project-dirs').unpack())
        if project_directory not in self.recentbooks:
            self.add_to_recentbooks(project_directory)
        self.MV.is_dirty = False  # DON'T write nothingness to SUMMARY.md !!!

        self.MV.textbuffer.begin_not_undoable_action()
        self.TV.open_section(opening_section, project_directory, self.TV.filename_tail)
        self.MV.textbuffer.end_not_undoable_action()

        self.TV.re_write_summary()

    def add_to_recentbooks(self, project_directory):
        self.recentbooks.appendleft(project_directory)
        self.gsettings.set_value('project-dirs', GLib.Variant('as', self.recentbooks))
        menu = self.builder.get_object("recent-chooser-menu")
        menuitem = Gtk.MenuItem(label=project_directory)
        menu.prepend(menuitem)
        menuitem.connect("activate", self.on_open_recent_book)

    def on_open_recent_book(self, parameter):
        which_book = parameter.get_label() # parameter is the recent books' submenu item clicked
        print(f'on_open_recent_book("{which_book}")')
        self.open_book_project(which_book)

    def on_exporttoepub_clicked(self, action, parameter):
        print("exporttoepub clicked")
        self.TV.export_to_epub()

    def on_exporttopdf_clicked(self, action, parameter):
        print("exporttopdf clicked")
        self.TV.export_to_pdf()

    def on_undo_clicked(self, action, parameter):
        print("undo clicked")
        if self.MV.textbuffer.can_undo():
            self.MV.textbuffer.undo()
            self.MV.is_dirty = True

    def on_redo_clicked(self, action, parameter):
        print("redo clicked")
        if self.MV.textbuffer.can_redo():
            self.MV.textbuffer.redo()
            self.MV.is_dirty = True

    def on_copy_clicked(self, action, parameter):
        print("copy clicked")
        self.MV.textbuffer.copy_clipboard(self.MV.clipboard)  # Copies the currently-selected text to the clipboard.

    def on_paste_clicked(self, action, parameter):
        print("paste clicked")
        editable = self.MV.textview.get_editable()
        self.MV.textbuffer.paste_clipboard(self.MV.clipboard, None, editable)  # Pastes the contents of the clipboard.
        self.MV.is_dirty = True

    def on_cut_clicked(self, action, parameter):
        print("cut clicked")
        editable = self.MV.textview.get_editable()
        self.MV.textbuffer.cut_clipboard(self.MV.clipboard, editable)
        # Copies the currently-selected text to a clipboard, then deletes the text if it’s editable.
        self.MV.is_dirty = True

    def on_bold_clicked(self, action, parameter):
        print("bold clicked")
        self.MV.wrap_selection("**", "**")
        self.MV.is_dirty = True

    def on_italic_clicked(self, action, parameter):
        print("italic clicked")
        self.MV.wrap_selection("*", "*")
        self.MV.is_dirty = True

    def on_uline_clicked(self, action, parameter):
        print("uline clicked")
        self.MV.wrap_selection("_", "_")
        self.MV.is_dirty = True

    def on_strike_clicked(self, action, parameter):
        print("strike clicked")
        self.MV.wrap_selection("~~", "~~")
        self.MV.is_dirty = True

    def on_as_python_clicked(self, action, parameter):
        print("as_python clicked")
        self.MV.wrap_selection("```py\n", "```")
        self.MV.is_dirty = True

    def on_as_text_clicked(self, action, parameter):
        print("as_text clicked")
        self.MV.wrap_selection("```text\n", "```")
        self.MV.is_dirty = True

    def on_insert_image_clicked(self, action, parameter):
        print(f'filename_path = {self.TV.filename_path}.md')
        dlg = Gtk.FileChooserDialog("Insert Image", self, Gtk.FileChooserAction.OPEN,
                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                     Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dlg.set_current_folder(self.TV.project_directory)
        dlg.set_default_response(Gtk.ResponseType.OK)

        filefilter = Gtk.FileFilter()
        filefilter.set_name("Images")
        filefilter.add_mime_type("image/png")
        filefilter.add_mime_type("image/jpeg")
        filefilter.add_mime_type("image/gif")
        filefilter.add_pattern("*.png")
        filefilter.add_pattern("*.jpg")
        filefilter.add_pattern("*.gif")
        filefilter.add_pattern("*.tif")
        filefilter.add_pattern("*.xpm")
        dlg.add_filter(filefilter)

        response = dlg.run()
        if response == Gtk.ResponseType.OK:
            imagefilepath = dlg.get_filename()  # actually gets the full path to the file

            images_directory = os.path.join(self.TV.project_directory, '_images/')

            # copy the file to the working images_directory (under project_directory)
            shutil.copy(imagefilepath, images_directory)
            # and to the final images_directory (under project_directory/_book) which
            # will be used in generating the book in whatever format.
            images_directory = os.path.join(self.TV.project_directory, '_book/_images/')
            shutil.copy(imagefilepath, images_directory)

            # this directory will be copied into the OEBPS directory of the epub, so we
            # need to insert a **relative** link in the generated xhtml content file.

            # Need to be in the current .md file's directory so the relative path will
            # work now in the preview as well as later in the epub file structure.
            curr_md_dir = os.path.split(f'{self.TV.filename_path}.md')[0]
            #
            # NOTE: the .xhtml file structure (below project_directory/_book) must be
            # kept parallel to the .md file structure (below project_directory), so
            # the xhtml can use relative addressing.
            relative = os.path.relpath(images_directory, curr_md_dir)

            self.MV.textbuffer.insert_at_cursor('![]({0}/{1})'.format(relative, os.path.split(imagefilepath)[1]))

            self.MV.is_dirty = True

        dlg.destroy()

    # noinspection PyMethodMayBeStatic
    def on_about_clicked(self, action, parameter):
        """
        Show an About dialog.
        """
        dialog = Gtk.AboutDialog()
        dialog.set_program_name(about.NAME)
        dialog.set_version("%s %s" % ('Version', about.VERSION))
        dialog.set_copyright(about.COPYRIGHT)
        dialog.set_comments(about.DESCRIPTION)
        dialog.set_authors(about.AUTHORS)
        # dialog.set_website(about.WEBSITE)

        dialog.set_license_type(Gtk.License.MIT_X11)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            UPSTART_LOGO,
            about.DEFAULT_LOGO_SIZE_WIDTH, about.DEFAULT_LOGO_SIZE_HEIGHT, True)
        dialog.set_logo(pixbuf)
        dialog.run()
        dialog.destroy()


class Application(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.myapp",
                         **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(self)
            # title="Hello World!")

        self.window.show_all()

        dialog =  RecentBooksDialog(self.window)
        dialog.run()
        dialog.destroy()

        dmx, dmy = self.window.get_size()
        print(f"Size = {dmx} x {dmy}")

    def do_startup(self):
        # FIRST THING TO DO: do_startup()
        Gtk.Application.do_startup(self)

        # The "app.new"_action
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new_clicked)
        self.add_action(new_action)

        # The "app.quit"_action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_clicked)
        self.add_action(quit_action)

    # The callbacks for app actions
    # noinspection PyMethodMayBeStatic
    def on_new_clicked(self, action, parameter):
        print("new clicked")

    def on_quit_clicked(self, action, parameter):
        print("quit clicked")
        # Call on_destroy directly to get same effect as clicking window 'x'
        if not self.window.on_delete_event(self.window):
            self.quit()

def main():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    print('BookMaker.py, called as script')
    appl = Application()
    appl.run(sys.argv)
