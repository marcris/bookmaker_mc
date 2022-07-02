import os, os.path
import json
import zipfile
import codecs

import shutil
from datetime import datetime, timezone

import uuid

from collections import deque

from contextlib import contextmanager
from pathlib import Path

from .XMLforEPUB import container_xml, content_opf, toc_xhtml, toc_xhtml_end, toc_ncx, toc_ncx_end, cover_xhtml

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

import subprocess
import pathlib

XHTML_EXT = '.xhtml'


template_css="""h1 {
  text-align: center;
}
"""

open_bracket_html="""
<!DOCTYPE html>
<html xml:lang="en" lang="en" xmlns="http://www.w3.org/1999/xhtml"
                              xmlns:epub="http://www.idpf.org/2007/ops">
<head>
<title></title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<link rel = "stylesheet" href = "_css/github-markdown.css" type = "text/css" />
<link rel = "stylesheet" href = "_css/github-pygments.css" type = "text/css" />

<style>
    .markdown-body {
        min-width: 200px;
        max-width: 790px;
        margin: 0 auto;
        padding: 30px;
        break-before: always
    }
    .center-image {
        display:block;
        margin-left: auto;
        margin-right: auto;
    }
    h1 {
        break-before: always;
    }
    h1, h2, h3, h4, h5 {
        page-break-after: avoid;
    }
    table, figure {
        page-break-inside: avoid;
    }
    table, td, th {
        border: 2px solid black;
    }
    tr {
        valign:baseline;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    </style>


    @page {
        size: 6in 9in portrait;
        margin: 70pt 60pt 70pt;
    }
    @page:first {
        size: 6in 9in portrait;
      margin: 0;
    }

    div.frontcover { 
      page: cover; 
      content: url("cover.png");
      width: 100%;
      height: 100%; 
    }
    @page:right{
        @bottom-right {
            content: counter(page);
        }
    }
    @page:left{
        @bottom-left {
            content: counter(page);
        }
    }

</style>

</head>
<body>
<article class="markdown-body">
"""
close_bracket_html="""
</article>\n</body></html>
"""


