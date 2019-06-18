import os
from io import BytesIO

import dnutils
from dnutils import ifnone

from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.events import OnSelect, _rwt_selection_event, _rwt_event
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget
from lxml import etree as ET

logger = dnutils.getlogger('MatCALOLogger')


class SVG(Widget):

    _rwt_class_name = 'pwt.customs.SVG'
    _defstyle_ = Widget._defstyle_

    @constructor('SVG')
    def __init__(self, parent, svg=None, cssid=None, **options):
        Widget.__init__(self, parent, **options)
        self.root = None
        self.tree = None
        self._cssid = cssid
        self._svgfile = svg
        self._content = None
        # limiting/scaling values
        self._factor = 1
        self._maxwidth = None
        self._maxheight = None
        self.on_select = OnSelect(self)
        self.theme = SVGTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.cssid = self._cssid
        options.selfid = self.id
        if self._svgfile is not None:
            print('getting svg', self._svgfile)
            options.svg = self._get_rwt_svg(self._svgfile)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def _get_rwt_svg(self, svg):
        if os.path.isfile(svg):
            self.tree = ET.parse(svg)
            self.root = self.tree.getroot()
        else:
            self.root = ET.fromstring(svg)
            self.tree = ET.ElementTree(self.root)
        #
        # # determine size from viewbox
        # w, h = self.root.attrib['viewBox'].split()[-2:]
        # self._vbwidth = int(float(w))
        # self._vbheight = int(float(h))
        # self._ratio = float(self._vbwidth) / self._vbheight

        # writing the stream to the content will omit leading doc infos
        stream = BytesIO()
        self.tree.write(stream)
        self._content = stream.getvalue().decode('utf8')
        stream.close()

        return self._content

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._selection = value

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        elif op.event == 'Selection':
            if 'mousedown' in op.args:
                events[op.event].notify(_rwt_event(op))
            else:
                events[op.event].notify(_rwt_selection_event(op))
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    def _handle_call(self, op):
        pass

    def setlisteners(self, elems, func):
        self.on_select += func
        session.runtime << RWTSetOperation(self.id, {'selectelem': elems})

    @property
    def svg(self):
        return self._content

    @svg.setter
    @checkwidget
    def svg(self, svg):
        self._svgfile = svg
        _svg = self._get_rwt_svg(svg)
        session.runtime << RWTSetOperation(self.id, {'svg': _svg})

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

    def scale(self, factor):
        self._factor = factor

    def maxwidth(self, width):
        self._maxwidth = width

    def maxheight(self, height):
        self._maxheight = height

    def compute_size(self):
        w, h = Widget.compute_size(self.parent)

        # try to determine size from SVG attributes
        if self.root is not None:
            # determine size from viewbox
            if 'viewBox' in self.root.attrib:
                w_, h_ = self.root.attrib['viewBox'].split()[-2:]
                w += int(float(w_))
                h += int(float(h_))
            # determine size from width/height attributes
            elif 'width' in self.root.attrib:
                try:
                    w += int(float(self.root.attrib['width']))
                except ValueError:
                    logger.warning('Width is not a float value:', self.root.attrib['width'])
            elif 'height' in self.root.attrib:
                try:
                    h += self.root.attrib['height']
                except ValueError:
                    logger.warning('Height is not a float value:', self.root.attrib['height'])

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

        # apply scaling factor
        w *= self._factor
        h *= self._factor

        # limit width/height to possibly set max values
        if h > 0:
            ratio = float(w) / float(h)

            if self._maxwidth is not None and self._maxheight is not None:
                tmpratio = self._maxwidth/self._maxheight
                # determine which max value is stricter limiting
                if tmpratio < ratio:
                    w = self._maxwidth
                    h = w/ratio
                else:
                    h = self._maxheight
                    w = h*ratio
            elif self._maxwidth is not None:
                w = min(w, self._maxwidth)
                h = w/ratio
            elif self._maxheight is not None:
                h = min(h, self._maxheight)
                w = ratio * h
        if w == 0 or h == 0:
            logger.warning('Size of SVG is too small to display. Set width and height manually.', w, h)
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
