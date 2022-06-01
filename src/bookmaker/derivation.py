import re

__all__ = ['plugin_derivation']

EXTEND_BLOCK = re.compile(
            r'(!_)([\s\S]+?)'   # bullet ('!_') followed by text (as group(1)
            r'(?:\n{2,})'       # & possible further lines of text, terminated by a blank line
        )

EXTEND_ITEM = re.compile(
            r'([^\n]+)\n?'      # widget name (as group) terminated by \n (discarded)
        )

EXTEND_BULLET = re.compile(
            r'!_'               # the bullet characters (discarded)
        )

def parse_derivation(self, m, state):
    # print("Parse derivation called")
    children = parse_derivation_list(self, m.group(2))
    return {'type': 'extend_start',
            'children': children}

def parse_derivation_list(self, text):
    # print("parse_derivation_list called")
    global item_no

    cells = []  # the list of children of extend_start
    m = EXTEND_ITEM.match(text, 0)
    cells.append({
        'type': 'first_extend_item_start',
        'text': m.group(1),
        })

    text = EXTEND_ITEM.sub('', text, 1)
    while '\n' in text: # there is a following line
        if EXTEND_BULLET.match(text, 0):   # the line starts with the extend bullet
            text = EXTEND_BULLET.sub('', text, 1)   # remove the bullet characters from text
            m = EXTEND_ITEM.match(text, 0)          # extract the widget name
            cells.append({
                'type': 'extend_item_start',
                'text': m.group(1),
            })
        else:
            m = EXTEND_ITEM.match(text, 0)          # extract the widget name
            cells.append({
                'type': 'extend_item_same',
                'text': m.group(1),
            })

        text = EXTEND_ITEM.sub('', text, 1)     # remove the widget name from text

    # this is now the last line; just the bullet and widget name (no \n)
    text = EXTEND_BULLET.sub('', text, 1)       # remove the bullet characters
    cells.append({
        'type': 'extend_item_start',
        'text': text,                           # leaving just the widget name
    })
    # print("parse_derivation_list exited")
    return cells

item_no = 0     # used to control indentation in the list
indent = 0

def render_derivation_list(text):
    return "<div class='highlight'><pre>%s</pre></div>" % text

def render_first_extend_item(item):
    global item_no
    global indent
    item_no = 0
    indent = 0
    return "%s\n" % item  # no indentation or lineart

def render_extend_item(item):
    global item_no
    global indent
    indent = 3*item_no
    item_no += 1
    indent += 4*(item_no)

    return "%s<span class='lineart'>╰──</span>%s\n" % (' '*indent, item)

def render_extend_item_same(item):
    global item_no
    global indent
    indent = 3*item_no
    indent += 4*(item_no+1)

    return "%s<span class='lineart'>╰──</span>%s\n" % (' '*indent, item)

def plugin_derivation(md):
    md.block.register_rule('derivation', EXTEND_BLOCK, parse_derivation)
    md.block.rules.append('derivation')

    if md.renderer.NAME == 'html':
        md.renderer.register('extend_start', render_derivation_list)
        md.renderer.register('first_extend_item_start', render_first_extend_item)
        md.renderer.register('extend_item_start', render_extend_item)
        md.renderer.register('extend_item_same', render_extend_item_same)

