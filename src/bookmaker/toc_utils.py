import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from ActiveRecord import ActiveRecord

# Declare
popup = Gtk.Menu()


class Toc_Utils(object):

    def __init__(self):
        pass


from functools import wraps
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

    def compare(model, row1, row2, user_data):
        key1 = 0
        key2 = 0
        for column in range(2, 6):  # level0..level4
            key1 = int(key1*100 + model.get_value(row1, column))
            key2 = int(key2*100 + model.get_value(row2, column))

        if key1 < key2:
            # print (f'{key1} < {key2}')
            return -1
        elif key1 == key2:
            # print (f'{key1} = {key2}')
            return 0
        else:
            # print (f'{key1} > {key2}')
            return 1

    # get a new model; the old one (if any) will no longer be referenced so should get garbage-collected
    self.toc_model = Gtk.TreeStore(str, str, int, int, int, int, int, int)
    # title, filename, level0, level1, level2, level3, level4, visited
    # 0      1         2       3       4       5       6       7
    # self.toc_view.set_model(self.toc_model)

    def celldatafunction(column, cell, model, iter, user_data=None):
        def argvalue(offset):
            value = str(model.get_value(iter, offset))
            if offset == 2:
                return value
            elif int(value) > 0:
                return f'.{value}'
            else:
                return ''

        text = ''.join([argvalue(offset) for offset in range(2, 6)])
        cell.set_property('text', f'{text} {model.get_value(iter, 0)}')
        return

    Summary = ActiveRecord.class_for_table(
        f'{self.project_directory}/{"summary.db"}', 'Summary', 'summary'
    )
    self.summary = Summary()
    for t in self.summary.all():
        if not t.level1:  # a level0 section
            section = f'{str(t.level0)} {t.title}'
            piter = self.toc_model.append(None,
                                          [t.title, t.filename, t.level0, t.level1, t.level2, t.level3, t.level4,
                                           t.id])
        elif not t.level2:  # a level1 section
            section = f'    {str(t.level0)}.{str(t.level1)} {t.title}'
            p2iter = self.toc_model.append(piter,
                                           [t.title, t.filename, t.level0, t.level1, t.level2, t.level3, t.level4,
                                            t.id])
        elif not t.level3:  # a level2 section
            section = f'        {str(t.level0)}.{str(t.level1)}.{str(t.level2)} {t.title}'
            p3iter = self.toc_model.append(p2iter,
                                           [t.title, t.filename, t.level0, t.level1, t.level2, t.level3, t.level4,
                                            t.id])
        elif not t.level4:  # a level3 section
            section = f'            {str(t.level0)}.{str(t.level1)}.{str(t.level2)}.{str(t.level3)} {t.title}'
            p4iter = self.toc_model.append(p3iter,
                                           [t.title, t.filename, t.level0, t.level1, t.level2, t.level3, t.level4,
                                            t.id])
        else:  # a level 4 section
            section = f'                {str(t.level0)}.{str(t.level1)}.{str(t.level2)}.{str(t.level3)} {t.title}'
            self.toc_model.append(p4iter,
                                  [t.title, t.filename, t.level0, t.level1, t.level2, t.level3, t.level4, t.id])


    self.tvcolumn.set_cell_data_func(self.cell, celldatafunction)

    self.sorted_model = Gtk.TreeModelSort(self.toc_model)
    self.sorted_model.set_default_sort_func(compare, None)
    self.sorted_model.set_sort_column_id(Gtk.TREE_SORTABLE_DEFAULT_SORT_COLUMN_ID, Gtk.SortType.ASCENDING)
    self.toc_view.set_model(self.sorted_model)
    self.toc_view.expand_all()

    # self.re_number()

    it = self.sorted_model.get_iter_first()
    opening_section = self.sorted_model.get_value(it, 2)
    title = self.sorted_model.get_value(it, 0)
    return f'{opening_section} {title}'


