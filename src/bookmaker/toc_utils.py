#import pdb
import codecs
import json
import subprocess
from datetime import datetime, timezone

import gi
import os
# pyrefly: ignore  # import-error
import shared
from collections import namedtuple

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
# pyrefly: ignore  # missing-module-attribute
from gi.repository import Gdk, Gtk  # noqa: E402

from functools import wraps

def get_record(model, it, fieldname):
    # pyrefly: ignore  # invalid-argument
    record = namedtuple('fieldnames',
        ['title', 'filename', 'parentid', 'section', 'id',])
    return record


def tree_path_to_section(thepath):
    thepath = thepath.rsplit(':')  # get a list of the path elements
    newpath = []
    for el in thepath:
        # pyrefly: ignore  # bad-argument-type
        newpath.append(str(int(el) + 1))
    return '.'.join(newpath)


def tree_path_to_following_section(thepath):
    thepath = thepath.rsplit(':')  # get a list of the path elements
    thepath[-1] = str(int(thepath[-1]) + 1)    # path to the following section
    newpath = []
    for el in thepath:
        # pyrefly: ignore  # bad-argument-type
        newpath.append(str(int(el) + 1))
    return '.'.join(newpath)

def tree_path_to_first_subsection(thepath):
    thepath = thepath.rsplit(':')  # get a list of the path elements
    thepath.append('0')    # path to the first subsection
    newpath = []
    for el in thepath:
        # pyrefly: ignore  # bad-argument-type
        newpath.append(str(int(el) + 1))
    return '.'.join(newpath)



def print_caller_name(stack_size=3):
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            import inspect
            stack = inspect.stack()

            s = '{index:>5} : {module:^25} : {name}'
            callers = ['', s.format(index='level', module='module', name='name'), '-' * 50]

            for n in reversed(list(range(1, stack_size))):
                module = inspect.getmodule(stack[n][0])
                # pyrefly: ignore  # missing-attribute
                callers.append(s.format(index=n, module=module.__name__, name=stack[n][3]))

            callers.append(s.format(index=0, module=fn.__module__, name=fn.__name__))
            callers.append('')
            print('\n'.join(callers))

            fn(*args, **kwargs)

        return inner

    return wrapper

def debug_on(*exceptions):
    if not exceptions:
        exceptions = (AssertionError, )
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions:
                print(exceptions)#pdb.post_mortem(sys.exc_info()[2])
        return wrapper
    return decorator


sdict = {}     # module-level global: cross-reference key = child.id vs. value = parent.id


def button_press_event(self, treeview, event):
    path, column, x, y = treeview.get_path_at_pos(int(event.x), int(event.y))
    print(f'button_press_event called with path={path.to_string()}')
    model = self.sorted_model   # treeview is displaying sorted_model
    # We click on the tree view in order to
    #   - go to a new article (by left-clicking)
    if event.button == 1:  # left click
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.markdown_view.textbuffer.begin_not_undoable_action()
            it = model.get_iter(path)
            section = model.section(it)
            section += '  ' + model.title(it)  # include the section title
            print("Opening section", section)

            # filename_tail = f'{model.filename(it)}'

            self.open_section(section, f'{model.filename(it)}')
            self.markdown_view.textbuffer.end_not_undoable_action()

    elif event.button == 3:  # right click
        # following is a way to do treeview.grab_focus without inadvertently selecting
        # the root element.
        with treeview.get_selection().handler_block(self.selection_changed_handler):
            treeview.grab_focus()

        treeview.set_cursor(path, column, 0)

        popup = create_popup(self, model, path)
        popup.show_all()
        popup.popup(None, None, None, None, event.button, event.time)

        return True  # event has been handled
    else:
        pass  # mouse not on a treeview item

def create_popup(self, model, path):
    popup = Gtk.Menu()
    it = Gtk.MenuItem("New section after selected")
    it.connect("activate", self.new_section_after, model, path)
    popup.add(it)
    it = Gtk.MenuItem("New subsection of selected")
    it.connect("activate", self.new_subsection_after, model, path)
    popup.add(it)
    it = Gtk.SeparatorMenuItem()
    popup.add(it)
    it = Gtk.MenuItem("Delete section")
    it.connect("activate", self.delete_section, model, model.get_iter(path))
    popup.add(it)

    return popup


def insert_into_db(self, title, relfilepath, parentid, section):
    # The new record will be inserted into the database
    self.summary.title = title
    self.summary.filename = relfilepath
    self.summary.parentid = parentid
    self.summary.section = section
    self.summary._in_db = False  # force insert rather than update

    self.summary.save()
    print(f'{title}, {relfilepath}, {parentid}, {section} written to db')

    return self.summary.pk  # return the database key of the inserted record

