import os

from pyrap import session, locations
from pyrap.communication import RWTCallOperation
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Scatterplot(D3Widget):

    _rwt_class_name = 'pwt.customs.Scatterplot'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Scatterplot')
    def __init__(self, parent, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'plot', 'plot.css'), version=3, **options)
        self.theme = ScatterTheme(self, session.runtime.mngr.theme)

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
        D3Widget.setdata(self, data)


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