def button_press_event(self, treeview, event):
    path, column, x, y = treeview.get_path_at_pos(int(event.x), int(event.y))
    model = self.sorted_model.get_model()   # treeview is showing sorted_model
    path = self.sorted_model.convert_path_to_child_path(path)

    # We click on the tree view in order to
    #   - go to a new article (by left-clicking)
    #   OR  (by right-clicking)
    #   - add a new section/subsection under the clicked entry
    #   OR
    #   - delete the clicked entry/article

    # Whichever of these actions is required, we need to record the file details for action
    # but save the current file (if dirty) first.
    # Since the file details belong to TV (self), don't update those yet.
    if event.button == 1:  # left click
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.MV.textbuffer.begin_not_undoable_action()

            section = f'{str(model[path][2])}'  # level0 section
            for column in range(3, 6):  # level1..level4
                if model[path][column]: # if non-zero
                    section += f'.{str(model[path][column])}'
            section += '  ' + self.sorted_model[path][0]    # include the section title
            print("Opening section", section)

            req_filename_tail = model[path][1][:-3] # file details belong to TV (self)

            self.open_section(section, self.project_directory, req_filename_tail)
            self.MV.textbuffer.end_not_undoable_action()

    elif event.button == 3:  # right click
        # following is a way to do treeview.grab_focus without inadvertently selecting
        # the root element.
        with treeview.get_selection().handler_block(self.selection_changed_handler):
            treeview.grab_focus()

        treeview.set_cursor(path, column, 0)
        self.popup = Gtk.Menu()
        it = Gtk.MenuItem("New section after selected")
        it.connect("activate", self.new_section_after, model, path)
        self.popup.add(it)
        it = Gtk.MenuItem("New subsection of selected")
        it.connect("activate", self.new_subsection, treeview.get_model(), path)
        self.popup.add(it)
        it = Gtk.SeparatorMenuItem()
        self.popup.add(it)
        it = Gtk.MenuItem("Delete section")
        it.connect("activate", self.delete_section, model, model.get_iter(path))
        self.popup.add(it)
        self.popup.show_all()
        self.popup.popup(None, None, None, None, event.button, event.time)

        return True # event has been handled
    else:
        pass  # mouse not on a treeview item

    # if path:  # ... is not None
    #     print (event)

    return True


def new_section_popup(self, dlg_title, title_label, file_label):
    # Define a popup dialog to enter new [sub]section Title and File
    global popup
    popup = Gtk.Dialog(dlg_title, self.main_window, Gtk.DialogFlags.MODAL,
                        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK))

    def response_to_dialog(entry, dialog, response):
        if response == Gtk.ResponseType.CANCEL:
            print ("Response was cancel")
        popup.response(response)

    popup.entry1 = Gtk.Entry()    # to enter the new section Title
    popup.entry1.set_width_chars(30)

    # create a horizontal box to pack the entry and a label
    hbox1 = Gtk.HBox()
    hbox1.pack_start(Gtk.Label(title_label), False, 5, 5)
    hbox1.pack_end(popup.entry1, True, True, 0)

    popup.entry2 = Gtk.Entry()    # to enter the new section file path
    popup.entry2.set_placeholder_text('suffix .md will be added unless given')
    # allow the user to press Enter to do Ok
    popup.entry2.connect("activate", response_to_dialog, popup, Gtk.ResponseType.OK)
    hbox2 = Gtk.HBox()
    hbox2.pack_start(Gtk.Label(file_label), False, 5, 5)
    hbox2.pack_end(popup.entry2, True, True, 0)
    # add it and show it
    popup.vbox.pack_start(hbox1, True, True, 0)
    popup.vbox.pack_start(hbox2, True, True, 0)
    popup.show_all()

    return popup



