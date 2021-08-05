import codecs
import os
import shutil

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import GLib, Gtk, WebKit2

html_header = """
<!DOCTYPE html>
<html xml:lang="en" lang="en" xmlns="http://www.w3.org/1999/xhtml"
                              xmlns:epub="http://www.idpf.org/2007/ops">
<head>
<title>dummy to satisfy epucheck</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
"""
html_header2 = """
<style>
    .markdown-content {
        min-width: 200px;
        max-width: 790px;
        margin: 0 auto;
        padding: 30px;
    }
    .center {
        display:block;
        margin-left: auto;
        margin-right: auto;
    }
    .inline {
        display:inline;
    }
    code {
        background-color: #e6e6e6;
    }        
    table, th, td {
        border: 1px solid black;
        padding: 5px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    tr {
        vertical-align: top;
    }

</style>
"""
html_header3 = """
    <script src="file:{0}/mermaid.min.js"></script>
"""
html_header4 = """
    <script>mermaid.initialize({startOnLoad:true});</script>
</head>
"""

article_prefix = """
<body>
<article class="markdown-content">
"""

class PREview(WebKit2.WebView):

    def __init__(self, TV):
        super(self.__class__, self).__init__()

        self.TV = TV
        self.TV.PV = self

        # Make the HTML viewable area
        self.wf = self.get_window_properties()

        # ws = self.get_settings()
        # ws.set_property('enable-javascript', True)
        #
        # # wf = self.wv.get_window_features()
        # # wf.set_property('scrollbar-visible', False)
        # self.set_settings(ws)

        ws = self.get_settings()
        ws.set_enable_javascript(True)
        ws.set_enable_write_console_messages_to_stdout(True)
        self.set_settings(ws)
        # print('Enable javascript is', ws.get_enable_javascript())

        self.syncscroll_instance = None

        self.connect('load-changed', self.on_webview_load_changed)

    def on_webview_load_changed(self, the_webview, the_event):
        if the_event == WebKit2.LoadEvent.FINISHED:
            self.syncscroll_instance.on_inscroll_adj_value_changed(0)
            # print('Load finished', the_webview)

    def print_caller_name(stack_size=3):
        def wrapper(fn):
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
    def reload(self, rendered):
        # The purpose of this function is solely to display the rendered html in the preview window.
        #
        # To do this we use css files held within the application. These must be identical to those
        # which will be used as part of the book we are developing, but need not be the same files.
        #
        # The application files are in <project>/src/bookmaker/css_resources which installs as
        # /usr/local/lib/python3.8/dist-packages/bookmaker/css_resources.
        #
        # Normally the css files for the book will be initialised from the application css files if
        # they do not exist at the start of a session. See toc_view.open_gitbook_folder().
        #
        # The book css files must be held within the book since the book (in whatever format) must be
        # readable independent of this application. They will be found in <book-project>/_book/_css
        # or wherever that ends up in the final epub or pdf.


        html_file = '{0}/{1}.xhtml'.format(
            self.TV.book_directory,
            self.TV.filename_tail)

        html_file_dir = os.path.split(html_file)[0]
        os.chdir(html_file_dir)


        css_directory = self.TV.css_directory
        # print(f'directory of pre_view.py is {css_directory}')
        # print(f'pre_view css from {css_directory}')

        # First we display the xhtml generated from the Markdown in the preview pane
        href1 = "{0}/github-markdown.css".format(os.path.abspath(css_directory))
        href2 = "{0}/github-pygments.css".format(os.path.abspath(css_directory))

        self.htmlstr = (html_header +
            f'<link rel = "stylesheet" href = "{href1}" type = "text/css" />\n' +
            f'<link rel = "stylesheet" href = "{href2}" type = "text/css" />\n' +
            html_header2 +
            html_header3.format(self.TV.book_directory + '/_script') +
            html_header4 +
            article_prefix
        + rendered
        + '\n</article>\n</body></html>')
        the_bytes = GLib.Bytes(str.encode(self.htmlstr))
        # print(the_bytes.get_data())
        self.load_bytes(the_bytes, "text/html", "utf8", "file://{0}".format(html_file_dir))
        self.set_editable(False)

    def save_rendered_html(self, project_directory, filename_tail):
        with codecs.open(f'{project_directory}/_book/{filename_tail}.xhtml', 'w') as f:
            f.write(self.htmlstr)
            print('PV: Written to .xhtml file {0}'.format(f.name))


