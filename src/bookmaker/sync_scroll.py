import gi
# print gi.__path__
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class SyncScroll(object):

    outscroll = None
    inscroll_adj = None

    def __init__(self, in_scroll, out_scroll):
        # in_scroll is a Gtk.ScrolledWindow containing the markdown view. See markdown_view.py.
        # out_scroll is a WebKit2.WebView containing the preview. See pre_view.py.

        # The scroll position in the markdown view is tracked using the vertical Gtk.Adjustment
        # of the ScrolledWindow. Gtk.Adjustment has methods which make this convenient and easy.

        # Originally, this module used the vertical adjustment of a ScrolledWindow wrapping the
        # preview to control the preview scrolling and keep the two synchronised. This was possible
        # using Webkit because of the simple implementation where the Webview's scrolling could be
        # controlled from the preview ScrolledWindow.

        # With Webkit2 a more complex multi-process implementation meant that this method no longer
        # worked. The only way now seems to be to use JavaScript to request the amount of scrolling
        # required for synchronisation.

        SyncScroll.inscroll_adj = in_scroll.get_vadjustment()
        SyncScroll.inscroll_adj.connect('value_changed', self.on_inscroll_adj_value_changed)

        SyncScroll.outscroll = out_scroll

    @classmethod
    def on_inscroll_adj_value_changed(cls, dummy):
        # print('on_inscroll_adj_value_changed')
        inscroll_range = cls.inscroll_adj.get_upper() - cls.inscroll_adj.get_page_size()
        percentage = str(cls.inscroll_adj.get_value() * 100 / inscroll_range) if inscroll_range else '0'
        # print('SS.__changed__', percentage, cls.inscroll_adj.get_value(), cls.inscroll_adj.get_upper(), cls.inscroll_adj.get_page_size(), inscroll_range)

        cls.outscroll.run_javascript('document.documentElement.scrollTop = \
            (document.documentElement.scrollHeight - window.innerHeight) *' + percentage + '/100;')
        # return False

    # @classmethod
    # def idle_add_inscroll_adj_value_changed(cls):
    #     GLib.idle_add(cls.on_inscroll_adj_value_changed, 0)

