import os
from dnutils import ifnone

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.events import OnSelect, _rwt_event, OnSet
from pyrap.ptypes import BitField
from pyrap.pwt.pwtutils import downloadsvg, downloadpdf
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor
from pyrap.constants import style, d3wrapper


class Scatterplot(Widget):

    _rwt_class_name = 'pwt.customs.Scatterplot'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Scatterplot')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ScatterTheme(self, session.runtime.mngr.theme)
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3wrapper.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=True)
        with open(os.path.join(locations.pwt_loc, 'plot', 'plot.css')) as fi:
            session.runtime.requirecss(fi)
        self._data = {}
        self.svg = None
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)

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
                downloadsvg(op.args['svg'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'plot', 'plot.css'), name=__class__.__name__)
            if key == 'pdf':
                downloadpdf(op.args['pdf'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'plot', 'plot.css'), name=__class__.__name__)
        self.on_set.notify(_rwt_event(op))

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

    @property
    def data(self):
        return self._data

    def clear(self):
        self._data = {}
        self._opts = []
        session.runtime << RWTCallOperation(self.id, 'clear', {})

    def formats(self, xformat=['', ",.2f", ''], yformat=['', ",.2f", '']):
        self._formats = [xformat, yformat]
        session.runtime << RWTCallOperation(self.id, 'formats', {'xformat': {'prefix': xformat[0], 'format': xformat[1], 'postfix': xformat[2]},
                                                                 'yformat': {'prefix': yformat[0], 'format': yformat[1], 'postfix': yformat[2]}})

    def axeslabels(self, xlabel='X-Axis', ylabel='Y-Axis'):
        self._labels = [xlabel, ylabel]
        session.runtime << RWTCallOperation(self.id, 'axes', {'labels': self._labels})

    def setdata(self, data):
        '''Expects `data' to be of the form
        {
            "scatter": scatterdata,
            "line": linedata
        },

        where `scatterdata' is a list of dicts of the form

        {
            'name': (str),      // the node labels. Leave empty if you do not want to label the scatter nodes.
            'x': (float),       // the x-coordinate of the scatter node
            'y': (float),       // the y-coordinate of the scatter node
            'tooltip': (str)    // the text to appear when hovering over a scatter node
        }

        and `linedata' is a dictionary of the form

        {
            <name>: [{'x': (float), 'y': (float)}],
            <name>: [{'x': (float), 'y': (float)}],
            ...
        }

        where the key `<name>' is a string representing the semantic meaning of the line plot (e.g. 'Prediction' and
        the value is a list of x/y coordinates (float) for the line plot.

        Note: The axes ticks are generated from the scatterdata, so make sure that the x/y coordinates for the line
        datasets lie within the axes' limits.
        '''
        self._data = data
        session.runtime << RWTSetOperation(self.id, {'data': data})

    def download(self, pdf=False):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg'})


class ScatterTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Scatterplot')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Scatterplot', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Scatterplot', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Scatterplot', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Scatterplot', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