class TOCview(Gtk.ScrolledWindow):
    from .toc_utils import   \
        table_of_contents,  \
        toc_scan,  \
        re_number,  \
        \
        button_press_event, \
        new_section_popup,  \
        new_section_after,  \
        new_subsection,  \
        delete_section

    def find_settings(self):
        # Make an instance of the GSettings for BookMaker.
        # Should only be called once, from TOCview.__init__.
        _curr_dir = os.path.split(__file__)[0]
        if not _curr_dir.startswith('/home/'):
            # We assume this means the application is installed, so look in the
            # central directory for GSettings schemas (/usr/share/glib-2.0/schemas)
            return Gio.Settings.__new__('com.marcrisoft.bookmaker')

        # Otherwise, get schema from the current (development) directory.
        # Make sure its been compiled since last change by compiling it now.
        # We should get (or overwrite) gschemas.compiled in ~/.local/share/glib-2.0/schemas,
        # but that should really be part of (local) installation. During development,
        # just compile it into current directory.
        try:
            print("compiling gsettings schema")
            subprocess.check_call(f'glib-compile-schemas .', shell=True)
        except subprocess.CalledProcessError:
            print ("compile didn't work")
            return None
        else:
            schema_source = Gio.SettingsSchemaSource.new_from_directory(
                _curr_dir, Gio.SettingsSchemaSource.get_default(), trusted=False)
            schema = schema_source.lookup(
                'com.marcrisoft.bookmaker', recursive=False)
            if not schema:
                raise Exception("Cannot get GSettings schema 'com.marcrisoft.bookmaker'")

        return Gio.Settings.new_full(schema, backend=None, path='/com/marcrisoft/bookmaker/')

    def __init__(self, main_window):
        super(self.__class__, self).__init__()

        self.main_window = main_window

        if not hasattr(self, 'gsettings'):
            self.gsettings = self.find_settings()
        self.recentbooks = deque([], maxlen=9)

        self.project_directory = None
        self.filename_tail = 'README'

        # -------------------------------------------------------------
        # Set up the treeview for the table of contents
        # -------------------------------------------------------------

        self.toc_view = Gtk.TreeView()
        self.toc_model = None  # initially

        self.toc_view.set_show_expanders(False)
        self.toc_view.set_level_indentation(30)
        # self.toc_view.columns_autosize()

        self.toc_view.connect("button-press-event", self.button_press_event)
        self.popup = None   # for use as context menu

        # create the TreeViewColumn
        self.tvcolumn = Gtk.TreeViewColumn('Table of Contents')
        self.tvcolumn.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.tvcolumn.set_property("fixed_width", 150)

        # add tvcolumn to treeview
        self.toc_view.append_column(self.tvcolumn)

        # create a CellRendererText to render the data
        self.cell = Gtk.CellRendererText()
        self.cell.set_fixed_height_from_font(1)
        # self.cell.set_property('background', 'pink')

        # add the cell to the tvcolumn and allow it to expand
        self.tvcolumn.pack_start(self.cell, True)

        # set the cell "text" attribute to column 0
        # (i.e. retrieve text from that column in toc_model)
        # self.tvcolumn.add_attribute(self.cell, 'text', 0)

        selection = self.toc_view.get_selection()
        self.selection_changed_handler = selection.connect("changed", self.on_toc_selection_changed)

        self.add(self.toc_view)
        self.show_all()




    def set_MV(self, MV):
        self.MV = MV

    def on_toc_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter != None:
            print("Selection changed to", model[treeiter][0])


    @contextmanager
    def choose_project_folder(self):
        # Allow the user to select a project folder. The project folder must contain
        # (as a minimum) a markdown file named README.md.

        chooser = Gtk.FileChooserDialog(title="Please choose a project folder",
                                        parent=None,
                                        action=Gtk.FileChooserAction.SELECT_FOLDER)
        chooser.add_buttons("_Open", Gtk.ResponseType.OK)
        chooser.add_buttons("_Cancel", Gtk.ResponseType.CANCEL)

        projects_base = self.gsettings.get_value('projects-base').unpack()
        print(f'projects_base was set to {projects_base}')
        if projects_base: # where user keeps existing projects
            chooser.set_current_folder(projects_base)
        else:
            chooser.set_current_folder(os.path.expanduser('~'))
            
        filefilter = Gtk.FileFilter()
        filefilter.set_name("Bookmaker projects")
        filefilter.add_mime_type("inode/directory")
        filefilter.add_pattern("*")
        chooser.add_filter(filefilter)

        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            print("Ok clicked")
            selected = chooser.get_filename()
            projects_base = str(Path(selected).parents[0])
            self.gsettings.set_value('projects-base', GLib.Variant('s', projects_base))
            print(f'projects_base now set to {projects_base}')

            print("Folder selected: %s" % chooser.get_filename())
            os.chdir(selected)  # always work in the project directory

            # The directory/file details will belong to TV as convention
            self.project_directory = selected
            self.filename_tail = 'README'

            yield selected
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
            yield None

        # this part acts as the contextmanager __exit__() method
        chooser.destroy()

    def open_section(self, section, project_directory, filename_tail):
        # NEW file details are supplied as arguments
        self.filename_path = os.path.join(project_directory, filename_tail)
        print("Opening section {0} in {1}.md".format(section, self.filename_path))

        # Current file details still held by TV (self)
        self.MV.save_if_dirty(self.project_directory, self.filename_tail)  # save the current changes, if any

        self.project_directory = project_directory  # new file details belong to TV (self)
        self.filename_tail = filename_tail

        self.force_first_line(section)

    def force_first_line(self, section):
        try:
            text = ""
            f = codecs.open("{0}.md".format(self.filename_path), 'r', encoding='utf-8')
            f.readline()        # read and discard existing first line
            text = f.read(-1)   # rest of the file
        except NameError as e:
            print(
                "Failed to open/read {0}.md :- {1}".format(self.filename_path, e.args))
        finally:
            self.MV.textbuffer.set_text("# {0}\n{1}".format(section, text))  # generated first line replacement
            f.close()

        self.MV.is_dirty = False


    def get_project_directory(self):
        return self.project_directory

    def re_write_summary(self):
        with open(self.project_directory + "/" + 'SUMMARY.txt', 'w') as f:
            f.write('# Summary\n\n')

            scan = self.toc_scan()  # we need a new generator

            for it in scan:
                f.write('{0}* [{1}]({2})\n'.format(
                    '    ' * it[0],
                    self.toc_model.get_value(it[1], 0),  # the section title
                    self.toc_model.get_value(it[1], 1)))  # the file path
                    
    def insert_inline_toc(self):
        with open(os.path.join(self.project_directory, '_book/TOC.html'), 'w') as f:
            f.write("<html>")
            f.write("<head>")
            f.write("</head>")
            f.write("<body>")
            
            f.write("<h1>Contents</h1>")
            f.write('<pre>')

            scan = self.toc_scan()  # we need a new generator
            for it in scan:
                section = str(self.toc_model.get_value(it[1], 2))
                sub = str(self.toc_model.get_value(it[1], 3))
                subsub = str(self.toc_model.get_value(it[1], 4))
                subsubsub = str(self.toc_model.get_value(it[1], 5))
                subsubsubsub = str(self.toc_model.get_value(it[1], 6))
                sub5 = str(self.toc_model.get_value(it[1], 7))

                if sub > '0':
                    section = "    {0}.{1}".format(section, sub)
                if subsub > '0':
                    section = "    {0}.{1}".format(section, subsub)
                if subsubsub > '0':
                    section += '.' + subsubsub
                if subsubsubsub > '0':
                    section += '.' + subsubsubsub
                if sub5 > '0':
                    section += '.' + sub5
                                        
                if sub == '0':
                    f.write('\n')   # Blank line before top-level sections
                # N.B. the next line MUST have <space><space><newline> to
                # get correct line breaks in the HTML.
                f.write("{0}    {1}  \n".format(section, self.toc_model.get_value(it[1], 0)))
                
            f.write('</pre></body></html>')
            

    def refresh_all(self):
        # Used by export_to_epub().
        # Run through the table of contents, saving copies of all the necessary files
        # into backup_directory.
        scan = self.toc_scan()  # we need a new generator

        # make an empty "backup" directory, or empty it if it exists.
        self.backup_directory = "{0}/_backup".format(self.project_directory)
        shutil.rmtree(self.backup_directory, True)
        os.mkdir(self.backup_directory)

        shutil.copy2(f'{self.project_directory}/SUMMARY.md', f'{self.backup_directory}/SUMMARY.md')
        shutil.copy2(f'{self.project_directory}/book.json', f'{self.backup_directory}/book.json')
        shutil.copy2(f'{self.project_directory}/cover.png', f'{self.backup_directory}/cover.png')

        shutil.copytree(f'{self.project_directory}/_css', f'{self.backup_directory}/_css')
        shutil.copytree(f'{self.project_directory}/_images', f'{self.backup_directory}/_images')

        for it in scan:
            title = self.toc_model.get_value(it[1], 0)
            filepath = self.toc_model.get_value(it[1], 1)
            section = self.toc_model.get_value(it[1], 2)

            htmlpath = filepath[0:-3] + XHTML_EXT
            # print("HTMLPATH", htmlpath)

            self.open_section(f"{section} {title}", self.project_directory, filepath[0:-3])

            backup_md = self.backup_directory + "/" + filepath[0:-3] + ".md"
            os.makedirs(os.path.dirname(backup_md), exist_ok=True)  # make a backup markdown file...
            with codecs.open(backup_md, "w") as f:  # ...and copy the markdown text to it
                start = self.MV.textbuffer.get_start_iter()
                end = self.MV.textbuffer.get_end_iter()
                f.write(self.MV.textbuffer.get_text(start, end, False))

            self.PV.save_rendered_html(self.project_directory, filepath[0:-3]) # write html file

            current_html = f'{self.project_directory}/_book/{htmlpath}' # now back up the html
            backup_html = f'{self.backup_directory}/_book/{htmlpath}'
            os.makedirs(os.path.dirname(backup_html), exist_ok=True)    # creates intermediate directories if missing
            shutil.copy2(current_html, backup_html)

    def export_to_pdf(self):
        # Export to pdf is done by combining all the .xhtml files of the book into one file
        # called book.html, including additions like the pdf meta-data, generated chapter/section
        # headings etc. and presenting the result to a suitable converter. Currently we use Prince
        # (www.princexml.com), although paged.js may be worth investigation.

        self.pdf_directory = self.project_directory + "/_pdf"  # created/emptied if user does "export to pdf"
        with codecs.open('{0}/book.html'.format(self.pdf_directory), 'w') as f:
            f.write("<html>\n")
            f.write("<head>\n")
            f.write('    <meta charset="utf-8" />')
            with open(self.project_directory + '/book.json') as j:
                data = json.load(j)
                f.write(f"    <title> {data['title']}\n </title>\n")
                author = data['author']
                f.write(f'    <meta name="creator" content="{author}">\n')
                f.write(f'    <meta name="author" content="{author}">\n')
                date = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                f.write(f'    <meta name="date" content={date}>\n')

            f.write('    <link rel = "stylesheet" href = "github-markdown.css" type = "text/css" />\n')
            f.write('    <link rel = "stylesheet" href = "github-pygments.css" type = "text/css" />\n')
            f.write("</head>\n")

        scan = self.toc_scan()  # we need a new generator

        print("Exporting to PDF")
        with codecs.open(f'{self.pdf_directory}/book.html', 'a') as f:
            f.write('<body>\n')
            f.write('<div class="frontcover">\n')
            f.write('</div>\n')
            f.write('<br/>\n')
            f.write('<br/>\n')
            f.write('<br/>\n')
            f.write('<br/>\n')

            f.write('<div class="body">\n')

        os.chdir(self.pdf_directory)

        for it in scan:
            title = self.toc_model.get_value(it[1], 0)
            filepath = self.toc_model.get_value(it[1], 1)
            section = str(self.toc_model.get_value(it[1], 2))
            sub = str(self.toc_model.get_value(it[1], 3))
            subsub = str(self.toc_model.get_value(it[1], 4))
            subsubsub = str(self.toc_model.get_value(it[1], 5))
            subsubsubsub = str(self.toc_model.get_value(it[1], 6))
            sub5 = str(self.toc_model.get_value(it[1], 7))

            if sub > '0':
                section += '.' + sub
            if subsub > '0':
                section += '.' + subsub
            if subsubsub > '0':
                section += '.' + subsubsub
            if subsubsubsub > '0':
                section += '.' + subsubsubsub
            if sub5 > '0':
                section += '.' + sub5

            self.open_section(f"{section} {title}", self.project_directory, filepath[0:-3])
            print(f'section {section}, sub={sub}, subsub={subsub}')

            with codecs.open(f'{self.pdf_directory}/book.html', 'a') as f:
                if subsub=='0': # major topic
                # if sub > '0' and subsub == '0':  # major topic
                    print(f'Writing <div class="chapter">')
                    f.write('<div class="chapter">\n')
                start = self.MV.textbuffer.get_start_iter()
                end = self.MV.textbuffer.get_end_iter()
                f.write(self.MV.markdown(self.MV.textbuffer.get_text(start, end, False)))
                # if sub > '0' and subsub == '0':  # major topic
                if subsub=='0':
                    f.write('</div>\n')

        with codecs.open(f'{self.pdf_directory}/book.html', 'a') as f:
            f.write('</div>\n') # end of div class="body"

        os.chdir(self.pdf_directory)
        # subprocess.run("prince -s pdf-styles.css toc.html book.html -o builds/book.pdf", shell=True)
        subprocess.run("prince -s pdf-styles.css book.html -o book.pdf", shell=True)

    def export_to_epub(self):
        def escape(t):
            """HTML-escape the text in `t`."""
            return (t
                    .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    .replace("'", "&#39;").replace('"', "&quot;")
                    )

        self.refresh_all()  # backs up the required stuff to _backup directory tree
        os.chdir(self.project_directory)
        self.epub_directory = self.project_directory + "/_epub"  # created/emptied if user does "export to epub"
        shutil.rmtree(self.epub_directory, True)
        os.mkdir(self.epub_directory)
        os.chdir(self.epub_directory)

        self.script_directory = self.book_directory + '/_script'



        # Create the epub file
        with zipfile.ZipFile('mybook.epub', mode='w') as zf:
            # Write the 'mimetype' file to it; note no newline, not compressed
            zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

            zf.writestr('META-INF/container.xml', container_xml, compress_type=zipfile.ZIP_DEFLATED)

            # zf.write('{0}/CSS-boilerplate.css'.format(self.css_directory), 'OEBPS/_css/CSS-boilerplate.css',
            #          compress_type=zipfile.ZIP_DEFLATED)
            zf.write('{0}/github-markdown.css'.format(self.css_directory), 'OEBPS/_css/github-markdown.css',
                     compress_type=zipfile.ZIP_DEFLATED)
            zf.write('{0}/github-pygments.css'.format(self.css_directory), 'OEBPS/_css/github-pygments.css',
                     compress_type=zipfile.ZIP_DEFLATED)
            zf.write('{0}/mermaid.min.js'.format(self.script_directory), 'OEBPS/_script/mermaid.min.js',
                     compress_type=zipfile.ZIP_DEFLATED)

            zf.write('{0}/cover.png'.format(self.project_directory), 'OEBPS/cover.png', compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr('OEBPS/cover.xhtml', cover_xhtml, compress_type=zipfile.ZIP_DEFLATED)

            self.title = 'Programming Python with GTK + and SQLite'
            self.author = 'C.C. Brown'
            self.date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            # must be in ISO 8601 format, with timezone Z indicating UTC
            # i.e. if used in a different timezone, utcnow will translate to UTC equivalent
            # doesn't account for daylight saving time but for this use who cares?

            self.ISBN = uuid.uuid4()
            print(self.ISBN)
            # input argument format to template is in dictionary format (see template for where variables are inserted)
            argDict = {'title': self.title,
                       'author': self.author,
                       'date': self.date,
                       'ISBN': self.ISBN}

            c_opf = content_opf.format_map(argDict)

            imagedir = self.project_directory + "/_book/_images"
            image_list = os.listdir(imagedir)
            for imagefile in image_list:
                imagename = imagefile.split('.')[0]
                imagetype = imagefile.split('.')[-1]
                # zf.write('{0}/{1}'.format(imagedir, imagefile), 'OEBPS/_images/{0}'.format(imagefile),
                zf.write('{0}/{1}'.format(imagedir, imagefile), 'OEBPS/_book/_images/{0}'.format(imagefile),
                                  compress_type=zipfile.ZIP_DEFLATED)
                c_opf += '    <item id="{0}" href="{1}" media-type="image/{2}" />\n'.format(
                    '{0}-{1}'.format(imagename, imagetype), '/_book/_images/{0}'.format(imagefile), imagetype)

            # Insert the links to the HTML content files into the Manifest section of the content.opf
            scan = self.toc_scan()

            for it in scan:
                filepath = self.toc_model.get_value(it[1], 1)
                htmlpath = filepath[0:-3] + '.xhtml'
                filename = filepath.split('/')[-1][0:-3]
                c_opf += '    <item id="{0}" href="{1}" media-type="application/xhtml+xml" />\n'.format(filename, htmlpath)

                print ('Copying {0}/{1}'.format(self.book_directory, htmlpath))
                # While we have the details to hand, add the content file itself to the zip
                zf.write('{0}/{1}'.format(self.book_directory, htmlpath),
                         'OEBPS/' + htmlpath,
                         compress_type=zipfile.ZIP_DEFLATED)

            c_opf += '  </manifest>\n'

            # Generate the Spine section of the content.opf
            c_opf += '  <spine toc="ncx">\n'
            scan = self.toc_scan()  # we need a new generator

            for it in scan:
                filepath = self.toc_model.get_value(it[1], 1)
                filename = filepath.split('/')[-1][0:-3]
                c_opf += '    <itemref idref="{0}" />\n'.format(filename)

            c_opf += '  </spine>\n'

            c_opf += '</package>\n'
            # That completes the OPF package; add it to the zip
            zf.writestr('OEBPS/content.opf', c_opf, compress_type=zipfile.ZIP_DEFLATED)

            # Now we need
            toc_html = toc_xhtml    # basis for toc.xhtml from XMLforEPUB.py

            scan = self.toc_scan()  # we need a new generator

            for it in scan:
                title = escape(self.toc_model.get_value(it[1], 0))   # title may contain special character(s)
                filepath = self.toc_model.get_value(it[1], 1)
                htmlpath = filepath[0:-3] + XHTML_EXT
                toc_html += '            <li><a href="{0}">"{1}"</a></li>\n'.format(htmlpath, title)

            toc_html += toc_xhtml_end    # termination for toc.xhtml from XMLforEPUB.py
            zf.writestr('OEBPS/toc.xhtml', toc_html, compress_type=zipfile.ZIP_DEFLATED)

            # Now the legacy toc.ncx file so EPUB2 readers can process it (EPUB3 reader ignores it)
            ncx = toc_ncx    # basis for toc.ncx from XMLforEPUB.py
            print(self.ISBN)
            argDict = {'ISBN': self.ISBN}
            ncx = ncx.format_map(argDict)

            scan = self.toc_scan()  # we need a new generator
            playOrder = 0
            template = """\
        <navPoint id="navPoint-%(playOrder)s" playOrder="%(playOrder)s">
          <navLabel>
            <text>%(title)s</text>
          </navLabel>
          <content src="%(htmlpath)s"/>
        </navPoint>
    """
            for it in scan:
                title = escape(self.toc_model.get_value(it[1], 0))   # title may contain special character(s)
                filepath = self.toc_model.get_value(it[1], 1)
                htmlpath = filepath[0:-3] + XHTML_EXT
                playOrder += 1
                argDict = {'playOrder': playOrder,
                           'title': title,
                           'htmlpath': htmlpath,
                           'ISBN': self.ISBN}
                ncx += template % argDict

            ncx += toc_ncx_end
            zf.writestr('OEBPS/toc.ncx', ncx, compress_type=zipfile.ZIP_DEFLATED)
            
            print (zf.testzip())
            
        shutil.copyfile('mybook.epub', 'mybook.zip')




