import os

from dnutils.tools import ifnone
from pyrap import session, locations
from pyrap.events import OnSelect, OnSet
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import constructor, Widget


class Template(D3Widget):

    _rwt_class_name = 'pwt.customs.Template'

    @constructor('Template')
    def __init__(self, parent, opts=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'template', 'template.css'), version=3, opts=opts, css=None, **options)
        self.theme = TemplateTheme(self, session.runtime.mngr.theme)
        self._data = {}
        self._opts = opts
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None


class TemplateTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Template')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Template', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Template', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Template', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Template', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
