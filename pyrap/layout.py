'''
Created on Dec 2, 2015

@author: nyga
'''
from itertools import zip_longest

from dnutils import ifnone, out
from tabulate import tabulate

from pyrap.ptypes import pc, px, parse_value
from pyrap.utils import pparti
from pyrap.exceptions import LayoutError


class LayoutAdapter:
    '''Base class representing an abstract, logical GUI element that is subject to some layout process.

    Typically wraps around a widget that is to be positioned in a composite'''

    def __init__(self, widget, parent, children=None):
        self.widget = widget
        self.layout = None if widget is None else widget.layout
        self.parent = parent
        self.children = ifnone(children, [])
        self.hpos = None
        self.vpos = None
        self.width = None
        self.height = None

    def preferred_size(self):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()


class Terminal(LayoutAdapter):
    '''Layout adapter for terminal widgets, i.e. widget that do not have any child widgets'''

    def __init__(self, widget, parent, children=None):
        LayoutAdapter.__init__(self, widget, parent, children)
        self._widgetsize = None
        self._minheight = None
        self._minwidth = None

    def preferred_size(self):
        if self._widgetsize is None:
            wsize = self.widget.compute_size() if self.widget is not None else (0, 0)
            self._widgetsize = max(wsize[0], ifnone(self.layout.minwidth, 0)), max(wsize[1], ifnone(self.layout.minheight, 0))
        if self._minwidth is None:
            self._minwidth = max(ifnone(self.layout.cell_minwidth, 0), self._widgetsize[0] + self.layout.padding_left + self.layout.padding_right)
        if self._minheight is None:
            self._minheight = max(ifnone(self.layout.cell_minheight, 0), self._widgetsize[1] + self.layout.padding_top + self.layout.padding_bottom)
        return self._minwidth, self._minheight

    def run(self):
        if self.widget is not None and None not in (self.hpos, self.vpos, self.width, self.height):
            x, y, width, height = None, None, None, None
            layout = self.layout
            wwidth, wheight = self._widgetsize
            # horizontal position
            if layout.halign == 'fill':
                x = self.hpos + layout.padding_left
                width = self.width - layout.padding_right - layout.padding_left
            elif layout.halign == 'left':
                x = self.hpos + layout.padding_left
                width = wwidth
            elif layout.halign == 'right':
                x = self.hpos + self.width - wwidth - layout.padding_right
                width = wwidth
            elif layout.halign == 'center':
                x = self.hpos + pc(50).of(self.width) - pc(50).of(wwidth)
                width = wwidth
            # vertical position
            if layout.valign == 'fill':
                y = self.vpos + layout.padding_top
                height = self.height - layout.padding_bottom - layout.padding_top
            elif layout.valign == 'top':
                y = self.vpos + layout.padding_top
                height = wheight
            elif layout.valign == 'bottom':
                y = self.vpos + self.height - wheight - layout.padding_bottom
                height = wheight
            elif layout.valign == 'center':
                y = self.vpos + pc(50).of(self.height) - pc(50).of(wheight)
                height = wheight
            self.widget.bounds = x, y, width, height


class CellSeq:
    '''Represents a sequence of layout cells in a  grid'''

    def __init__(self, idx, cells=None):
        self.idx = idx
        self._cells = ifnone(cells, [])

    def append(self, cell):
        self._cells.append(cell)

    def itercells(self):
        yield from self._cells

    def __repr__(self):
        return str(self)


class Row(CellSeq):
    '''Represents one row of layout cells in a grid'''

    def __init__(self, idx, cells=None):
        CellSeq.__init__(self, idx, cells)
        self._minheight = None

    def __str__(self):
        return '<Row: [%s]>' % ';'.join(['?' if c.widget is None else c.widget.id for c in self.itercells()])

    @property
    def minheight(self):
        if self._minheight is None:
            self._minheight = max([c.preferred_size()[1] for c in self.itercells()])
        return self._minheight

    def setheights(self, h):
        for cell in self.itercells():
            cell.height = h

    def equalize_heights(self):
        max_height = max([c.height for c in self.itercells()])
        self.setheights(max_height)
        return max_height


