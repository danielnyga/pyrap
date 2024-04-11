import os
from dnutils import ifnone

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.events import _rwt_event, OnSelect
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Video(Widget):

    _rwt_class_name = 'pwt.customs.Video'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Video')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = VideoTheme(self, session.runtime.mngr.theme)
        self._sources = []
        self.isPlaying = False
        self.on_select = OnSelect(self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w, h = Widget.compute_size(self.parent)

        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        margin = self.theme.margin
        if margin:
            w += ifnone(margin.left, 0) + ifnone(margin.right, 0)
            h += ifnone(margin.top, 0) + ifnone(margin.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)

        return w, h

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    def play(self):
        session.runtime << RWTCallOperation(self.id, 'play', {})
        self.isPlaying = True

    def pause(self):
        session.runtime << RWTCallOperation(self.id, 'pause', {})
        self.isPlaying = False

    def addsrc(self, src):
        self._sources.append(src)
        with open(os.path.abspath(src['source']), "rb") as f:
            resource = session.runtime.mngr.resources.registerf(os.path.basename(src.get('source')), src.get('type', 'video/mp4'), f, encode=False)
            session.runtime << RWTCallOperation(self.id, 'addSrc', {'source': resource.location, 'type': src['type']})


class VideoTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Video')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Video', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Video', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Video', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Video', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Video', self.custom_variant(), self.styles(), self.states())
