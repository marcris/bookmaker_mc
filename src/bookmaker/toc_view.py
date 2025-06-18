import gi

gi.require_version("Gdk", "3.0")
# gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
import os

#from src import ActiveRecord
from ActiveRecord import ActiveRecord
# pyrefly: ignore  # missing-module-attribute
from gi.repository import Gtk

# pyrefly: ignore  # import-error
import about
# pyrefly: ignore  # import-error
import shared
# pyrefly: ignore  # import-error
from markdown_view import MARKDOWNview

from functools import wraps

XHTML_EXT = '.xhtml'


# # An alternative formulation of namedtuples
#
# import operator
# import types
# import sys
#
# def named_tuple(classname, fieldnames):
#     # Populate a dictionary of field property accessors
#     cls_dict = { name: property(operator.itemgetter(n))
#                  for n, name in enumerate(fieldnames) }
#
#     # Make a __new__ function and add to the class dict
#     def __new__(cls, *args):
#         if len(args) != len(fieldnames):
#             raise TypeError(f'Expected {len(fieldnames)} arguments, not {len(args)}')
#         return tuple.__new__(cls, (args))
#
#     cls_dict['__new__'] = __new__
#
#     # Make the class
#     cls = types.new_class(classname, (tuple,), {},
#                            lambda ns: ns.update(cls_dict))
#     cls.__module__ = sys._getframe(1).f_globals['__name__']
#     return cls


# Layout of a row in the TreeModel
field_names = 'title', 'filename', 'parentid', 'section', 'id'
# section title for TOC, associated content file, parent row db key (or 0), section number for TOC, row's own db key


class SortedModel(Gtk.TreeModelSort):

    def __init__(self, child_model):
        # pyrefly: ignore  # unexpected-keyword
        super().__init__(model=child_model)

        self.child_model = child_model

    def title(self, it):
        return self[it][0]

    def filename(self, it):
        return self[it][1]

    def parentid(self, it):
        return self[it][2]

    def section(self, it):
        return self[it][3]

    def id(self, it):
        return self[it][4]


class ChildModel(Gtk.TreeStore):

    def __init__(self, *args):
        super().__init__(*args)

    def title(self, it):
        return self[it][0]

    def filename(self, it):
        return self[it][1]

    def parentid(self, it):
        return self[it][2]

    def section(self, it):
        return self[it][3]

    def id(self, it):
        return self[it][4]

    def set_section(self, it, value):
        self.set_value(it, 3, value)


# # Layout of a row in the sorted model tree
# field_names = {
#     'title':    0,  # section title for TOC
#     'filename': 1,  # associated content file
#     'parentid': 2,  # parent row db key (or 0)
#     'section':  3,  # section number for TOC
#     'id':       4,  # row db key
# }

@staticmethod
def error_box(parent, message_text):
    message = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK)
    message.set_markup('<span size="xx-large" weight="heavy">Error</span>')
    message.format_secondary_text(message_text)
    message.run()
    message.destroy()