def modify_db_section(self, db_key, section):
    # The record held under db_key will have its section field updated
    # ====== get the record into self.summary
    self.summary.get(db_key)

    self.summary.id = db_key
    self.summary.section = section
    self.summary._in_db = True  # force update rather than insert

    self.summary.save()



class new_section_popup(Gtk.Dialog):
    def __init__(self, title, parent=None):
        # pyrefly: ignore  # bad-argument-type
        super().__init__(self)

        # Define a popup dialog to enter new [sub]section Title and File
        self.dlg_title = title
        self.set_title(title)
        self.parent = None
        self.flags = Gtk.DialogFlags.MODAL

        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        self.entry1 = Gtk.Entry()  # to enter the new section Title
        self.entry1.set_width_chars(30)

        # create a horizontal box to pack the entry and a label
        hbox1 = Gtk.HBox()
        hbox1.pack_start(Gtk.Label('Section title'), False, 5, 5)
        hbox1.pack_end(self.entry1, True, True, 0)

        self.entry2 = Gtk.Entry()  # to enter the new section file path
        self.entry2.set_placeholder_text('suffix .md will be added unless given')
        self.entry1.connect("activate", self.move_on, self.entry2)
        # allow the user to press Enter to do Ok
        self.entry2.connect("activate", self.response_to_dialog, self, Gtk.ResponseType.OK)
        hbox2 = Gtk.HBox()
        hbox2.pack_start(Gtk.Label('Section file'), False, 5, 5)
        hbox2.pack_end(self.entry2, True, True, 0)
        # add it and show it
        self.vbox.pack_start(hbox1, True, True, 0)
        self.vbox.pack_start(hbox2, True, True, 0)
        self.show_all()

    def move_on(self, widget, child):
        # used to allow 'Enter' in entry1 to focus entry2
        # 'Enter' in entry2 will terminate the dialog
        child.grab_focus()

    def response_to_dialog(self, entry, dialog, response):
        if response == Gtk.ResponseType.CANCEL:
            print("Response was cancel")  # ... and do nothing else
        self.response(response)

    def get_section_info(self,):
        text1 = ''
        text2 = ''
        # go go go
        response = self.run()
        if response != Gtk.ResponseType.CANCEL:
            # if it wasn't CANCEL it was OK
            text1 = self.entry1.get_text()  # desired section title
            text2 = self.entry2.get_text()  # desired section filename

        self.destroy()
        return text1, text2

def collect_refs(sorted_model, parent_iter, updated_parent_section):
    # Update the section number in any children of parent_iter (recursively)
    collected_refs = []

    sub_iter = sorted_model.iter_children(parent_iter)  # first child (or None)
    # index the children
    child_no = 1
    while sub_iter:
        cm_iter = sorted_model.convert_iter_to_child_iter(sub_iter)
        section = f"{updated_parent_section}.{str(child_no)}"
        print(f'Section must be updated to {section}')
        cm_ref = [cm_iter, section]
        collected_refs.append(cm_ref)

        # Update the section number in any children of sub_iter (recursively)
        collected_refs.extend(collect_refs(sorted_model, sub_iter, section))

        child_no += 1
        sub_iter = sorted_model.iter_next(sub_iter)

    return collected_refs

def init_markdown_file(desired_title, desired_filename):
    if desired_filename.endswith('.md'):  # as promised in the placeholder text
        relfilepath = f'{desired_filename}'
    else:
        relfilepath = f'{desired_filename}.md'

    # get the full (absolute) filepath and filename
    absfilepath = os.path.join(shared.markdown_directory, relfilepath)
    # write the initial Markdown heading to the file
    with open(absfilepath, 'w') as newfile:
        newfile.write(f'# {desired_title}\n')
    return relfilepath


