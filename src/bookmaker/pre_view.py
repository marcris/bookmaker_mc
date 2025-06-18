import gi

#gi.require_version("WebKit2", "4.1")
import os

#from src import shared
# pyrefly: ignore  # import-error
import shared

print (shared.__file__, shared.tail)

gi.require_version("WebKit2", "4.1")
# pyrefly: ignore  # missing-module-attribute
from gi.repository import GLib, WebKit2
# pyrefly: ignore  # import-error
from html_bits import (article_prefix, html_header, html_header2, html_header3,
                 html_header4)


class PREview(WebKit2.WebView):
    syncscroll_instance = None

    def __init__(self):
        # pyrefly: ignore  # invalid-argument
        super(self.__class__, self).__init__()

        self.htmlstr = None

        # Make the HTML viewable area
        self.wf = self.get_window_properties()

        ws = self.get_settings()
        ws.set_enable_javascript(True)
        ws.set_enable_write_console_messages_to_stdout(True)
        self.set_settings(ws)

        self.connect("load-changed", self.on_webview_load_changed)

    def on_webview_load_changed(self, the_webview, the_event):
        if self.syncscroll_instance and the_event == WebKit2.LoadEvent.FINISHED:  # When loaded scroll to beginning
            self.syncscroll_instance.on_inscroll_adj_value_changed(0)

    @staticmethod
    def print_caller_name(stack_size=3):
        def wrapper(fn):
            def inner(*args, **kwargs):
                import inspect

                stack = inspect.stack()

                s = "{index:>5} : {module:^25} : {name}"
                callers = [
                    "",
                    s.format(index="level", module="module", name="name"),
                    "-" * 50,
                ]

                for n in reversed(list(range(1, stack_size))):
                    module = inspect.getmodule(stack[n][0])
                    callers.append(
                        # pyrefly: ignore  # missing-attribute
                        s.format(index=n, module=module.__name__, name=stack[n][3])
                    )

                callers.append(
                    s.format(index=0, module=fn.__module__, name=fn.__name__)
                )
                callers.append("")
                print("\n".join(callers))

                fn(*args, **kwargs)

            return inner

        return wrapper

    # @print_caller_name(4)
    def load_rendered(self, markdown_view, rendered):
        print(shared.__file__, shared.tail)

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
        # readable independent of this application. They will be found in <project>/_book/_css
        # or wherever that ends up in the final epub or pdf.

#        os.chdir(f'{shared.book_directory}/_images')
        # print(f'directory of pre_view.py is {css_directory}')
        # print(f'pre_view css from {css_directory}')

        # First we display the xhtml generated from the Markdown in the preview pane
        href1 = f"{os.path.abspath(shared.css_directory)}/github-markdown.css"
        href2 = f"{os.path.abspath(shared.css_directory)}/github-pygments.css"
        href3 = f"{os.path.abspath(shared.css_directory)}/styles.css"
        href4 = f"{os.path.abspath(shared.css_directory)}/admonitions.css"

        self.htmlstr = (
                html_header
                + f'<link rel = "stylesheet" href = "{href1}" type = "text/css" />\n'
                + f'<link rel = "stylesheet" href = "{href2}" type = "text/css" />\n'
                + f'<link rel = "stylesheet" href = "{href3}" type = "text/css" />\n'
                + f'<link rel = "stylesheet" href = "{href4}" type = "text/css" />\n'
                + html_header2
                + html_header3
                + html_header4
                + article_prefix
                + rendered
                + "\n</article>\n</body></html>"
            )

        the_bytes = GLib.Bytes(str.encode(self.htmlstr))
        self.load_bytes(
            the_bytes, "text/html", "utf8",
            "file://{0}/_images".format(os.path.abspath(f'{shared.markdown_directory}'))
        )
        self.set_editable(False)

        # We also need to save the html as a file
        print(f'Preview tail = {shared.tail}')
        fn_name = f'{shared.tail}'[0:-3]
        with open(
            f"{shared.project_directory}/_book/{fn_name}.xhtml", "w", encoding="utf-8") as f:
                f.write(self.htmlstr)
        print(f'Wrote {fn_name}.xhtml')