class Col(CellSeq):
    '''Represents one column of layout cells in a grid'''

    def __init__(self, idx, cells=None):
        CellSeq.__init__(self, idx, cells)
        self._minwidth = None

    def __str__(self):
        return '<Col: [%s]>' % (';'.join(['?' if c.widget is None else c.widget.id for c in self.itercells()]))

    @property
    def minwidth(self):
        if self._minwidth is None:
            self._minwidth = max([c.preferred_size()[0] for c in self.itercells()])
        return self._minwidth

    def setwidths(self, w):
        for cell in self.itercells():
            cell.width = w

    def equalize_widths(self):
        max_width = max([c.width for c in self.itercells()])
        self.setwidths(max_width)
        return max_width


class LayoutGrid:
    '''Represents a grid of layout cells'''

    def __init__(self, cell, children=None):
        self.cell = cell
        self.cols = []
        self.rows = []
        self.children = children
        self._materialize()

    def _materialize(self):
        layout = self.cell.layout
        colcount, rowcount = None, None
        if hasattr(layout, 'cols') and layout.cols is not None:
            colcount = layout.cols
        elif hasattr(layout, 'rows') and layout.rows is not None:
            rowcount = layout.rows
        limit = ifnone(colcount, rowcount)
        wmatrix = []
        children = list(self.children)
        while children:
            chdrn = children[:limit]
            wmatrix.append([c for c in chdrn] + [GridCell(None, self.cell) for _ in range(limit - len(chdrn))])
            children = children[len(chdrn):]
        if rowcount is not None:  # transpose the matrix if #rows are given
            wmatrix = list(zip_longest(*wmatrix))
        self.cols = []
        self.rows = []
        for i, cells in enumerate(wmatrix):
            row = Row(i, cells)
            self.rows.append(row)
            for c in cells: c.row = row
        for i, cells in enumerate(zip(*wmatrix)):
            col = Col(i, cells)
            self.cols.append(col)
            for c in cells: c.col = col

    def itercells(self):
        for row in self.rows:
            yield from row.itercells()

    def __str__(self):
        return '<LayoutGrid %dx%d>' % (len(self.rows), len(self.cols))

    def equalize_column_widths(self, all_cols_equal=False):
        maxwidth = max([c.equalize_widths() for c in self.cols])
        if all_cols_equal:
            for col in self.cols:
                col.setwidths(maxwidth)

    def equalize_row_heights(self, all_rows_equal=False):
        maxheight = max([r.equalize_heights() for r in self.rows])
        if all_rows_equal:
            for row in self.rows:
                row.setheights(maxheight)

    def print_minsizes(self):
        sizes = [['%sx%s' % (c.minwidth, c.minheight) for c in row.itercells()] for row in self.rows]
        print(tabulate(sizes))

    def print_sizes(self):
        sizes = [['%sx%s' % (c.width, c.height) for c in row.itercells()] for row in self.rows]
        print(tabulate(sizes))

    def print_positions(self):
        sizes = [['%s %sx%s at (%s,%s)' % (c.widget.id, int(c.width), int(c.height), int(c.hpos), int(c.vpos)) for c in row.itercells() if c.widget is not None] for row in self.rows]
        print(tabulate(sizes))