def new_section_after(self, widget, sorted_model, selected_tree_path):

    # User wants to create a new section following the selected section at the same level.
    
    # We create a new record whose parent is the selected section's parent, and give it
    # a section number which immediately follows the selected section.

    # We then have to update all the section numbers in records following the selected
    # section at the same level or deeper (recursively).
    
    # Remember that the record is destined for the summary.db, which has
    #   0: title
    #   1: (relative) filepath
    #   2: parent id
    #   3: section
    #   4: database key
    
    # Calculate these fields for the new section record.
    desired_title, desired_filename = new_section_popup('New section after selected').get_section_info()

    # Create & initialise the markdown file for the new subsection
    relfilepath = init_markdown_file(desired_title, desired_filename)

    selected = sorted_model.get_iter(selected_tree_path)  # set 'selected' to selected section

    parentid = sorted_model.id(selected)  # new record's parentid (database field 'parentid')

    # Work out what its section number will be.
    tree_path_as_string = sorted_model.get_string_from_iter(selected)
    new_section = tree_path_to_following_section(tree_path_as_string)

    # Make up the new section record
    section_entry = [desired_title, relfilepath, parentid, new_section, None]  # database key unknown as yet


    selected_parent_iter = sorted_model.iter_parent(selected)  # selected's parent iter

    child_model = sorted_model.get_model()
    if selected_parent_iter:
        cm_parent = sorted_model.convert_iter_to_child_iter(selected_parent_iter)
    else:
        cm_parent = None


    # The new record will be inserted into the database, but before doing so, we
    # need to locate the first record whose section number will have to be updated.
    # This will be the start of a sequence of records whose section numbers must all
    # be updated. We don't do this yet, just record the necessary information.
    refs = []
    following_iter = sorted_model.iter_next(selected)  # first to be updated
    while following_iter:
        cm_iter = sorted_model.convert_iter_to_child_iter(following_iter)

        following_path_as_string = sorted_model.get_string_from_iter(following_iter)
        section = tree_path_to_following_section(following_path_as_string)

        cm_ref = [cm_iter, section]
        refs.append(cm_ref)

        # Must update the section number in any children of following_iter (recursively)
        refs.extend(collect_refs(sorted_model, following_iter, section))

        following_iter = sorted_model.iter_next(following_iter)

    # Now we have the required information, we can risk the changes that will be made
    # automatically by the sorting algorithm
    # so let's actually append the record to the cm_parent in child_model ...
    cm_appended_iter = child_model.append(cm_parent, section_entry)
    # ... and write the corresponding entry to the database
    print(*section_entry)
    db_key = self.insert_into_db(desired_title, relfilepath, parentid, new_section)
    # ... and now we can update the id (database key) field in the tree record
    child_model.set_value(cm_appended_iter, 4, int(db_key))

    # At last, we can do the update (in the child_model) for all the rows collected
    for ref in refs:
        cm_iter = ref[0]
        section = ref[1]
        # Do the update in the child_model ...
        was = child_model.section(cm_iter)
        child_model.set_section(cm_iter, section)
        now = child_model.section(cm_iter)

        # ... and in the database
        db_key = child_model.id(cm_iter)
        record = self.summary.get(db_key)
        record.section = now  # update using the id in the record
        record.save()
        print(f'Section {was} updated to {now}')


def new_subsection_after(self, widget, sorted_model, selected_tree_path):
    # User wants to create a new subsection of the selected section.
    # We create a new record whose parent is the selected section, and give it a section
    # number immediately following the last of the selected section's children (if any).

    # If there are currently no children of selected, the new record is inserted as the
    # first child.

    # In this case, we don't need to update any subsequent section numbers, because
    # there are none. To insert a new subsection in between existing subsections, use
    # the new_section_after function.

    # body of new_subsection_after begins
    desired_title, desired_filename = new_section_popup('New sub-section of selected').get_section_info()

    # Create & initialise the markdown file for the new subsection
    relfilepath = init_markdown_file(desired_title, desired_filename)

    parent = sorted_model.get_iter(selected_tree_path)  # set parent to selected section
    # Now we need to create a new child for parent and add it after parent's existing 
    # children, if any
    
    sub_iter = sorted_model.iter_children(parent)  # first child (or None)

    if sub_iter:    # parent already has children
       last_child_iter = None  # to avoid ref before assign warning
       # index the children
       while sub_iter:
           last_child_iter = sub_iter
           sub_iter = sorted_model.iter_next(sub_iter)
       # Calculate the section number for the new subsection
       tree_path_as_string = sorted_model.get_string_from_iter(last_child_iter)
       new_section = tree_path_to_following_section(tree_path_as_string)
    else:	# No existing children, so add as first child
        tree_path_as_string = sorted_model.get_string_from_iter(parent)
        new_section = tree_path_to_first_subsection(tree_path_as_string)
        
    parent_id = sorted_model.id(parent)

    section_list = [desired_title, relfilepath, parent_id, new_section, None]    # database key unknown as yet
    

    cm_parent = sorted_model.convert_iter_to_child_iter(parent)

    # append the record to the child model ...
    child_model = sorted_model.get_model()
    cm_appended_iter = child_model.append(cm_parent, section_list)
    # ... and write the corresponding entry to the database
    db_key = self.insert_into_db(desired_title, relfilepath, parent_id, new_section)
    # ... and now we can update the id (database key) field in the tree record
    child_model.set_value(cm_appended_iter, 4, int(db_key))

    self.toc_view.expand_all()


