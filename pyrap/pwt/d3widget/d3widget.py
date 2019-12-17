import io
import os
import tempfile

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, RWTSetOperation
from pyrap.constants import d3v3, d3v4, d3v5
from pyrap.events import OnSelect, OnSet, _rwt_event
from pyrap.ptypes import BitField, SVG
from pyrap.widgets import Widget

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

d3versions = {3: d3v3, 4: d3v4, 5: d3v5}


def downloadsvg(cnt, w, h, css, name='tmpviz'):
    svg = SVG()
    svg.load(cnt, w=w, h=h, css=css)

    stream = io.BytesIO()
    svg.save(stream)
    session.runtime.download('{}.svg'.format(name), 'image/svg+xml', stream.getvalue(), force=True)
    stream.close()


def downloadpdf(cnt, w, h, css, name='tmpviz'):
    tmpfile = os.path.join(tempfile.gettempdir(), 'viz.svg')
    svg = SVG()
    svg.load(cnt, w=w, h=h, css=css)

    with open(tmpfile, 'wb') as f:
        svg.save(f)

    svgcontent = svg2rlg(tmpfile)
    v = renderPDF.drawToString(svgcontent)
    session.runtime.download('{}.pdf'.format(name), 'application/pdf', v, force=True)
    os.remove(tmpfile)


class D3Widget(Widget):
    '''Wrapper class for all d3js widgets. Make sure that the type handler in your d3 widget's corresponding .js file
    contains the following methods, events and properties (see template.py and template.js):

    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]
    '''

    _rwt_class_name = None
    _defstyle_ = BitField(Widget._defstyle_)

    def __init__(self, parent, widgetcss, version=3, opts=None, css=None, **options):
        Widget.__init__(self, parent, **options)
        self._data = {}
        self._d3version = 'd3.v{}.min.js'.format(str(version))
        self._d3css = os.path.join(locations.trdparty, 'd3', self._d3version)
        self._widgetcss = widgetcss
        self._opts = opts
        with open(self._d3css, 'r') as f:
            cnt = d3versions.get(version, d3v3).format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name=self._d3version, force=True)
        with open(self._widgetcss) as fi:
            session.runtime.requirecss(fi)
        if css is not None:
            self._css = css
            for css_ in css:
                with open(css_) as fcss:
                    session.runtime.requirecss(fcss)
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._opts:
            options.options = self._opts
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        events[op.event].notify(_rwt_event(op))
        return True

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'svg':
                fname = op.args['svg'][1]
                if fname is None:
                    fname = __class__.__name__
                downloadsvg(op.args['svg'][0], self.width.value, self.height.value, [self._widgetcss] + (self._css if self._css is not None else []), name=fname)
                self.on_set.notify(_rwt_event(op))
            if key == 'pdf':
                fname = op.args['pdf'][1]
                if fname is None:
                    fname = __class__.__name__
                downloadpdf(op.args['pdf'][0], self.width.value, self.height.value, [self._widgetcss] + (self._css if self._css is not None else []), name=fname)
                self.on_set.notify(_rwt_event(op))

    def clear(self):
        self._data = {}
        self._opts = []
        session.runtime << RWTCallOperation(self.id, 'clear', {})

    def setdata(self, data):
        self._data = data
        session.runtime << RWTSetOperation(self.id, {'data': data})

    def download(self, pdf=False, fname=None):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg', 'fname': fname})
