import os

from pyrap import session, locations
from pyrap.events import _rwt_event
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Tree(D3Widget):

    _rwt_class_name = 'pwt.customs.Tree'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Tree')
    def __init__(self, parent, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'tree', 'tree.css'), version=3, **options)
        self.theme = TreeTheme(self, session.runtime.mngr.theme)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_event(op))
        return True


class TreeTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Tree')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Tree', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Tree', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Tree', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Tree', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
