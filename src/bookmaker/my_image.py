import re

from mistune.util import ESCAPE_TEXT, PUNCTUATION, escape_url, unikey

__all__ = ['plugin_my_image']


ESCAPE_CHAR = re.compile(r'\\([' + PUNCTUATION + r'])')
LINK_TEXT = r'(?:\[(?:\\.|[^\[\]\\])*\]|\\.|`[^`]*`|[^\[\]\\`])*?'

#: link or image syntax::
#:
#: [text](/link "title")
#: ![alt](/src "title")
BLOCK_IMAGE_PATTERN = (
        r'!\[(' + LINK_TEXT + r')\]\(\s*)'
)

INLINE_IMAGE_PATTERN = (
        r'&\[\]\(\s*)'
)


def parse_inline_image(self, m, state):
    line = m.group(0)
    text = m.group(1)
    link = ESCAPE_CHAR.sub(r'\1', m.group(2))
    if link.startswith('<') and link.endswith('>'):
        link = link[1:-1]

    title = m.group(3)
    if title:
        title = ESCAPE_CHAR.sub(r'\1', title[1:-1])

    if line[0] == '!':
        return 'image', escape_url(link), text, title

    return self.tokenize_link(line, link, text, title, state)



def render_inline_math(renderer, text):
    return r'<span class="math">\(' + text + r'\)</span>'


def plugin_my_image(md):
    pass
    # md.inline.register_rule(
    #     'inline_image', INLINE_IMAGE_PATTERN, parse_inline_image)
    #
    # md.inline.rules.insert(0, 'image')
    # (   'image',
    #     INLINE_IMAGE_PATTERN,
    #     parse_inline_image
    # )


