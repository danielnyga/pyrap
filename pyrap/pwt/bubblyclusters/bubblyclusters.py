import os

from pyrap import session, locations
from pyrap.communication import RWTCallOperation, \
    RWTSetOperation
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class BubblyClusters(D3Widget):

    _rwt_class_name = 'pwt.customs.BubblyClusters'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('BubblyClusters')
    def __init__(self, parent, opts=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'bubblyclusters', 'bubblyclusters.css'), version=3, opts=opts, **options)
        self.theme = BubblyClustersTheme(self, session.runtime.mngr.theme)

    def play(self):
        session.runtime << RWTCallOperation(self.id, 'play', {})

    def setaudio(self, audio):
        '''Played on creating bubbly nodes'''
        self._audio = audio
        with open(os.path.abspath(audio), "rb") as f:
            resource = session.runtime.mngr.resources.registerf(os.path.basename(audio), 'audio/mpeg', f, encode=False)
            session.runtime << RWTSetOperation(self.id, {'audio': resource.location})


class BubblyClustersTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'BubblyClusters')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'BubblyClusters', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'BubblyClusters', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'BubblyClusters', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'BubblyClusters', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