class GridCell(LayoutAdapter):
    '''Represents one single cell in a grid layout'''

    def __init__(self, widget, parent):
        LayoutAdapter.__init__(self, widget, parent)
        self._grid = None
        self.col = None
        self.row = None
        self._minwidth = None
        self._minheight = None
        self._widgetsize = None
        self._fringe = None

    @property
    def grid(self):
        if self._grid is None and self.children:
            self._grid = LayoutGrid(self, self.children)
        return self._grid

    @property
    def fringe(self):
        if self._fringe is None:
            self._fringe = self.widget.compute_fringe() if self.widget is not None else (0, 0, 0, 0)
        return self._fringe

    @property
    def widget_size(self):
        if self._widgetsize is None:
            w, h = self.widget.compute_size() if self.widget is not None else (0, 0)
            self._widgetsize = w, h#max(w, ifnone(self.layout.minwidth, 0)), max(h, ifnone(self.layout.minheight, 0))
        return self._widgetsize

    def preferred_size(self):
        # preferred horizontal size
        if self._minwidth is None:
            self._minwidth, h = self.widget_size
            if self.grid is not None:
                minwidths = [c.minwidth for c in self.grid.cols]
                if self.layout.equalwidths:
                    minwidth = max(minwidths) * len(self.grid.cols)
                else:
                    minwidth = sum(minwidths)
                if self.layout.hexceed == 'pack':
                    self._minwidth += minwidth + (len(self.grid.cols) - 1) * self.layout.hspace
                self._widgetsize = max(self._minwidth, ifnone(self.layout.minwidth, 0)), h
                self._minwidth = max(self._minwidth, self._widgetsize[0]) + self.layout.padding_left + self.layout.padding_right
                self._minwidth = max(self._minwidth, ifnone(self.layout.cell_minwidth, 0))
        # preferred vertical size
        if self._minheight is None:
            w, self._minheight = self.widget_size
            if self.grid is not None:
                minheights = [r.minheight for r in self.grid.rows]
                if self.widget.layout.equalheights:
                    maxminheight = max(minheights)
                    minheight = maxminheight * len(self.grid.rows)
                else:
                    minheight = sum(minheights)
                if self.layout.vexceed == 'pack':
                    self._minheight += minheight + (len(self.grid.rows) - 1) * self.layout.vspace
                self._widgetsize = w, max(self._minheight, ifnone(self.layout.minheight, 0))
                self._minheight = max(self._minheight, self._widgetsize[1]) + self.layout.padding_top + self.layout.padding_bottom
                self._minheight = max(self._minheight, ifnone(self.layout.cell_minheight, 0))
        return self._minwidth, self._minheight

    @property
    def flexcols(self):
        if self.widget is None or self.grid is None: return {} # or self.layout.halign != 'fill'
        return {f: v for f, v in self.layout.flexcols.items() if f < len(self.grid.cols)}

    @property
    def fixcols(self):
        if self.widget is None or self.grid is None: return []
        return [i for i in range(len(self.grid.cols)) if i not in self.flexcols]

    @property
    def flexrows(self):
        if self.widget is None or self.grid is None: return {} # or self.widget.layout.valign != 'fill'
        return {f: v for f, v in self.widget.layout.flexrows.items() if f < len(self.grid.rows)}

    @property
    def fixrows(self):
        if self.widget is None or self.grid is None: return []
        return [i for i in range(len(self.grid.rows)) if i not in self.flexrows]

    def __str__(self):
        return '<GridCell: %s at (%s,%s)>' % (self.widget.id if self.widget is not None else '?',
                                              self.row.idx if self.row is not None else '?',
                                              self.col.idx if self.col is not None else '?')

    def __repr__(self):
        return str(self)

    def run(self):
        # first, compute the preferred sizes hierarchically in a bottom-up fashion
        self.preferred_size()
        self._distribute()
        for child in self.children:
            child.run()

    def _distribute(self):
        if self.widget is None:
            return
        layout = self.layout
        if None in (self.width, self.height):
            self.width, self.height = self.preferred_size()
        # =======================================================================
        # if this widget already has a width specified, distribute the flexcols
        # over the remaining free space.
        # =======================================================================
        fringe_top, fringe_right, fringe_bottom, fringe_left = self.fringe
        if self.grid is not None:  # and layout.halign == 'fill' and cell.width is not None:
            fixcols = self.fixcols
            flexcols = self.flexcols
            # out('distributing cols in', self, self.width, 'x', self.height)
            if layout.equalwidths:
                if fixcols and flexcols:
                    raise LayoutError('Layout is inconsistent: I was told to make columns in %s '
                                      'equal length, but you have manually specified flexcols. '
                                      'Remove them or set all columns be flexible.' % repr(self.widget))
                fixcols = []
                flexcols = {i: 1 for i in range(len(self.grid.cols))}
            if layout.halign == 'fill' and not flexcols:
                raise Exception('Layout is underdetermined: I was told to fill %s '
                                'horizontally, but I do not have any flexcols. '
                                '(created at %s)' % (repr(self.widget), self.widget._created))
            fixcolwidths = 0
            maxcolwidth = 0
            for col in self.grid.cols:
                colwidth = col.minwidth  # equalize_widths()
                maxcolwidth = max(maxcolwidth, colwidth)
                if col.idx in fixcols:
                    fixcolwidths += colwidth  # the space definitely occupied by fixcols
            if self.width is None:
                free = 0 #self._minwidth
            else:
                if layout.halign == 'fill':
                    free = self.width
                else:
                    free = self._minwidth
                free -= fixcolwidths + layout.padding_left + layout.padding_right + \
                        layout.hspace * (len(self.grid.cols) - 1)
                free -= fringe_left + fringe_right
            # compute the widths of the flexible columns proportionally to their specification
            flexcolidx = sorted(flexcols.keys())
            flexwidths = dict(zip(flexcolidx, pparti(max(0, free), [flexcols[j] for j in flexcolidx])))
            fringe = set(flexcolidx)
            while fringe:
                idx = fringe.pop()
                try:
                    ratio = float(flexwidths[idx]) / float(self.grid.cols[idx].minwidth)
                except ZeroDivisionError:
                    ratio = 1
                if 0 < ratio < 1:
                    for i, h in dict(flexwidths).items():
                        flexwidths[i] = float(h) * 1. / ratio
                    fringe = set(flexcolidx)
            for col in self.grid.cols:
                # a cell should always have at least the minimum width imposed by the widget containing it
                w = max(maxcolwidth if layout.equalwidths else 0,
                        flexwidths.get(col.idx, 0),
                        col.minwidth if (col.idx not in flexcols or self.width is None) else 0)
                col.setwidths(w)
        # =======================================================================
        # if this widget already has a height specified, distribute the flexcols
        # over the remaining free space.
        # =======================================================================
        if self.grid is not None:  # and layout.valign == 'fill' and cell.height is not None:
            fixrows = self.fixrows
            flexrows = self.flexrows
            if layout.equalheights:
                if fixrows and flexrows:
                    raise LayoutError('Layout is inconsistent: I was told to make rows in %s '
                                      'equal height, but you have manually specified flexrows. '
                                      'Remove them or set all rows be flexible.' % repr(self.widget))
                fixrows = []
                flexrows = {i: 1 for i in range(len(self.grid.rows))}
            if layout.valign == 'fill' and not flexrows:  # sanity check
                raise Exception('Layout is underdetermined: I was told to fill %s '
                                'vertically, but I do not have any flexrows. '
                                '(created at %s)' % (repr(self.widget), self.widget._created))
            fixrowheights = 0
            maxrowheight = 0
            for row in self.grid.rows:
                rowheight = row.minheight  # equalize_heights()
                maxrowheight = max(maxrowheight, rowheight)
                if row.idx in fixrows:
                    fixrowheights += rowheight  # the space definitely occupied by fixrows
            if self.height is None:
                free = 0
            else:
                if layout.valign == 'fill':
                    free = self.height
                else:
                    free = self._minheight
                free -= fixrowheights + layout.padding_top + layout.padding_bottom + \
                        layout.vspace * (len(self.grid.rows) - 1)
                free -= fringe_top + fringe_bottom
            # compute the widths of the flexible columns proportionally to their specification
            flexrowidx = sorted(flexrows.keys())
            flexheights = dict(zip(flexrowidx, pparti(free, [flexrows[j] for j in flexrowidx])))
            fringe = set(flexrowidx)
            while fringe:
                idx = fringe.pop()
                try:
                    ratio = float(flexheights[idx]) / float(self.grid.rows[idx].minheight)
                except ZeroDivisionError:
                    ratio = 1
                if 0 < ratio < 1:
                    for i, h in dict(flexheights).items():
                        flexheights[i] = float(h) * 1. / ratio
                    fringe = set(flexrowidx)
            for row in self.grid.rows:
                # any cell should always have at least the minimum height imposed by the widget containing it,
                # or the height of the highest cell in the grid, or the height yielded by the distribution
                h = max(maxrowheight if layout.equalheights else 0,
                        flexheights.get(row.idx, 0),
                        row.minheight if (row.idx not in flexrows or self.height is None) else 0)
                row.setheights(h)
        if self.grid is not None:
            self.grid.equalize_column_widths()
            self.grid.equalize_row_heights()
            self.compute_cell_positions()
            # self.grid.print_positions()
        self._apply_layout()

    def compute_cell_positions(self):
        if self.grid is not None:
            t, _, _, l = self.fringe
            vcum = t
            for row in self.grid.rows:
                hcum = l
                for cell in row.itercells():
                    cell.hpos = hcum
                    cell.vpos = vcum
                    hcum += cell.width + self.layout.hspace
                vcum += cell.height + self.layout.vspace

    def _apply_layout(self):
        if self.widget is not None and None not in (self.hpos, self.vpos, self.width, self.height):
            x, y, width, height = None, None, None, None
            layout = self.widget.layout
            wwidth, wheight = self._widgetsize
            # horizontal position
            if layout.halign == 'fill':
                x = self.hpos + layout.padding_left
                width = self.width - layout.padding_right - layout.padding_left
            elif layout.halign == 'left':
                x = self.hpos + layout.padding_left
                width = wwidth
            elif layout.halign == 'right':
                x = self.hpos + self.width - wwidth - layout.padding_right
                width = wwidth
            elif layout.halign == 'center':
                x = self.hpos + pc(50).of(self.width) - pc(50).of(wwidth)
                width = wwidth
            # vertical position
            if layout.valign == 'fill':
                y = self.vpos + layout.padding_top
                height = self.height - layout.padding_bottom - layout.padding_top
            elif layout.valign == 'top':
                y = self.vpos + layout.padding_top
                height = wheight
            elif layout.valign == 'bottom':
                y = self.vpos + self.height - wheight - layout.padding_bottom
                height = wheight
            elif layout.valign == 'center':
                y = self.vpos + pc(50).of(self.height) - pc(50).of(wheight)
                height = wheight
            # out('position', self.widget, 'at', x, y, width, height)
            # out('was at', self.hpos, self.vpos, self.width, self.height, 'widget:', wwidth, wheight)
            self.widget.bounds = x, y, width, height


