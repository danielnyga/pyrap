import os
from io import BytesIO

from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.themes import WidgetTheme
from pyrap.utils import out, ifnone
from pyrap.widgets import Widget, constructor, checkwidget
from lxml import etree as ET


class SVG(Widget):

    _rwt_class_name = 'pwt.customs.SVG'
    _defstyle_ = Widget._defstyle_

    @constructor('SVG')
    def __init__(self, parent, svg=None, cssid=None, **options):
        Widget.__init__(self, parent, **options)
        self._cssid = cssid
        self._svgfile = svg
        self._content = None
        # size as read from the viewbox property in the svg attributes
        self._vbwidth = None
        self._vbheight = None
        # size as can be set by the user
        self._gwidth = None
        self._gheight = None
        self.theme = SVGTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.cssid = self._cssid
        options.selfid = self.id
        if self._svgfile is not None:
            options.svg = self._get_rwt_svg(self._svgfile)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def _get_rwt_svg(self, svg):
        if os.path.isfile(svg):
            self.tree = ET.parse(svg)
            self.root = self.tree.getroot()
        else:
            self.root = ET.fromstring(svg)
            self.tree = ET.ElementTree(self.root)
        w, h = self.root.attrib['viewBox'].split()[-2:]
        out(w, h, type(w), type(h))
        self._vbwidth = int(float(w))
        self._vbheight = int(float(h))

        # writing the stream to the content will omit leading doc infos
        stream = BytesIO()
        self.tree.write(stream)
        self._content = str(stream.getvalue())
        stream.close()

        return self._content

    @property
    def svg(self):
        return self._content

    @svg.setter
    @checkwidget
    def svg(self, svg):
        self._svgfile = svg
        _svg = self._get_rwt_svg(svg)
        session.runtime << RWTSetOperation(self.id, {'svg': _svg})

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

    def getattr(self, id, attr):
        '''
        Returns the value for the requested attribute of the element with the
        given id.
        :param id:      (str) the element to retrieve the attribute value from
        :param attr:    (str) the attribute to retrieve the value from
        :return:        (str) the value of the attribute
        '''
        elem = self.tree.find('*//*[@id="{}"]'.format(id))
        if attr in elem.attrib:
            return elem.attrib[attr]
        else:
            return None

    def elattribute(self, id, attr, val):
        '''
        Sets the given value for the attribute attr of the element with the
        specified id in the svg.
        :param id:      (str) the id of the element to be updated
        :param attr:    (str) the attribute to assign a value to
        :param val:     (str) the value to set for the attribute
        :return:        nothing
        '''
        # set in gui
        session.runtime << RWTCallOperation(self.id, 'elAttribute', {'id': id, 'attribute': attr, 'value': val})
        # update local content
        elem = self.tree.find('*//*[@id="{}"]'.format(id))
        if elem is not None:
            elem.set(attr, val)
        self.save()

    def attribute(self, attr, val):
        '''
        Assigns the given value to the attribute attr of the svg.
        :param attr:    (str) the attribute to assign a value to
        :param val:     (str) the value to set for the attribute
        :return:        nothing
        '''
        # set in gui
        session.runtime << RWTCallOperation(self.id, 'attribute', {'attribute': attr, 'value': val})
        # update local content
        elem = self.root
        if elem is not None:
            elem.set(attr, val)
        self.save()

    def highlight(self, id, clear):
        session.runtime << RWTCallOperation(self.id, 'highlight', { 'id': id, 'clear': clear })

    def clear(self, ids):
        session.runtime << RWTCallOperation(self.id, 'clear', {'ids': ids})

    def save(self):
        stream = BytesIO()
        self.tree.write(stream)
        self._content = str(stream.getvalue())
        stream.close()

    def compute_size(self):
        # prefer user given size, otherwise try to obtain size from svg content
        # if still not successful, use parent size
        w = self.gwidth or self._vbwidth
        h = self.gheight or self._vbheight

        if self._vbwidth is not None and self._vbheight is not None:
            ratio = float(self._vbwidth) / self._vbheight
        else:
            ratio = None

        if w is None and ratio is not None and h is not None:
                w = h * ratio
        elif h is None and ratio is not None and w is not None:
                h = w / ratio
        else:
            w = self.parent.width
            h = self.parent.height

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


class SVGTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'SVG')
        self.separator = None

    @property
    def font(self):
        if self._font is not None: return self._font
        return self._theme.get_property('font', 'SVG', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'SVG', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'SVG', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'SVG', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