class TOCview(Gtk.ScrolledWindow):
    # pyrefly: ignore  # import-error
    from toc_utils import (
        button_press_event,
        # table_of_contents,
        export_to_pdf,
    )

    # pyrefly: ignore  # bad-function-definition
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
    # @print_caller_name(4)
    def table_of_contents(self):
        # Called from the main program.to display the TOC in the sidebar
        sdict = {}  # module-level global: cross-reference key = child.id vs. value = parent.id

        # Set up access to the database <project_directory>/summary.db
        Summary = ActiveRecord.class_for_table(
            # pyrefly: ignore  # bad-argument-type
            f'{shared.project_directory}/summary.db', 'Summary', 'summary'
        )
        # pyrefly: ignore  # implicitly-defined-attribute
        self.summary = Summary()

        # get a new model; the old one (if any) will no longer be referenced so should get garbage-collected
        self.toc_model = ChildModel(str, str, int, str, int)

        # title, filename, parentid, section, id
        # 0      1         2         3        4

        # Define how to sort the rows of toc_model producing sorted_model.
        # The rows are sorted as a hierarchy on the section numbers.
        # Note: it is sorted model that is displayed as the table of contents
        def compare(model, row1, row2, user_data):
            # Using two rows so avoid the caching in model.get_record
            parts1 = model.section(row1).split('.')
            parts2 = model.section(row2).split('.')

            # What to do if comparing section numbers at different levels, e.g. 2.6.2 vs 2.6.2.1
            # Experimentally, this never happens; code in the model presumably handles it???????
            if len(parts1) < len(parts2):
                print(f'len({parts1}) < len({parts2})')
                return -1
            elif len(parts1) > len(parts2):
                print(f'len({parts1}) > len({parts2})')
                return 1

            # so now the two lists are equal in length, so
            # we can compare the actual values of the parts.
            value1 = value2 = 0
            # make up a composite integer from each list
            for part in range(len(parts1)):
                value1 = value1 * 1000 + int(parts1[part])
                value2 = value2 * 1000 + int(parts2[part])
            # compare the composite values
            if value1 < value2:
                # print(f'value1 {value1} < value2 {value2}')
                return -1
            elif value1 > value2:
                # print(f'value1 {value1} > value2 {value2}')
                return 1

            # Duplicate section number: value1 {value1} = value2 {value2}')
            # If this happens under normal circumstances, e.g. on initialising the tree
            # structure from the database, it would be an error. However, it will occur
            # temporarily while re-numbering sections after inserting a new section or
            # subsection. Need to distinguish the error case, so we can tell the user.
            return 0

        def celldatafunction(column, cell, model, iter, user_data=None):
            # Generate the text "<section> <title>
            # Use this celldatafunction on the (only) cell in the display
            cell.set_property('text', f'{model.section(iter)} {model.title(iter)}')


        self.tvcolumn.set_cell_data_func(self.cell, celldatafunction)

        # Read in the database records and build the treestore
        # Only call this once, so we can assume sdict is empty
        for t in self.summary.all():
            if t.parentid == 0:  # a level0 section, e.g. '2' as '1'
                sdict[t.id] = self.toc_model.append(None,
                                                    [t.title, t.filename, t.parentid, t.section, t.id])
            else:
                sdict[t.id] = self.toc_model.append(sdict[t.parentid],
                                                    [t.title, t.filename, t.parentid, t.section, t.id])

        # sdict[t.id] contains the treemodel iterator pointing where the new record has been appended
        # calculate the corresponding section number and overwrite that read from the database
        # appended_path = self.toc_model.get_string_from_iter(sdict[t.id])
        # appended_section = self.tree_path_to_section(appended_path)
        # self.toc_model.set_section(sdict[t.id], appended_section)
        #
        self.toc_model.set_default_sort_func(compare, None)
        self.toc_model.set_sort_column_id(Gtk.TREE_SORTABLE_DEFAULT_SORT_COLUMN_ID, Gtk.SortType.ASCENDING)
        # pyrefly: ignore  # implicitly-defined-attribute, missing-attribute
        self.sorted_model = SortedModel(self.toc_model)
        self.toc_view.set_model(self.sorted_model)
        self.toc_view.expand_all()

        # Set up to open the first secction in the list
        it = self.sorted_model.get_iter_first()

        toc_first_section = self.sorted_model.section(it)
        toc_first_title = self.sorted_model.title(it)
        toc_first_file = self.sorted_model.filename(it)
        return toc_first_file, f'{toc_first_section} {toc_first_title}'

    def tree_path_to_section(self, thepath):
        thepath = thepath.rsplit(':')  # get a list of the path elements
        newpath = []
        for el in thepath:
            # pyrefly: ignore  # bad-argument-type
            newpath.append(str(int(el) + 1))
        return '.'.join(newpath)

    def tree_path_to_following_section(self, thepath):
        thepath = thepath.rsplit(':')  # get a list of the path elements
        thepath[-1] = str(int(thepath[-1]) + 1)    # path to the following section
        newpath = []
        for el in thepath:
            # pyrefly: ignore  # bad-argument-type
            newpath.append(str(int(el) + 1))
        return '.'.join(newpath)

    def __init__(self, main_window):
        # pyrefly: ignore  # invalid-argument
        super(self.__class__, self).__init__()

        self.main_window = main_window

        # if not hasattr(self, 'gsettings'):
        #     self.gsettings = self.find_settings()
        # self.recentbooks = deque([], maxlen=9)

        # -------------------------------------------------------------
        # Set up the treeview for the table of contents
        # -------------------------------------------------------------

        self.toc_view = Gtk.TreeView()
        self.toc_model = None  # initially

        self.toc_view.set_show_expanders(False)
        self.toc_view.set_level_indentation(30)

        self.toc_view.connect("button-press-event", self.button_press_event)
        self.popup = None  # for use as context menu

        selection = self.toc_view.get_selection()
        self.selection_changed_handler = selection.connect(
            "changed", self.on_toc_selection_changed
        )

        # create the TreeViewColumn
        self.tvcolumn = Gtk.TreeViewColumn("Table of Contents")
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
        self.tvcolumn.add_attribute(self.cell, 'text', 0)

        self.markdown_view = MARKDOWNview()

        os.chdir(shared.project_directory)  # Always work in the project directory

        toc_first_file, toc_first = self.table_of_contents()    # returns e.g. 'README.md', '1 Introduction'
        print(f"Initially opening {toc_first} in {toc_first_file}")
        shared.tail = toc_first_file
        self.open_section(toc_first, toc_first_file)

        self.add(self.toc_view)
        self.show_all()

    def on_toc_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            print("Selection changed to", model.title(treeiter))

            # Before doing ANYTHING else, save the current changes if any
            self.markdown_view.save_if_dirty(shared.tail)

            # pyrefly: ignore  # implicitly-defined-attribute
            self.filename_path = os.path.join(
                shared.markdown_directory, model.filename(treeiter)
            )
            print(f"Opening section {model.section(treeiter)} in {self.filename_path}")
            self.force_first_line(f"{model.section(treeiter)} {model.title(treeiter)}")

            shared.tail = model.filename(treeiter)

    # @print_caller_name(4)
    def open_section(self, section, selected_filename_tail):
        self.markdown_view.save_if_dirty(shared.tail)  # save the current changes, if any

        self.filename_path = os.path.join(
            shared.markdown_directory, selected_filename_tail
        )

        print(f"Opening section {section} in {self.filename_path}")
        self.force_first_line(section)

        print(f'Old tail = {shared.tail}')
        shared.tail = selected_filename_tail
        print(f'New tail = {shared.tail}')

    def force_first_line(self, section):
        try:
            with open(f"{self.filename_path}", "r", encoding="utf-8") as f:
                print(f"force_first_line on {self.filename_path}")
                f.readline()  # read and discard existing first line
                text = f.read(-1)  # rest of the file

                # about.main()  should have been called from init.py, so the
                # info we require should already be set.
                self.markdown_view.textbuffer.set_text(
                    "# {0}\n{1}".format(section, text)
                )  # generated first line replacement + rest of content as was

                # Changed signal from textbuffer handled by markdown_view.text_modified()
                # which will set is_dirty flag True
                self.markdown_view.is_dirty = False  # we just 'modified' it

                self.main_window.set_title(
                    f"{about.NAME} - {about.VERSION}\t\t\t\t\t\t{section}"
                )


        except FileNotFoundError as e:
            error_box(None, f"{e.filename}\n\n{e.args[1]}")

