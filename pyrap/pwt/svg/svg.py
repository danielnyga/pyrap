from io import BytesIO

from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.themes import WidgetTheme
from pyrap.utils import out
from pyrap.widgets import Widget, constructor, checkwidget
from lxml import etree as ET


class SVG(Widget):

    _rwt_class_name = 'pwt.customs.SVG'
    _defstyle_ = Widget._defstyle_

    @constructor('SVG')
    def __init__(self, parent, svgfile=None, cssid=None, **options):
        Widget.__init__(self, parent, **options)
        self._cssid = cssid
        self._svgfile = svgfile
        self._svgcontent = None
        self.theme = SVGTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.cssid = self._cssid
        options.selfid = self.id
        if self._svgfile is not None:
            options.svg = self._get_rwt_svg(self._svgfile)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def _get_rwt_svg(self, fpath):
        self.tree = ET.parse(fpath)
        self.root = self.tree.getroot()
        w, h = self.root.attrib['viewBox'].split()[-2:]
        self._width = int(w)
        self._height = int(h)

        # writing the stream to the content will omit leading doc infos
        stream = BytesIO()
        self.tree.write(stream)
        self._content = str(stream.getvalue())
        stream.close()

        return self._content

    @property
    def svg(self):
        return self._svgcontent

    @svg.setter
    @checkwidget
    def svg(self, path):
        self._svgfile = path
        session.runtime << RWTSetOperation(self.id, {'svg': self._get_rwt_svg(path)})

    def getattr(self, id, attr):
        elem = self.tree.find('*//*[@id="{}"]'.format(id))
        if attr in elem.attrib:
            return elem.attrib[attr]
        else:
            return None

    def setattr(self, id, attr, val):
        # set in gui
        session.runtime << RWTSetOperation(self.id, {'attr': [id, attr, val]})
        # update local content
        elem = self.tree.find('*//*[@id="{}"]'.format(id))
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
        _, _, w, h = session.runtime.windows.display.bounds
        prop = float(self._width)/self._height
        h = h/2.
        h = min(h, self._height)
        w = h * prop
        out('svg sizes========================================================', w, h)

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
