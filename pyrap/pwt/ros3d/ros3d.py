from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation
from pyrap.themes import WidgetTheme
from pyrap.utils import ifnone
from pyrap.widgets import Widget, constructor, checkwidget


class ROS3D(Widget):

    _rwt_class_name = 'pwt.customs.ROS3D'
    _defstyle_ = Widget._defstyle_

    @constructor('ROS3D')
    def __init__(self, parent, cssid=None, requiredjs=None, url=None, port=None, **options):
        Widget.__init__(self, parent, **options)
        self._cssid = cssid
        self._url = url
        self._port = port
        self._requiredjs = requiredjs
        self._gwidth = None
        self._gheight = None
        session.runtime.ensurejsresources(self._requiredjs)
        self.theme = ROS3DTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._cssid:
            options.cssid = self._cssid
        if self._url:
            options.url = self._url
        if self._port:
            options.port = self._port
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w = 800
        h = 600

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

    @property
    def cssid(self):
        return self._cssid

    @cssid.setter
    def cssid(self, cssid):
        self._cssid = cssid

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url
        session.runtime << RWTSetOperation(self.id, {'url': self.url})

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port
        session.runtime << RWTSetOperation(self.id, {'port': self.port})

    @property
    def gwidth(self):
        return self._gwidth

    @gwidth.setter
    @checkwidget
    def gwidth(self, w):
        self._gwidth = w
        session.runtime << RWTSetOperation(self.id, {'width': self.gwidth})

    @property
    def gheight(self):
        return self._gheight

    @gheight.setter
    @checkwidget
    def gheight(self, h):
        self._gheight = h
        session.runtime << RWTSetOperation(self.id, {'height': self.gheight})


class ROS3DTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'ROS3D')
        self.separator = None

    @property
    def font(self):
        if self._font is not None: return self._font
        return self._theme.get_property('font', 'ROS3D', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'ROS3D', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'ROS3D', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'ROS3D', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'ROS3D', self.custom_variant(), self.styles(), self.states())
