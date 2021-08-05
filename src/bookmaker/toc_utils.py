import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# Declare
popup = Gtk.Menu()


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

    # get a new model; the old one (if any) will no longer be referenced so should get garbage-collected
    self.toc_model = Gtk.TreeStore(str, str, int, int, int, int, int, int)
    self.toc_view.set_model(self.toc_model)

    def celldatafunction(column, cell, model, iter, user_data=None):
        section = str(model.get_value(iter, 2))
        sub = str(model.get_value(iter, 3))
        subsub = str(model.get_value(iter, 4))
        subsubsub = str(model.get_value(iter, 5))
        subsubsubsub = str(model.get_value(iter, 6))
        sub5 = str(model.get_value(iter, 7))

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
        section += '  ' + model.get_value(iter, 0)

        cell.set_property('text', section)
        return

    # Read from SUMMARY.md
    try:
        with open(os.path.join(self.project_directory, 'SUMMARY.md'), 'r') as summary:
            for line in summary:
                parts = line.partition('*')
                if parts[2]:  # to skip initial heading & blank line
                    parts2 = parts[2].partition('[')
                    parts22 = parts2[2].partition(']')

                    parts222 = parts22[2].partition('(')
                    parts2220 = parts222[2].partition(')')

                    if parts[0] == "":
                        piter = self.toc_model.append(None, [parts22[0], parts2220[0], 0, 0, 0, 0, 0, 0])
                    if parts[0] == "    ":
                        p2iter = self.toc_model.append(piter, [parts22[0], parts2220[0], 0, 0, 0, 0, 0, 0])
                    if parts[0] in ["        "]:
                        p3iter = self.toc_model.append(p2iter, [parts22[0], parts2220[0], 0, 0, 0, 0, 0, 0])
                    if parts[0] == "            ":
                        p4iter = self.toc_model.append(p3iter, [parts22[0], parts2220[0], 0, 0, 0, 0, 0, 0])
                    if parts[0] == "                ":
                        p5iter = self.toc_model.append(p4iter, [parts22[0], parts2220[0], 0, 0, 0, 0, 0, 0])

    except Exception as e:
        print(type(e))
        print(e)

    it = self.toc_model.get_iter_first()

    self.re_number()

    self.tvcolumn.set_cell_data_func(self.cell, celldatafunction)

    self.insert_inline_toc()

    # opening_section = self.cell.get_property('text')
    opening_section = self.toc_model.get_value(it, 2)
    title = self.toc_model.get_value(it, 0)
    return f"{opening_section} {title}"


def button_press_event(self, treeview, event):
    path, column, x, y = treeview.get_path_at_pos(int(event.x), int(event.y))

    # We click on the tree view in order to
    #   - go to a new article (by left clicking)
    #   OR
    #   - add a new section/subsection under the clicked entry
    #   OR
    #   - delete the clicked entry/article

    # Whichever of these actions is required, we need to record the file details for action
    # but save the current file (if dirty) first.
    # Since the file details belong to TV (self), don't update those yet.
    if event.button == 1:  # left click
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.MV.textbuffer.begin_not_undoable_action()

            model = treeview.get_model()
            section = str(model[path][2])
            sub = str(model[path][3])
            subsub = str(model[path][4])
            subsubsub = str(model[path][5])
            subsubsubsub = str(model[path][6])
            sub5 = str(model[path][7])

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
            section += '  ' + model[path][0]    # include the section title
            print("Opening section", section)

            req_filename_tail = model[path][1][:-3] # file details belong to TV (self)

            self.open_section(section, self.project_directory, req_filename_tail)
            self.MV.textbuffer.end_not_undoable_action()

    elif event.button == 3:  # right click
        # following is a way to do treeview.grab_focus without inadvertently selecting
        # the root element.
        with self.toc_view.get_selection().handler_block(self.selection_changed_handler):
            treeview.grab_focus()

        treeview.set_cursor(path, column, 0)
        self.popup = Gtk.Menu()
        it = Gtk.MenuItem("New section after selected")
        it.connect("activate", self.new_section_after, treeview.get_model(), path)
        self.popup.add(it)
        it = Gtk.MenuItem("New subsection of selected")
        it.connect("activate", self.new_subsection, treeview.get_model(), path)
        self.popup.add(it)
        it = Gtk.SeparatorMenuItem()
        self.popup.add(it)
        it = Gtk.MenuItem("Delete section")
        it.connect("activate", self.delete_section, treeview.get_model(), path)
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
    if response == Gtk.ResponseType.OK:
        text1 = popup.entry1.get_text()
        text2 = popup.entry2.get_text()
    else:   # response was Cancel
        text1 = ''
        text2 = ''

    popup.destroy()

    parent = None   # Not necessary to specify parent as we are setting sibling
    sibling = self.toc_model.get_iter(path)     # set sibling to selected section

    # get the (relative) filepath from the selected section
    dir = os.path.dirname(self.toc_model.get_value(sibling, 1))

    # create the new section entry with the same (relative) filepath and the given filename

    # From GTK3 documentation for Gtk.TreeStore ...
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



def delete_section(self, widget, model, path):
    # Get the TreeView selected row(s)
    selection = self.toc_view.get_selection()
    # selection.get_selected() returns a tuple
    # The first element is the treeview model (a ListStore)
    # The second element is a treeiter for the selected row
    model, it = selection.get_selected()
    print("You selected to delete", model[it][0])
    # Remove the ListStore row referenced by iter
    model.remove(it)

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



