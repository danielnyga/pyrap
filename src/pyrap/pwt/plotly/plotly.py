import os

from pathlib import Path

from pyrap import session, locations
from pyrap.communication import RWTSetOperation
from pyrap.events import OnSelect, OnSet
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import constructor


class Plotly(D3Widget):
    _rwt_class_name = 'pwt.customs.Plotly'

    @constructor('Plotly')
    def __init__(self, parent, opts=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'plotly', 'plotly.css'), version=3, opts=opts, css=None, **options)
        self.theme = PlotlyTheme(self, session.runtime.mngr.theme)
        self._data = {}
        self._opts = opts
        self._url = opts.get('url', None)
        self._plotid = None
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        with open(url, 'rb') as f:
            res = session.runtime.mngr.resources.registerf(f'resource/static/image/{Path(url).stem}.html', 'text/html', f)
            print('set url', res.location)
        self._url = res.location
        session.runtime << RWTSetOperation(self.id, {'url': url})


class PlotlyTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Plotly')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Plotly', self.styles(), self.states()) for b in
                ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Plotly', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Plotly', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Plotly', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
