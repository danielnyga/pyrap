import os

from pyrap import locations
from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget


class ROS3D(Widget):

    _rwt_class_name = 'pwt.customs.ROS3D'
    _defstyle_ = Widget._defstyle_

    @constructor('ROS3D')
    def __init__(self, parent, cssid=None, requiredjs=None, url=None, port=None, urdfdata=None, **options):
        Widget.__init__(self, parent, **options)
        if requiredjs is None:
            requiredjs = []
        self._cssid = cssid
        self._url = url
        self._port = port
        self._urdfdata = urdfdata
        rwt_loc = os.path.join(locations.pwt_loc, 'ros3d', 'robotwebtools')
        self._requiredjs = [os.path.join(rwt_loc, 'three.js'),
                            os.path.join(rwt_loc, 'ColladaLoader.js'),
                            os.path.join(rwt_loc, 'STLLoader.js'),
                            os.path.join(rwt_loc, 'ColladaLoader2.js'),
                            os.path.join(rwt_loc, 'eventemitter2.min.js'),
                            os.path.join(rwt_loc, 'roslib.js'),
                            os.path.join(rwt_loc, 'ros3d.js')]
        self._requiredjs.extend(requiredjs)
        session.runtime.ensurejsresources(self._requiredjs)
        self._gwidth = None
        self._gheight = None
        self.theme = ROS3DTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._cssid:
            options.cssid = self._cssid
        if self._url:
            options.url = self._url
        if self._port:
            options.port = self._port
        if self._urdfdata:
            options.urdfdata = self._urdfdata
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

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
    def urdfdata(self):
        return self._urdfdata

    @urdfdata.setter
    def urdfdata(self, urdfdata):
        self._urdfdata = urdfdata
        session.runtime << RWTSetOperation(self.id, {'urdfdata': self.urdfdata})

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

    def startviz(self):
        session.runtime << RWTCallOperation(self.id, 'visualize', {})


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