def new_section_after(self, widget, model, path):
    # User wants to create a new section following the selection at the same level.
    # Define a popup dialog to enter new section Title and File
    global popup
    popup = self.new_section_popup('New section after selected', 'Section title', 'Section file ')
    # go go go
    response = popup.run()
    if response == Gtk.ResponseType.CANCEL:
        text1 = ''
        text2 = ''
    else:  # if it wasn't CANCEL it was OK
        Summary = ActiveRecord.class_for_table(
            f'{self.project_directory}/{"summary.db"}', 'Summary', 'summary'
        )
        summary = Summary()

        text1 = popup.entry1.get_text() # desired section title
        text2 = popup.entry2.get_text() # desired section filename

        parent = None  # Not necessary to specify parent as we are setting sibling
        sibling = model.get_iter(path)  # set sibling to selected section

        # create the new section entry with the same (relative) filepath and the given filename
        # get the (relative) filepath from the selected section
        dir = os.path.dirname(self.toc_model.get_value(sibling, 1))
        if text2.endswith('.md'):   # as promised in the placeholder text
            filepath = os.path.join(dir, f'{text2}')
        else:
            filepath = os.path.join(dir, f'{text2}.md')

        # From GTK3 documentation for Gtk.TreeStore ...
        # The insert_after() method inserts a new row after the row pointed to by sibling. If sibling is
        # None, then the row will be prepended to the beginning of the children of parent. If parent and
        # sibling are None, then the row will be prepended to the toplevel. If both sibling and parent
        # are set, parent must be the parent of sibling. When sibling is set, parent is optional. This
        # method returns a Gtk.TreeIter pointing at the new row.

        section_list = [text1, filepath, model[path][2]] # level0 section
        for column in range(3, 6):  # level1..level4
            if model[path][column + 1]:  # if next column zero, this is last subsection
                section_list.append(model[path][column])
            else:
                section_list.append(model[path][column] + 1)
                break

        while column <= 7:
            section_list.append(0)

        it = model.insert_after(parent, sibling, section_list)

        # # get the full (absolute) filepath and filename
        # filepath = os.path.join(self.project_directory, filepath)
        # write the initial heading to the file
        with open(filepath, 'w') as newfile:
            newfile.write('This will be replaced before user sees it\n'.format(text1))

        # The new record will be inserted into the database
        summary.title = text1
        summary.filename = filepath
        summary.level0 = section_list[2]
        summary.level1 = section_list[3]
        summary.level2 = section_list[4]
        summary.level3 = section_list[5]
        summary.level4 = section_list[6]
        summary.save()

        #
        #
        self.re_number()

    popup.destroy()


def new_subsection(self, widget, model, path):  # sourcery skip: assign-if-exp
    # User wants to create a new subsection of the selected section. We need to
    # skip over any existing subsections and create this as the last.
    #
    # Define a popup dialog to enter new section Title and File
    global popup
    popup = self.new_section_popup('New subsection of selected', 'Section title', 'Section file ')
    # go go go
    response = popup.run()
    if response == Gtk.ResponseType.CANCEL:
        text1 = ''
        text2 = ''
    else:   # if it wasn't CANCEL it was OK
        text1 = popup.entry1.get_text()
        text2 = popup.entry2.get_text()

        parent = self.toc_model.get_iter(path)              # the selected section
        kids = self.toc_model.iter_n_children(parent)       # how many subsections already?
        if kids:    # If parent has any existing children, new sub goes after last existing
            sibling = self.toc_model.iter_nth_child(parent, kids-1)    # its last child
        else:       # If parent has no children, this goes as first
            sibling = None


        # get the (relative) filepath from the selected section
        # If parent has existing children, take the filepath from the last existing child
        dir = os.path.dirname(self.toc_model.get_value(parent, 1))

        # create the new section entry with the same (relative) filepath and the given filename

        # Gtk.TreeStore.insert_after
        #
        #     def insert_after(parent, sibling, row=None)
        #
        # parent :
        # 	a Gtk.TreeIter, or None
        #
        # sibling :
        # 	a Gtk.TreeIter, or None
        #
        # row :
        # 	a tuple or list containing ordered column values to be set in the new row
        #
        # Returns :
        # 	a Gtk.TreeIter pointing to the new row
        #
        # The insert_after() method inserts a new row after the row pointed to by sibling. If sibling is
        # None, then the row will be prepended to the beginning of the children of parent. If parent and
        # sibling are None, then the row will be prepended to the toplevel. If both sibling and parent
        # are set, parent must be the parent of sibling. When sibling is set, parent is optional. This
        # method returns a Gtk.TreeIter pointing at the new row.
        filepath = os.path.join(dir, f'{text2}.md')
        it = self.toc_model.insert_after(parent, sibling, (text1, filepath, 0, 0, 0, 0, 0, 0))

        # get the full (absolute) filepath and filename
        filepath = os.path.join(self.project_directory, filepath)
        # write the initial Markdown heading to the file
        with open(filepath, 'w') as newfile:
            newfile.write('# {}\n'.format(text1))

        self.re_write_summary()
        self.re_number()

    popup.destroy()

