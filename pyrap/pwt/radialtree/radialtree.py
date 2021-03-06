#  -*- coding: utf-8 -*-
#                                           _..._                       .-'''-.
#                                        .-'_..._''.           .---.   '   _    \
#   __  __   ___                       .' .'      '.\          |   | /   /` '.   \
#  |  |/  `.'   `.                    / .'                     |   |.   |     \  '
#  |   .-.  .-.   '              .|  . '                       |   ||   '      |  '
#  |  |  |  |  |  |    __      .' |_ | |                 __    |   |\    \     / /
#  |  |  |  |  |  | .:--.'.  .'     || |              .:--.'.  |   | `.   ` ..' /
#  |  |  |  |  |  |/ |   \ |'--.  .-'. '             / |   \ | |   |    '-...-'`
#  |  |  |  |  |  |`" __ | |   |  |   \ '.          .`" __ | | |   |
#  |__|  |__|  |__| .'.''| |   |  |    '. `._____.-'/ .'.''| | |   |
#                  / /   | |_  |  '.'    `-.______ / / /   | |_'---'
#                  \ \._,\ '/  |   /              `  \ \._,\ '/
#                   `--'  `"   `'-'                   `--'  `"
#  (C) 2017 by Mareike Picklum (mareikep@cs.uni-bremen.de)
# 
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os

from pyrap import session, locations
from pyrap.communication import RWTSetOperation
from pyrap.events import _rwt_event, _rwt_selection_event
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class RadialTree(D3Widget):
    '''The data structure expected by this visualization is a nested json object with the attributes
        * name:         (str) the text shown at the respective node
        * showname:     (bool) whether the node name is hidden or shown
        * type:         (hex) color value for the node and edge at this point in the tree
        * tooltip:      (str) the tooltip shown when hovering over the node
        * children:     (list <object>) the subtree with the same structure as above

    and looks as follows:

    :Example:
        {
          "name": "Char. Vals",
          "showname": true,
          "type": null,
          "tooltip": "Characteristic Values",
          "children": [
            {
              "name": "D01",
              "showname": true,
              "type": "#6C00FF",
              "tooltip": "D01",
              "children": [...]
            },
            {...}
          ]

    '''

    _rwt_class_name = 'pwt.customs.RadialTree'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadialTree')
    def __init__(self, parent, opts=None, css=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'radialtree', 'radialtree.css'), version=3, opts=opts, css=css, **options)
        self.theme = RadialTreeTheme(self, session.runtime.mngr.theme)
        self._glow = False
        self._fontcolor = None
        self._bgcolor = None
        self._mode = None

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        elif op.event == 'Selection':
            events[op.event].notify(_rwt_selection_event(op))
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    @property
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, glow):
        self._glow = glow
        session.runtime << RWTSetOperation(self.id, {'glow': glow})

    @property
    def fontcolor(self):
        return self._fontcolor

    @fontcolor.setter
    def fontcolor(self, fc):
        self._fontcolor = fc
        session.runtime << RWTSetOperation(self.id, {'fontcolor': fc})

    @property
    def bgcolor(self):
        return self._bgcol

    @bgcolor.setter
    def bgcolor(self, bgc):
        self._bgcol = bgc
        session.runtime << RWTSetOperation(self.id, {'bgcolor': bgc})

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        '''Convenience function for visual settings: `mode` can be either `bw` or `color`:
            * bw:       fontcolor = black, background-color = white, glow = False
            * color:    fontcolor = white, background-color = black, glow = true
        '''
        self._mode = mode
        session.runtime << RWTSetOperation(self.id, {'mode': mode})


class RadialTreeTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'RadialTree')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'RadialTree', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'RadialTree', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'RadialTree', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'RadialTree', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