class StackLayoutAdapter(LayoutAdapter):

    def __init__(self, widget, parent, children=None):
        LayoutAdapter.__init__(self, widget, parent, children)
        self._minwidth = None
        self._minheight = None
        self._widgetsize = None
        self._fringe = None

    @property
    def fringe(self):
        if self._fringe is None:
            self._fringe = self.widget.compute_fringe() if self.widget is not None else (0, 0, 0, 0)
        return self._fringe

    @property
    def stack(self):
        return self.children

    @property
    def widget_size(self):
        if self._widgetsize is None:
            self._widgetsize = self.widget.compute_size() if self.widget is not None else (0, 0)
        return self._widgetsize

    def preferred_size(self):
        # preferred horizontal size
        if self._minwidth is None:
            self._minwidth, h = self.widget_size
            if self.stack:
                self._minwidth += max([p.preferred_size()[0] for p in self.stack])
                self._widgetsize =  max(self._minwidth, ifnone(self.layout.minwidth, 0)), h
                # self._minwidth += self.layout.padding_left + self.layout.padding_right
                self._minwidth = max(self._minwidth,
                                     self._widgetsize[0]) + self.layout.padding_left + self.layout.padding_right
                self._minwidth = max(self._minwidth, ifnone(self.layout.cell_minwidth, 0))
        # preferred vertical size
        if self._minheight is None:
            w, self._minheight = self.widget_size
            if self.stack:
                self._minheight += max([p.preferred_size()[1] for p in self.stack])
                self._widgetsize = w, max(self._minheight, ifnone(self.layout.minheight, 0))
                # self._minheight += self.layout.padding_top + self.layout.padding_bottom
                self._minheight = max(self._minheight,
                                      self._widgetsize[1]) + self.layout.padding_top + self.layout.padding_bottom
                self._minheight = max(self._minheight, ifnone(self.layout.cell_minheight, 0))
        return self._minwidth, self._minheight

    @property
    def minwidth(self):
        return self.preferred_size()[0]

    @property
    def minheight(self):
        return self.preferred_size()[1]

    def run(self):
        if self.widget is None:
            return
        layout = self.layout
        # t, r, b, l = self.widget.compute_fringe()
        if self.stack:
            top, right, bottom, left =  self.fringe
            if self.width is not None and layout.halign == 'fill':
                pagewidth = self.width
            else:
                pagewidth = self.minwidth
            pagewidth -= layout.padding_left + layout.padding_right + left + right
            if self.height is not None and layout.valign == 'fill':
                pageheight = self.height
            else:
                pageheight = self.minheight
            pageheight -= layout.padding_top + layout.padding_bottom + top + bottom
            for page in self.stack:
                page.width = pagewidth
                page.height = pageheight
            self.compute_cell_positions()
        self._apply_layout()
        for page in self.stack:
            page.run()

    def compute_cell_positions(self):
        for page in self.stack:
            page.hpos = 0
            page.vpos = 0

    def _apply_layout(self):
        if self.widget is not None and None not in (self.hpos, self.vpos, self.width, self.height):
            x, y, width, height = None, None, None, None
            layout = self.widget.layout
            wwidth, wheight = self._widgetsize
            # horizontal position
            if layout.halign == 'fill':
                x = self.hpos + layout.padding_left
                width = self.width - layout.padding_right - layout.padding_left
            elif layout.halign == 'left':
                x = self.hpos + layout.padding_left
                width = wwidth
            elif layout.halign == 'right':
                x = self.hpos + self.width - wwidth - layout.padding_right
                width = wwidth
            elif layout.halign == 'center':
                x = self.hpos + pc(50).of(self.width) - pc(50).of(wwidth)
                width = wwidth
            # vertical position
            if layout.valign == 'fill':
                y = self.vpos + layout.padding_top
                height = self.height - layout.padding_bottom - layout.padding_top
            elif layout.valign == 'top':
                y = self.vpos + layout.padding_top
                height = wheight
            elif layout.valign == 'bottom':
                y = self.vpos + self.height - wheight - layout.padding_bottom
                height = wheight
            elif layout.valign == 'center':
                y = self.vpos + pc(50).of(self.height) - pc(50).of(wheight)
                height = wheight
            self.widget.bounds = x, y, width, height