def delete_section(self, widget, model, iter):
    print("You selected to delete", model[iter][0])
    # Remove the database record
    recd = model[iter][7]   # get the 'id' field from the record
    self.summary.delete(recd)
    # TreeStore row referenced by iter
    model.remove(iter)

    self.re_write_summary()
    self.re_number()

def toc_scan(self):
    """
    Scans the model of the TOC treeview , yielding at each section a tuple (level, treeiter)
    """
    it = self.toc_model.get_iter_first()
    while it:
        yield (0, it)

        it2 = self.toc_model.iter_children(it)
        while it2:
            yield (1, it2)

            it3 = self.toc_model.iter_children(it2)
            while it3:
                yield (2, it3)

                it4 = self.toc_model.iter_children(it3)
                while it4:
                    yield (3, it4)

                    it5 = self.toc_model.iter_children(it4)
                    while it5:
                        yield (4, it5)

                        it6 = self.toc_model.iter_children(it5)
                        while it6:
                            yield (5, it6)

                            it6 = self.toc_model.iter_next(it6)

                        it5 = self.toc_model.iter_next(it5)

                    it4 = self.toc_model.iter_next(it4)

                it3 = self.toc_model.iter_next(it3)

            it2 = self.toc_model.iter_next(it2)

        it = self.toc_model.iter_next(it)


def re_number(self):
    scan = self.toc_scan()  # we need a new generator
    level0 = 0

    for it in scan:
        if it[0] == 0:
            level0 += 1
            self.toc_model.set_value(it[1], 2, level0)
            level1 = 0
            level2 = 0
            level3 = 0
            level4 = 0
            level5 = 0

        elif it[0] == 1:
            level1 += 1
            self.toc_model.set_value(it[1], 2, level0)
            self.toc_model.set_value(it[1], 3, level1)
            level2 = 0

        elif it[0] == 2:
            level2 += 1
            self.toc_model.set_value(it[1], 2, level0)
            self.toc_model.set_value(it[1], 3, level1)
            self.toc_model.set_value(it[1], 4, level2)
            level3 = 0

        elif it[0] == 3:
            level3 += 1
            self.toc_model.set_value(it[1], 2, level0)
            self.toc_model.set_value(it[1], 3, level1)
            self.toc_model.set_value(it[1], 4, level2)
            self.toc_model.set_value(it[1], 5, level3)
            level4 = 0

        elif it[0] == 4:
            level4 += 1
            self.toc_model.set_value(it[1], 2, level0)
            self.toc_model.set_value(it[1], 3, level1)
            self.toc_model.set_value(it[1], 4, level2)
            self.toc_model.set_value(it[1], 5, level3)
            self.toc_model.set_value(it[1], 6, level4)
            level5 = 0

    # The following line is required to make visible a new section
    # added after a previously unexpanded entry
    self.toc_view.expand_all()