def tree_path_to_previous_section(thepath):
    thepath = thepath.rsplit(':')  # get a list of the path elements
    thepath[-1] = str(int(thepath[-1]) - 1)    # path to the previous section
    newpath = []
    for el in thepath:
        # pyrefly: ignore  # bad-argument-type
        newpath.append(str(int(el) + 1))
    print('newpath = ', newpath)
    return '.'.join(newpath)


def delete_section(self, widget, sorted_model, it):
    # Really need a confirmation dialog !!!!!!!!!!!
    # This command will deliberately NOT delete the associated Markdown file
    # Remove the database record
    print(f'You selected to delete section {sorted_model.section(it)}  {sorted_model.title(it)}')

    # All changes have to be done in the child model
    child_model = sorted_model.get_model()

    # The record will be deleted from the database, but before doing so, we
    # need to locate the first record whose section number will have to be updated.
    # This will be the start of a sequence of records whose section numbers must all
    # be updated. We don't do this yet, just record the necessary information.
    refs = []
    following_iter = sorted_model.iter_next(it)  # first to be updated
    while following_iter:
        print(f'Ref points to {sorted_model.title(following_iter)}')
        # Must update the section number in rows at the same level as following_iter
        cm_iter = sorted_model.convert_iter_to_child_iter(following_iter)
        # it has to be updated to the section number that logically follows
        section = tree_path_to_previous_section(sorted_model.get_string_from_iter(following_iter))

        cm_ref = [cm_iter, section]
        refs.append(cm_ref)

        # Must update the section number in any children of following_iter (recursively)
        refs.extend(collect_refs(sorted_model, following_iter, section))
        following_iter = sorted_model.iter_next(following_iter)

    # At last, we can do the update (in the child model) for all the rows collected
    for ref in refs:
        cm_iter = ref[0]
        section = ref[1]
        # Do the update in the child model ...

        was = child_model.section(cm_iter)
        child_model.set_section(cm_iter, section)
        now = child_model.section(cm_iter)

        # ... and in the database
        db_key = child_model.id(cm_iter)
        record = self.summary.get(db_key)
        record.section = now  # update using the id in the record
        record.save()
        print(f'Section {was} updated to {now}')

    # Remove the row from the database ...
    # ... and now remove the corresponding TreeStore row
    # ... and now remove the row from the database
    db_key = sorted_model.id(it)
    child_model.remove(sorted_model.convert_iter_to_child_iter(it))

    self.toc_view.expand_all()

    record = self.summary.get(db_key)
    record.delete()


def toc_scan(self):
    """
    Scans the model of the TOC treeview , yielding at each section a tuple (level, treeiter)
    """
    model = self.toc_view.get_model()
    it = model.get_iter_first()
    while it:
        yield (it)

        it2 = model.iter_children(it)
        while it2:
            yield (it2)

            it3 = model.iter_children(it2)
            while it3:
                yield (it3)

                it4 = model.iter_children(it3)
                while it4:
                    yield (it4)

                    it5 = model.iter_children(it4)
                    while it5:
                        yield (it5)

                        it6 = model.iter_children(it5)
                        while it6:
                            yield (it6)

                            it6 = model.iter_next(it6)

                        it5 = model.iter_next(it5)

                    it4 = model.iter_next(it4)

                it3 = model.iter_next(it3)

            it2 = model.iter_next(it2)

        it = model.iter_next(it)

def generate_btoc_html(self):
    # Generate the HTML for the Table of Contents.
    # The TOC HTML contains references to tags #ch{section} which must appear in the
    # content of each section.
    with open(os.path.join(shared.project_directory, '_pdf/btoc.html'), 'w') as f:
        f.write('<div class="contents">\n')
        f.write('<h1>Programming Python with GTK and SQLite</h1>\n')
        f.write('<h2>Contents</h2>\n')
        f.write('<ul class="toc">\n')
        level = 1

        scan = toc_scan(self)
        for it in scan:
            previous_level = level
            section = self.toc_view.get_model().get_value(it, 3)
            level = len(section.split('.'))

            if level > previous_level:
                f.write('<ul>\n')
            elif level < previous_level:
                f.write('</ul>\n')

            f.write(
                f'<li><a href="#ch{section}">{section} {self.toc_view.get_model().get_value(it, 0)}</a></li>\n')
        #
        f.write('</ul>\n')
        f.write('</ul>\n')
        f.write('</div>\n')