def materialize_adapters(shell):
    '''Creates a tree of layout adapters by calling :method:`pyrap.layout.Layout.adapt()` for
    every widget in the hierarchy of the given shell.'''
    cell = _materialize_adapters(shell.content, None)
    return cell


def _materialize_adapters(widget, parent):
    '''Recursive varaint of ``materialize_adapters()``.'''
    adapter = widget.layout.adapt(widget, parent)
    if widget.children:
        adapter.children = [_materialize_adapters(w, adapter) for w in widget.children if not widget.layout.exclude]
    return adapter


class BaseLayout:
    '''Abstract base class for every layout'''

    def adapt(self, widget, parent):
        '''This is a factory method that is supposed to create a layout adapter object for a widget
        given the specified layout. The layout adapter is the layouting class that does the
        actual layout calculations.'''
        raise NotImplementedError()


class Layout(BaseLayout):

    PADDING_TOP = px(5)
    PADDING_RIGHT = px(5)
    PADDING_BOTTOM = px(5)
    PADDING_LEFT = px(5)
    H_ALIGN = 'center'
    V_ALIGN = 'center'

    def __init__(self, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, padding_top=None,
                 padding_right=None, padding_bottom=None, padding_left=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None, padding=None):
        self.minwidth = ifnone(minwidth, None, parse_value)
        self.maxwidth = ifnone(maxwidth, None, parse_value)
        self.minheight = ifnone(minheight, None, parse_value)
        self.maxheight = ifnone(maxheight, None, parse_value)
        self.cell_minwidth = ifnone(cell_minwidth, None, parse_value)
        self.cell_maxwidth = ifnone(cell_maxwidth, None, parse_value)
        self.cell_minheight = ifnone(cell_minheight, None, parse_value)
        self.cell_maxheight = ifnone(cell_maxheight, None, parse_value)
        self.valign = ifnone(valign, type(self).V_ALIGN)
        self.halign = ifnone(halign, type(self).H_ALIGN)

        self.padding_top = ifnone(padding, type(self).PADDING_TOP)
        self.padding_right = ifnone(padding, type(self).PADDING_RIGHT)
        self.padding_bottom = ifnone(padding, type(self).PADDING_BOTTOM)
        self.padding_left = ifnone(padding, type(self).PADDING_LEFT)

        self.padding_top = ifnone(padding_top, self.padding_top)
        self.padding_right = ifnone(padding_right, self.padding_right)
        self.padding_bottom = ifnone(padding_bottom, self.padding_bottom)
        self.padding_left = ifnone(padding_left, self.padding_left)

        self.exclude = False

    @property
    def padding_top(self):
        return self._padding_top

    @padding_top.setter
    def padding_top(self, p):
        self._padding_top = px(p)

    @property
    def padding_right(self):
        return self._padding_right

    @padding_right.setter
    def padding_right(self, p):
        self._padding_right = px(p)


    @property
    def padding_bottom(self):
        return self._padding_bottom

    @padding_bottom.setter
    def padding_bottom(self, p):
        self._padding_bottom = px(p)

    @property
    def padding_left(self):
        return self._padding_left

    @padding_left.setter
    def padding_left(self, p):
        self._padding_left = px(p)

    def adapt(self, widget, parent):
        return Terminal(widget, parent)


