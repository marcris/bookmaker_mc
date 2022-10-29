import re

__all__ = ['plugin_my_extra']

PUNCTUATION = r'''\\!"#$%&'()*+,./:;<=>?@\[\]^`{}|_~-'''
ESCAPE_CHAR = re.compile(r'\\([' + PUNCTUATION + r'])')

# Implement underscore emphasis
# underscore_emphasis syntax looks like: '_word_'

# The pattern '__word__' is now reserved for Python "dunder" methods
# (and not specially handled so it appears literally in the HTML)
USCORE_PATTERN = (
    r'\b_(?=[^_])([\s\S]*?)_\b'
)

# Superscript pattern; allows text wrapped in ^ (circumflex). Text can
# include any combination of whitespace & non-whitespace; just not the
# circumflex, which terminates the pattern.
SUP_PATTERN = (
    r'\^([\s\S]*?)\^'
)

#: alternative image syntax::
#  I don't understand all the regex; all I want is an alternative
#  syntax to insert images inline with text, so just use # instead
#  of the normal ! introducer, and parse normal as 'image' in the
#  inline_parser and this as 'inline_image'.
#:
#: #[alt](/src)
INLINE_IMAGE_PATTERN = (
        r'#?\[([\s\S]*?)\]\(([A-Za-z0-9./_]+)\)')

# I want to extend the facility for code highlighting to inline code.
# This involves replacing the CODESPAN_PATTERN. My current attempts
# works but invalidates the original syntax, requiring language to be
# specified even if it's "text".
MY_CODESPAN_PATTERN = ( # `<language code><space or newline><code>`
    r'(`)([^ \n]*)(?: |/n)([\s\S.]*?)(?:`)'
)


def parse_uscore(self, m, state):
    text = m.group(1)
    return 'uscore', self.render(text, state)

def render_html_uscore(text):
    return '<u>' + text + '</u>'

def parse_sup(self, m, state):
    text = m.group(1)
    return 'sup', self.render(text, state)

def render_html_sup(text):
    return '<sup>' + text + '</sup>'

def parse_inline_image(self, m, state):
    text = m.group(1)
    link = m.group(2)
    return 'inline_image', link, text

def parse_my_codespan(self, m, state):
    lang = m.group(2)
    code = m.group(3)
    print(f'parsing my_codespan as {lang}, {code}|')
    return 'my_codespan', lang, code

def render_inline_image(src, alt):
    s = '<img src="' + src + '" alt="' + alt + '" style="vertical-align:middle"'
    return s + ' />'

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html

class CodeHtmlFormatter(html.HtmlFormatter):

    def wrap(self, source):
        return self._wrap_code(source)

    def _wrap_code(self, source):
        # yield 0, '<code>'
        for i, t in source:
            if i == 1:
                # it's a line of formatted code
                t += '<br>'
            yield i, t
        # yield 0, '</code>'

def render_my_codespan(lang, text):
    print(f'rendering my_codespan ({lang}, {text})')
    lexer = get_lexer_by_name(lang)  # , stripall=True)
    formatter = html.HtmlFormatter(nowrap=True)
    hl =  highlight(text, lexer, formatter)[0:-1]
    print(repr(hl), '|')
    print('---------')
    return '<code>' + hl + '</code>'


def plugin_my_extra(md):
    md.inline.register_rule(
        'uscore', USCORE_PATTERN, parse_uscore)
    md.inline.register_rule(
        'sup', SUP_PATTERN, parse_sup)
    md.inline.register_rule(
        'inline_image', INLINE_IMAGE_PATTERN, parse_inline_image)
    md.inline.register_rule(
        'my_codespan', MY_CODESPAN_PATTERN, parse_my_codespan)

    # allow for asterisk_emphasis only; subvert previous underscore_emphasis
    md.inline.rules.remove('underscore_emphasis')
    md.inline.rules.remove('codespan')
    md.inline.rules.append('uscore')
    md.inline.rules.append('sup')
    md.inline.rules.append('my_codespan')

    md.inline.rules.append('inline_image')

    if md.renderer.NAME == 'html':
        md.renderer.register('uscore', render_html_uscore)
        md.renderer.register('sup', render_html_sup)
        md.renderer.register('inline_image', render_inline_image)
        md.renderer.register('my_codespan', render_my_codespan)