def export_to_pdf(self):  # sourcery skip: extract-duplicate-method, extract-method, low-code-quality
    # Export to pdf is done by combining all the .xhtml files of the book into one file
    # called book.html, including additions like the pdf meta-data, generated chapter/section
    # headings etc. and presenting the result to a suitable converter. Currently, we use Prince
    # (www.princexml.com), although paged.js may be worth investigation.

    self.pdf_directory = f"{shared.project_directory}/_pdf"
    # created/emptied if user does "export to pdf"
    os.chdir(self.pdf_directory)
    with codecs.open('{0}/book.html'.format(self.pdf_directory), 'w') as f:
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n")
        f.write("<head>\n")
        f.write('    <meta charset="utf-8" />\n')
        with open(f'{shared.project_directory}/book.json') as j:
            data = json.load(j)
            f.write(f"    <title> {data['title']} </title>\n")
            author = data['author']
            f.write(f'    <meta name="creator" content="{author}">\n')
            f.write(f'    <meta name="author" content="{author}">\n')
            date = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            f.write(f'    <meta name="date" content={date}>\n')

        f.write('    <link rel = "stylesheet" href = "github-markdown.css" type = "text/css" />\n')
        f.write('    <link rel = "stylesheet" href = "github-pygments.css" type = "text/css" />\n')
        f.write(
            '    <script src = "file:/home/chris/MDProject/Code/programming-python-with-gtk-and-sqlite/_book/_script/mermaid.min.js"></script>\n')
        f.write('    <script> mermaid.initialize({startOnLoad:true}) </script>\n')
        f.write('    <link rel = "stylesheet" href = "pdf_styles.css" type = "text/css" />\n')
        f.write("</head>\n")

    generate_btoc_html(self)

    print("Exporting to PDF")
    with codecs.open(f'{self.pdf_directory}/book.html', 'a') as f:
        f.write('<body>\n')
        with codecs.open(f'{self.pdf_directory}/btoc.html', 'r') as g:
            for line in g:
                f.write(line)

        f.write('<br/>\n')  # because if not we will start the body on a left page
        f.write('<br/>\n')  # because if not we will start the body on a left page
        f.write('<div class="body">\n')

    os.chdir(self.pdf_directory)

    scan = toc_scan(self)
    for it in scan:
        title = self.toc_view.get_model().get_value(it, 0)
        filepath = self.toc_view.get_model().get_value(it, 1)
        section = self.toc_view.get_model().get_value(it, 3)

        self.open_section(f"{section} {title}", filepath)
        print(f'opening section {section} {title}')

        with codecs.open(f'{shared.pdf_directory}/book.html', 'a') as f:
            # Top-level sections(numbered 1, 2, 3 etc) should always start on a right-hand page.
            # This is arranged by generating the following empty <div> in conjunction with the
            # CSS  .h1_top_level {break-before: right;} in pdf_styles.css.
            if len(section) == 1:
                f.write('<div class="h1_top_level" />')

            s = section.split('.')
            if len(s) <= 4:  # TOC to include levels 1-4
                print('Writing <div class="chapter">')
                f.write(f'<div id="ch{section}" class="chapter">\n')
            # Now get the markdown content of the section and generate the (x)html.
            mv = self.markdown_view
            start = mv.textbuffer.get_start_iter()
            end = mv.textbuffer.get_end_iter()
            f.write(mv.markdown(mv.textbuffer.get_text(start, end, False)))
            # Close the <div> for the TOC
            if len(s) <= 4:  # TOC to include levels 1-4
                f.write('</div>\n')

        print(f'written section {section} {title}')

    with codecs.open(f'{shared.pdf_directory}/book.html', 'a') as f:
        f.write('</div>\n')  # end of div class="body"
        f.write('</html>\n')  # end of html

    os.chdir(f'{shared.pdf_directory}')  # run prince in the _pdf directory
    # All image references in the html are of the form _images/<image file>,
    # which points to <project_directory>/_images. However, during development
    # these same references in the single .xhtml files point to
    # <project_directory>/_book/_images. Therefore, these two _image directories
    # must be identical.
    # The alternative would be to merge the "source" (markdown) and "target" (html)
    # into the same directory.
    subprocess.run("~/.local/bin/prince "
                   "frontmatter.html "  # Note btoc.html has been copied into book.html
                   "-s pdf_styles.css book.html -o book.pdf", shell=True)