class GridLayout(Layout):

    PADDING_TOP = px(0)
    PADDING_RIGHT = px(0)
    PADDING_BOTTOM = px(0)
    PADDING_LEFT = px(0)

    HSPACE = px(0)
    VSPACE = px(0)
    
    H_ALIGN = 'center'
    V_ALIGN = 'center'
    
    EQUAL_HEIGHTS = False
    EQUAL_WIDTHS = False
    SQUARED = False

    H_EXCEED = 'pack'
    V_EXCEED = 'pack'

    def __init__(self, cols=None, rows=None, flexrows=None, flexcols=None, minwidth=None, 
                 maxwidth=None, minheight=None, maxheight=None, valign=None, halign=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None, vspace=None, hspace=None, equalheights=None,
                 equalwidths=None, squared=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None, exceed=None,
                 hexceed=None, vexceed=None):
        Layout.__init__(self, minwidth=minwidth, maxwidth=maxwidth, minheight=minheight,
                        maxheight=maxheight, valign=valign, halign=halign,
                        cell_minwidth=cell_minwidth, cell_maxwidth=cell_maxwidth,
                        cell_minheight=cell_minheight, cell_maxheight=cell_maxheight,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        padding=padding)
        if len([a for a in (cols, rows) if a is not None]) != 1:
            raise LayoutError('You need to specify either the number of rows or the number of cols in a grid layout.')
        if cols is not None:
            self.cols = cols
        elif rows is not None:
            self.rows = rows
        if type(flexrows) is int:
            self.flexrows = {flexrows: 1}
        elif type(flexrows) in (list, tuple):
            self.flexrows = {r: 1 for r in flexrows}
        else:
            self.flexrows = ifnone(flexrows, {})
        if type(flexcols) is int:
            self.flexcols = {flexcols: 1}
        elif type(flexcols) in (list, tuple):
            self.flexcols = {c: 1 for c in flexcols}
        else:
            self.flexcols = ifnone(flexcols, {})
        self.vspace = ifnone(vspace, type(self).VSPACE)
        self.hspace = ifnone(hspace, type(self).HSPACE)
        self.hexceed = ifnone(hexceed, ifnone(exceed, type(self).H_EXCEED))
        self.vexceed = ifnone(vexceed, ifnone(exceed, type(self).V_EXCEED))
        self.equalheights = equalheights
        self.equalwidths = equalwidths
        self.squared = squared

    def adapt(self, widget, parent):
        return GridCell(widget, parent)


