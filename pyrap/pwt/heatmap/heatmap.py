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
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Heatmap(D3Widget):

    _rwt_class_name = 'pwt.customs.Heatmap'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Heatmap')
    def __init__(self, parent, opts=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'heatmap', 'heatmap.css'), version=5, opts=opts, **options)
        self.theme = HeatmapTheme(self, session.runtime.mngr.theme)
        self._limits = [0, 1]

    def setlimits(self, limits):
        self._limits = limits
        session.runtime << RWTSetOperation(self.id, {'limits': limits})


class HeatmapTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Heatmap')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Heatmap', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Heatmap', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Heatmap', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Heatmap', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