class CellLayout(GridLayout): 
    '''This layout consists of only ony single cell. It may only contain
    a signle child widget'''

    def __init__(self, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_minwidth=None, 
                 cell_maxwidth=None, cell_minheight=None, cell_maxheight=None,
                 squared=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None, exceed=None,
                 hexceed=None, vexceed=None):
        GridLayout.__init__(self, cols=1, flexcols={0: 1}, flexrows={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, squared=squared,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        padding=padding, exceed=exceed, vexceed=vexceed, hexceed=hexceed)

    def adapt(self, widget, parent):
        if len(widget.children) > 1:
            raise LayoutError('Cell layout may only have one child. (created at %s)' % str(widget._created))
        return GridCell(widget, parent)


class RowLayout(GridLayout): 
    
    def __init__(self, flexrows=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalheights=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, vspace=None, padding=None, exceed=None,
                 hexceed=None, vexceed=None):
        GridLayout.__init__(self, cols=1, flexrows=flexrows, flexcols={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalheights=equalheights,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right, 
                        vspace=vspace, padding=padding, exceed=exceed, vexceed=vexceed,
                        hexceed=hexceed)
        

class ColumnLayout(GridLayout): 
    
    def __init__(self, flexcols=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalwidths=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, hspace=None, padding=None,
                 exceed=None, hexceed=None, vexceed=None):
        GridLayout.__init__(self, rows=1, flexrows={0: 1}, flexcols=flexcols, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalwidths=equalwidths,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        hspace=hspace, padding=padding, exceed=exceed, vexceed=vexceed,
                        hexceed=hexceed)


class StackLayout(GridLayout):
    
    def __init__(self, minwidth=None, 
                 maxwidth=None, minheight=None, maxheight=None, valign=None, halign=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None, exceed=None,
                 hexceed=None, vexceed=None):
        GridLayout.__init__(self, cols=1, 
                            minwidth=minwidth, maxwidth=maxwidth, minheight=minheight,
                            maxheight=maxheight,
                            valign=valign, halign=halign, cell_minwidth=cell_minwidth,
                            cell_minheight=cell_minheight, cell_maxwidth=cell_maxwidth,
                            cell_maxheight=cell_maxheight, padding_top=padding_top,
                            padding_bottom=padding_bottom, padding_left=padding_left,
                            padding_right=padding_right, padding=padding, vspace=None,
                            equalwidths=(halign=='fill'), equalheights=(valign=='fill'),
                            exceed=exceed, vexceed=vexceed, hexceed=hexceed)

    def adapt(self, widget, parent):
        return StackLayoutAdapter(widget, parent)