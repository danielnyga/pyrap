'''
Created on Dec 2, 2015

@author: nyga
'''
from collections import defaultdict
from itertools import zip_longest
from pprint import pprint

import dnutils
from dnutils import allnone, ifnone, out
from dnutils.stats import stopwatch, print_stopwatches

from pyrap import session
from pyrap.ptypes import pc, BoundedDim, Var, VarCompound, px, parse_value
from pyrap.utils import pparti
from pyrap.constants import inf, RWT
from pyrap.exceptions import LayoutError
import math
import time


# class LayoutData(object):
#
#     def __init__(self, layout):
#         self.cellwidth = BoundedDim(ifnone(layout.cell_minwidth, px(0)), ifnone(layout.cell_maxwidth, px(inf)))
#         if self.cellwidth.min >= self.cellwidth.max:
#             self.cellwidth.value = self.cellwidth.min
#         self.cellheight = BoundedDim(ifnone(layout.cell_minheight, px(0)), ifnone(layout.cell_maxheight, px(inf)))
#         if self.cellheight.min >= self.cellheight.max:
#             self.cellheight.value = self.cellheight.min
#         self.cellhpos = Var(None)
#         self.cellvpos = Var(None)
#         self.halign = layout.halign
#         self.valign = layout.valign
#         self.width = BoundedDim(ifnone(layout.minwidth, px(0)), ifnone(layout.maxwidth, px(inf)))
#         self.height = BoundedDim(ifnone(layout.minheight, px(0)), ifnone(layout.maxheight, px(inf)))
#         self.hpos = Var(None)
#         self.vpos = Var(None)
#         self.dimensions = VarCompound(self.height, self.width, self.cellheight, self.cellwidth, self.cellhpos, self.cellvpos)
#         self.padding_top = layout.padding_top
#         self.padding_right = layout.padding_right
#         self.padding_bottom = layout.padding_bottom
#         self.padding_left = layout.padding_left
#
#     @property
#     def completed(self):
#         return self.dimensions.all_defined
#
#     @property
#     def changed(self):
#         return self.dimensions.dirty
#
#     def clean(self):
#         return self.dimensions.clean()
    

class GridCell:
    '''Represents one single cell in a grid layout'''

    def __init__(self, widget, pcell):
        self.widget = widget
        self.pcell = pcell
        self.grid = None
        self.col = None
        self.row = None
        self.hpos = None
        self.vpos = None
        self.width = None
        self.height = None
        self._minwidth = None
        self._minheight = None
        self._widgetsize = None

    @property
    def widget_size(self):
        if self._widgetsize is None:
            self._widgetsize = self.widget.compute_size() if self.widget is not None else (0, 0)
        return self._widgetsize

    @property
    def minwidth(self):
        if self._minwidth is not None:
            return self._minwidth
        self._minwidth, _ = self.widget_size
        # self._minwidth = int(self._minwidth)
        if self.widget is not None:
            self._minwidth += self.widget.layout.padding_left + self.widget.layout.padding_right
        if self.grid:
            self._minwidth += (len(self.grid.cols) - 1) * self.widget.layout.hspace + sum([c.minwidth for c in self.grid.cols])
        return self._minwidth

    @property
    def minheight(self):
        if self._minheight is not None:
            return self._minheight
        _, self._minheight = self.widget_size
        # self._minheight = int(self._minheight)
        if self.widget is not None:
            self._minheight += self.widget.layout.padding_top + self.widget.layout.padding_bottom
        if self.grid:
            self._minheight += (len(self.grid.cols) - 1) * self.widget.layout.vspace + sum([c.minheight for c in self.grid.rows])
        return self._minheight

    @property
    def flexcols(self):
        if self.widget is None or self.grid is None or self.widget.layout.halign != 'fill': return {}
        return {f: v for f, v in self.widget.layout.flexcols.items() if f < len(self.grid.cols)}

    @property
    def fixcols(self):
        if self.widget is None or self.grid is None: return []
        return [i for i in range(len(self.grid.cols)) if i not in self.flexcols]

    @property
    def flexrows(self):
        if self.widget is None or self.grid is None or self.widget.layout.valign != 'fill': return {}
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
        self.height = None

    def __str__(self):
        return '<Row: [%s]>' % ';'.join(['?' if c.widget is None else c.widget.id for c in self.itercells()])

    @property
    def minheight(self):
        if self._minheight is None:
            self._minheight = max([c.minheight for c in self.itercells()])
        return self._minheight

    def equalize_heights(self):
        max_height = max([c.height for c in self.itercells()])
        for cell in self.itercells():
            cell.height = max_height
        return max_height


class Col(CellSeq):
    '''Represents one column of layout cells in a grid'''

    def __init__(self, idx, cells=None):
        CellSeq.__init__(self, idx, cells)
        self._minwidth = None
        self._width = None

    def __str__(self):
        return '<Col: [%s]>' % (';'.join(['?' if c.widget is None else c.widget.id for c in self.itercells()]))

    @property
    def minwidth(self):
        if self._minwidth is None:
            self._minwidth =  max([c.minwidth for c in self.itercells()])
        return self._minwidth

    def equalize_widths(self):
        max_width = max([c.width for c in self.itercells()])
        for cell in self.itercells():
            cell.width = max_width
        return max_width


class LayoutGrid:
    '''Represents a grid of layout cells'''

    def __init__(self, cell, children=None):
        self.cell = cell
        self.cols = []
        self.rows = []
        self._children = children
        self._materialize()

    def _materialize(self):
        layout = self.cell.widget.layout
        colcount, rowcount = None, None
        if hasattr(layout, 'cols'):
            colcount = layout.cols
        elif hasattr(layout, 'rows'):
            rowcount = layout.rows
        limit = ifnone(colcount, rowcount)
        wmatrix = []
        children = list(self._children)
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

    def equalize_column_widths(self):
        for col in self.cols:
            col.equalize_widths()

    def equalize_row_heights(self):
        for row in self.rows:
            row.equalize_heights()

    def compute_cell_positions(self):
        vcum = 0
        for row in self.rows:
            hcum = 0
            for cell in row.itercells():
                cell.hpos = hcum
                cell.vpos = vcum
                hcum += cell.width
            vcum += cell.height


def compute_minsizes(cell):
    fringe = [cell]
    order = [cell]
    while fringe:
        c = fringe.pop()
        if c.grid is not None:
            children = list(c.grid.itercells())
            fringe.extend(children)
            order.extend(children)
    while order:
        c = order.pop()
        c.width = c.minwidth
        c.height = c.minheight
        if c.grid is not None:
            c.grid.equalize_column_widths()
            c.grid.equalize_row_heights()
        #     c.grid.compute_cell_positions()


def distribute(cell):
    fringe = [cell]
    while fringe:
        cell = fringe.pop(0)
        if cell.grid is not None:
            fringe.extend(cell.grid.itercells())
        if cell.widget is None: continue
        layout = cell.widget.layout
        fringe_width, fringe_height = cell.widget.compute_fringe()
        # out('distributing', cell, cell.grid, layout.halign, cell.hpos, cell.vpos, cell.width, cell.height)
        cont = False
        if cell.grid is not None and layout.halign == 'fill' and cell.width is not None:
            fixcols = cell.fixcols
            flexcols = cell.flexcols
            # =======================================================================
            # if this widget already has a width specified, distribute the flexcols
            # over the remaining free space.
            # =======================================================================
            if layout.equalwidths:
                if fixcols and flexcols:
                    raise LayoutError('Layout is inconsistent: I was told to make columns in %s '
                                      'equal length, but you have manually specified flexcols. '
                                      'Remove them or set all columns be flexible.' % repr(cell.widget))
                fixcols = []
                flexcols = {i: 1 for i in range(len(cell.grid.cols))}
            if not flexcols:
                raise Exception('Layout is underdetermined: I was told to fill %s '
                                'horizontally, but I do not have any flexcols. '
                                '(created at %s)' % (repr(cell.widget), cell.widget._created))
            # if all([c.data.cellwidth.value is not None for i in fixcols for c in self.col(i)]):
            fixcolwidths = 0
            for col in cell.grid.cols:
                colwidth = col.equalize_widths()
                if col.idx in fixcols:
                    fixcolwidths +=  colwidth # the space definitely occupied by fixcols
                for c in col.itercells():
                    c.width = c.minwidth
            fixcolwidths += sum([cell.grid.cols[i].minwidth for i in flexcols])  # + the space at least occupied by the flexcols
            if layout.equalwidths:
                free = cell.width
            else:
                free = cell.width - fixcolwidths - layout.hspace * (len(cell.grid.cols) - 1) - layout.padding_left - layout.padding_right - fringe_width
            flexwidths = pparti(int(free), [flexcols[i] for i in sorted(flexcols)])
            for fci, flexwidth in zip(flexcols, flexwidths):
                for c in cell.grid.cols[fci].itercells():
                    c.width = flexwidth + (c.minwidth if not layout.equalwidths else 0)
        elif cell.width is None:
            cell.width = cell.minwidth
            fringe.append(cell)
            cont = True

        if cell.grid is not None and layout.valign == 'fill' and cell.height is not None:
            fixrows = cell.fixrows
            flexrows = cell.flexrows
            # =======================================================================
            # if this widget already has a height specified, distribute the flexcols
            # over the remaining free space.
            # =======================================================================
            if layout.equalheights:
                if fixrows and flexrows:
                    raise LayoutError('Layout is inconsistent: I was told to make rows in %s '
                                      'equal height, but you have manually specified flexrows. '
                                      'Remove them or set all rows be flexible.' % repr(cell.widget))
                fixrows = []
                flexrows = {i: 1 for i in range(len(cell.grid.rows))}
            if not flexrows:
                raise Exception('Layout is underdetermined: I was told to fill %s '
                                'vertically, but I do not have any flexrows. '
                                '(created at %s)' % (repr(cell.widget), cell.widget._created))
            fixrowheights = 0
            for row in cell.grid.rows:
                rowheight = row.equalize_heights()
                if row.idx in fixrows:
                    fixrowheights += rowheight # the space definitely occupied by fixcols
                for c in row.itercells():
                    c.height = c.minheight
            fixrowheights += sum([cell.grid.rows[i].minheight for i in flexrows])  # + the space at least occupied by the flexcols
            if layout.equalheights:
                free = cell.height
            else:
                free = cell.height - fixrowheights - layout.vspace * (len(cell.grid.rows) - 1) - layout.padding_top - layout.padding_bottom - fringe_height
            flexheights = pparti(int(free), [flexrows[i] for i in sorted(flexrows)])
            for fri, flexheight in zip(flexrows, flexheights):
                for c in cell.grid.rows[fri].itercells():
                    c.height = flexheight + (c.minheight if not layout.equalheights else 0)
        elif cell.height is None:
            cell.height = cell.minheight
            if cell not in fringe:
                fringe.append(cell)
                cont = True
        # if cont: continue
        if cell.grid is not None:
            cell.grid.equalize_column_widths()
            cell.grid.equalize_row_heights()
            cell.grid.compute_cell_positions()


def apply_layout(cell):
    topcell = cell
    fringe = [cell]
    while fringe:
        c = fringe.pop()
        if c.grid is not None:
            fringe.extend(c.grid.itercells())
        # out(c.widget, c.hpos, c.vpos, c.width, c.height)
        if c.widget is not None and None not in (c.hpos, c.vpos, c.width, c.height):
            # if c is cell:
            #     c.widget.bounds = c.hpos, c.vpos, c.width, c.height
            #     continue
            x, y, width, height = None, None, None, None
            layout = c.widget.layout
            wwidth, wheight = c.widget_size
            # horizontal position
            if layout.halign == 'fill':
                x = c.hpos + layout.padding_left
                width = c.width - layout.padding_right - layout.padding_left
            elif layout.halign == 'left':
                x = c.hpos + layout.padding_left
                width = wwidth
            elif layout.halign == 'right':
                x = c.hpos + c.width - wwidth - layout.padding_right
                width = wwidth
            elif layout.halign == 'center':
                x = c.hpos + pc(50).of(c.width) - pc(50).of(wwidth)
                width = wwidth
            # vertical position
            if layout.valign == 'fill':
                y = c.vpos + layout.padding_top
                height = c.height - layout.padding_bottom - layout.padding_top
            elif layout.valign == 'top':
                y = c.vpos + layout.padding_top
                height = wheight
            elif layout.valign == 'bottom':
                y = c.vpos + c.height - wheight - layout.padding_bottom
                height = wheight
            elif layout.valign == 'center':
                y = c.vpos + pc(50).of(c.height) - pc(50).of(wheight)
                height = wheight
            # out(x, y, width, height)
            c.widget.bounds = x, y, width, height
            # c.widget.bounds = c.hpos, c.vpos, c.width, c.height

            # out(cell, cell.minwidth)

def layout(shell, pack):
    out('pack:', pack)
    with stopwatch('/pyrap/layout'):
        cell = materialize_grid(shell)
        compute_minsizes(cell)
        if not pack or shell.maximized:
            cell.hpos, cell.vpos, cell.width, cell.height = shell.client_rect
        distribute(cell)
        if pack and not shell.maximized:
            cell.hpos, cell.vpos, _, _ = shell.client_rect
            cell.width = cell.minwidth
            cell.height = cell.minheight
            h, w = 0, 0
            if shell.title is not None or RWT.TITLE in shell.style:
                h += shell.theme.title_height
            w += cell.width
            h += cell.height
            _, _, dispw, disph = session.runtime.display.bounds
            xpos = int(round(dispw.value / 2. - w.value / 2.))
            ypos = int(round(disph.value / 2. - h.value / 2.))
            shell.bounds = xpos, ypos, w, h
        apply_layout(cell)
    print_stopwatches()


def materialize_grid(shell):
    cell = materialize_gridcell(shell.content, None)
    return cell

def materialize_gridcell(widget, parent):
    cell = GridCell(widget, parent)
    if widget.children:
        cell.grid = LayoutGrid(cell, children=[materialize_gridcell(w, cell) for w in widget.children])
    return cell

def compute_dependency_graph(cell, pack=False):
    # traverse the whole grid hierarchy and build up a tree
    # of widgets that depend on the sizes of one another
    hdeps = DependencyGraph()
    vdeps = DependencyGraph()
    fringe = list([cell])
    while len(fringe):
        c = fringe.pop()
        hdeps.cell(c)
        vdeps.cell(c)
        if c.widget is None: continue
        #####################################################################
        # horizontal
        if c.widget.layout.halign == 'fill' and c.pcell is not None:
            hdeps.add(c, c.pcell)
        elif c.pcell is not None:
            hdeps.add(c.pcell, c)
        #####################################################################
        # vertical
        if c.widget.layout.valign == 'fill' and c.pcell is not None:
            vdeps.add(c, c.pcell)
        elif c.pcell is not None:
            vdeps.add(c.pcell, c)
        if c.grid is not None:
            fringe.extend(c.grid.itercells())
    pprint(hdeps.full_dependencies())
    pprint(vdeps.full_dependencies())
    return hdeps, vdeps


class DependencyGraph:

    def __init__(self):
        self.depmap = defaultdict(list)
        self.cells = set()

    def cell(self, c):
        self.cells.add(c)

    def get(self, cell):
        return self.depmap[cell]

    def add(self, cell, depends_on):
        if cell not in self.cells:
            self.cell(cell)
        if depends_on not in self.cells:
            self.cell(depends_on)
        deps = self.depmap[cell]
        if depends_on not in deps:
            deps.append(depends_on)

    def __contains__(self, cell):
        return cell in self.cells

    def rm(self, cell, dependee, rmcell=False):
        if dependee in self.depmap[cell]:
            self.depmap[cell].remove(dependee)
        if not self.depmap[cell]:
            del self.depmap[cell]
            if rmcell:
                self.cells.remove(cell)

    def depending_on(self, dependee):
        for c, d in self.depmap.items():
            if dependee in d:
                yield c

    def depends_on(self, cell, dependee):
        return dependee in self.depmap[cell]

    def iterdeps(self):
        for cell in self.cells:
            for dep in self.depmap[cell]:
                yield (cell, dep)

    def independents(self):
        return [c for c in self.cells if not self.depmap[c]]

    def full_dependency(self, cell):
        deps = set()
        f = [cell]
        while f:
            n = f.pop()
            dep = self.depmap[n]
            if cell in dep:
                raise LayoutError('detected cyclic dependency (%s and %s mutually depend on each other)' % (cell, n))
            deps.update(dep)
            f.extend(dep)
        return deps

    def full_dependencies(self):
        deps = {c: self.full_dependency(c) for c in self.cells}
        return deps


class LayoutAdapter(object):

    def __init__(self, widget, parent):
        # self.logger = dnutils.getlogger(type(self).__name__, level=dnutils.ERROR)
        self.widget = widget
        self.layout = widget.layout
        self.data = LayoutData(self.layout)
        self.children = []
        self.parent = parent

    def prepare(self): pass
    
    @staticmethod
    def create(widget, parent):
        layout = widget.layout
        grid = None
        # out(layout)
        # if hasattr(layout, 'cols'):
        #     grid = LayoutGrid(colcount=layout.cols)
        # elif hasattr(layout, 'rows'):
        #     grid = LayoutGrid(rowcount=layout.rows)
        # if grid:
        #     grid.setwidgets(widget.children)
        #     out(grid)
        #     out(grid.cols)
        #     out(grid.rows)
        if layout.exclude:
            raise Exception('Cannot create a LayoutAdapter for a Widget that is excluded from layouting.')
        if type(layout) in (GridLayout, RowLayout, ColumnLayout, CellLayout, StackLayout):
            if type(layout) is GridLayout:
                layout = GridLayoutAdapter(widget, parent)
            elif type(layout) is RowLayout:
                layout = RowLayoutAdapter(widget, parent)
            elif type(layout) is ColumnLayout:
                layout = ColumnLayoutAdapter(widget, parent)
            elif type(layout) is CellLayout:
                layout = CellLayoutAdapter(widget, parent)
            elif type(layout) is StackLayout:
                layout = StackLayoutAdapter(widget, parent)
            # if the "exclude" flag is set, do not consider the respective
            # in the layout computations.
            layout.children.extend([LayoutAdapter.create(w, layout) for w in widget.children if not w.layout.exclude])
        else:
            layout = TerminalLayoutAdapter(widget, parent)
        layout.prepare()

        return layout
    
    def clean(self):
        self.data.clean()
        for c in self.children: c.clean()
    
    @property
    def changed(self):
        for c in self.children: 
            if c.changed: return True
        return self.data.changed

    def compute_dependency_graph(self, pack):
        import networkx as nx
        # traverse the whole widget hierarchy and build up a tree
        # of widgets that depend on the sizes of one another
        hdeps = nx.DiGraph()
        vdeps = nx.DiGraph()
        fringe = list(self.children)
        while len(fringe):
            adapter = fringe.pop()
            #####################################################################
            # horizontal
            if adapter.layout.halign == 'fill':
                from_node, from_adapt = adapter.widget.id, adapter
                to_node, to_adapt = adapter.widget.parent.id, adapter.parent
            else:
                from_node, from_adapt = adapter.widget.parent.id, adapter.parent
                to_node, to_adapt = adapter.widget.id, adapter
            # add "from" node if not existent
            if from_adapt is not None and from_node not in hdeps.nodes():
                hdeps.add_node(from_node, adapter=from_adapt)
            # add "to" node if not existent
            if to_adapt is not None and to_node not in hdeps.nodes():
                hdeps.add_node(to_node, adapter=to_adapt)
            # add dependency edge
            if (from_adapt, to_adapt) != (None, None):
                hdeps.add_edge(from_node, to_node)
            #####################################################################
            # vertical
            if adapter.layout.valign == 'fill':
                from_node, from_adapt = adapter.widget.id, adapter
                to_node, to_adapt = adapter.widget.parent.id, adapter.parent
            else:
                from_node, from_adapt = adapter.widget.parent.id, adapter.parent
                to_node, to_adapt = adapter.widget.id, adapter
            if to_adapt and to_node not in vdeps.nodes():
                vdeps.add_node(to_node, adapter=to_adapt)
            if from_adapt and from_node not in vdeps.nodes():
                vdeps.add_node(from_node, adapter=from_adapt)
            if (from_adapt, to_adapt) != (None, None):
                vdeps.add_edge(from_node, to_node)
            fringe.extend(adapter.children)
        # check consistency

        # out('all nodes:', vdeps.nodes())
        out('vertical deps:')
        myid = self.widget.id
        out('myid is', myid)
        for e in vdeps.edges():
            if e[1] == myid and pack:
                vdeps.remove_edge(*e)
                vdeps.add_edge(myid, e[0])
        for e in vdeps.edges():
            out(e)
        out('horizontal edges:')
        for e in hdeps.edges():
            if e[1] == myid and pack:
                hdeps.remove_edge(*e)
                hdeps.add_edge(myid, e[0])
        for e in hdeps.edges():
            out(e)
        return hdeps, vdeps

    def _compute_verticals(self):
        raise NotImplementedError()

    def _compute_horizontals(self):
        raise NotImplementedError()

    def compute_verticals(self, vdeps):
        fringe = [n for n in vdeps.nodes() if not vdeps.successors(n)] # all nodes without parents
        adapters = set()
        processed = set()
        while fringe:
            node = fringe.pop(0)
            if node in processed:
                continue
            processed.add(node)
            adapter = vdeps.node[node]['adapter']
            adapter._compute_verticals()
            self.logger.info('computing vertical dimensions for', adapter.widget, adapter.data.height)
            fringe.extend(vdeps.predecessors(node))
        return adapters

    def compute_horizontals(self, hdeps):
        fringe = [n for n in hdeps.nodes() if not hdeps.successors(n)] # all nodes without parents
        adapters = set()
        processed = set()
        while fringe:
            node = fringe.pop(0)
            if node in processed:
                continue
            processed.add(node)
            adapter = hdeps.node[node]['adapter']
            adapters.add(adapter)
            adapter._compute_horizontals()
            out('computing horizontal dimensions for', adapter.widget, adapter.data.width)
            fringe.extend(hdeps.predecessors(node))
        return adapters

    def compute(self, pack=False):
        start = time.time()
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        # compute dependencies among widgets
        if not pack:
            self.data.width.value = self.widget.width
            self.data.height.value = self.widget.height
            out(self.widget, 'bounds:', list(map(str, self.widget.bounds)))
        hdeps, vdeps = self.compute_dependency_graph(pack)
        # compute the vertical components
        adapters = set()
        adapters.update(self.compute_horizontals(hdeps))
        adapters.update(self.compute_verticals(vdeps))
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        self.logger.info('layout computation took %s sec' % (time.time() - start))
        self.logger.info('apply layout...')
        self._compute_widget()
        self.logger.info('layout application done.')
    
    def _compute(self):
        raise Exception('Not implemented.')

    def _compute_widget(self):
        x, y, width, height = None, None, None, None
        # horizontal position
        if self.layout.halign == 'fill':
            x = self.data.cellhpos() + self.layout.padding_left
            width = self.data.cellwidth.value - self.layout.padding_right - self.layout.padding_left
        elif self.layout.halign == 'left':
            x = self.data.cellhpos() + self.layout.padding_left
            width = self.data.width.value
        elif self.layout.halign == 'right':
            out(self.widget, self.data.cellhpos.value, self.data.cellwidth.value, self.data.width.value, self.layout.padding_right)
            x = self.data.cellhpos.value + self.data.cellwidth.value - self.data.width.value - self.layout.padding_right
            width = self.data.width.value
        elif self.layout.halign == 'center':
            out(self.widget, self.data.cellwidth.value, self.data.width.value)
            x = self.data.cellhpos.value + pc(50).of(self.data.cellwidth.value) - pc(50).of(self.data.width.value)
            width = self.data.width.value
        # vertical position
        if self.layout.valign == 'fill':
            y = self.data.cellvpos() + self.layout.padding_top
            height = self.data.cellheight() - self.layout.padding_bottom - self.layout.padding_top
        elif self.layout.valign == 'top':
            y = self.data.cellvpos() + self.layout.padding_top
            height = self.data.height.value
        elif self.layout.valign == 'bottom':
            y = self.data.cellvpos() + self.data.cellheight.value - self.data.height.value - self.layout.padding_bottom
            height = self.data.height.value
        elif self.layout.valign == 'center':
            out(self.widget, self.data.cellvpos.value, self.data.cellheight.value, self.data.height.value)
            y = self.data.cellvpos() + pc(50).of(self.data.cellheight.value) - pc(50).of(self.data.height.value)
            height = self.data.height.value
#         out(self.widget, ':', x, y, width, height)
        self.widget.bounds = x, y, width, height
        for c in self.children:
            c._compute_widget()
    

class GridLayoutAdapter(LayoutAdapter): 

    def _compute_horizontals(self):
        my = self.data
        widget = self.widget
        layout = self.layout
        # indent = '   ' * level
        self.logger.debug('computing horizontal layout for', widget.id, repr(widget), 'cell:', self.data.cellwidth,
                          self.data.cellheight, 'widget', self.data.width, self.data.height)

        fringe_width, _ = widget.compute_fringe()
        fixcols = [i for i in range(self.colcount()) if i not in layout.flexcols]
        flexcols = {f: v for f, v in layout.flexcols.items() if f < self.colcount()}

        # =======================================================================
        # if this widget already has a width specified, distribute the flexcols
        # over the remaining free space.
        # =======================================================================
        if my.width.value is not None and layout.halign == 'fill':  # and not RWT.HSCROLL in widget.style:
            if layout.equalwidths:
                if fixcols and flexcols:
                    raise LayoutError('Layout is inconsistent: I was told to make columns in %s '
                                      'equal length, but you have manually specified flexcols. '
                                      'Remove them or set all columns be flexible.' % repr(self.widget))
                fixcols = []
                flexcols = {i: 1 for i in range(self.colcount())}
            if not flexcols:
                raise Exception('Layout is underdetermined: I was told to fill %s '
                                'horizontally, but I do not have any flexcols. '
                                '(created at %s)' % (repr(self.widget), self.widget._created))
            if all([c.data.cellwidth.value is not None for i in fixcols for c in self.col(i)]):
                self.logger.debug('distributing over all flexcols')
                occ = sum([self.col(i)[0].data.cellwidth.value for i in fixcols if self.col(i)])
                occ += sum([self.col(i)[0].data.cellwidth.min for i in flexcols if self.col(i)])
                free = px(my.width.value - occ - layout.hspace * (
                self.colcount() - 1) - layout.padding_left - layout.padding_right - fringe_width)
                flexwidths = pparti(free.value, [flexcols[i] for i in sorted(flexcols)])
                for fci, flexwidth in zip(flexcols, flexwidths):
                    for c in self.col(fci):
                        c.data.cellwidth.value = px(flexwidth + c.data.cellwidth.min)

        mywidth, _ = widget.compute_fringe()

        # ======================================
        # make all cells of a column equal width
        # ======================================
        wmaxt = px(0)
        wmaxg = px(0)
        for i in range(self.colcount()):
            wmax = px(0)
            for c in self.col(i):
                wmax = max(wmax, c.data.cellwidth.min)
                wmaxg = max(wmax, wmaxg)
            for c in self.col(i):
                c.data.cellwidth.min = wmax
                if i not in flexcols or layout.halign != 'fill':
                    c.data.cellwidth.value = wmax
            wmaxt += wmax
        if layout.equalwidths:
            wmaxt = wmaxg * self.colcount()
            for cells in self.itercols():
                for c in cells:
                    if i not in flexcols or layout.halign != 'fill':
                        c.data.cellwidth.value = wmaxg
                        # if layout.squared:
                        #     m = max(hmaxg, wmaxg)
                        #     hmaxt = m * self.rowcount()
                        #     wmaxt = m * self.colcount()
                        #     for cells in self.itercols():
                        #         for c in cells:
                        #             if i not in flexrows or not layout.valign == 'fill':
                        #                 c.data.cellheight.value = c.data.cellwidth.value = m
        children_width = max(my.width.min,
                             wmaxt + layout.hspace * (self.colcount() - 1) + layout.padding_left + layout.padding_right)
        # =======================================================================
        # if the width of the cell is specified, adjust the width of the
        # widget in case that halign = 'fill'
        # =======================================================================
        if layout.halign == 'fill':
            my.width.value = my.cellwidth.value
            my.cellwidth.min = mywidth + (children_width if not RWT.HSCROLL in widget.style else 0)
        else:
            my.width.value = mywidth + (children_width if not RWT.HSCROLL in widget.style else 0)
            my.cellwidth.min = my.width.value

        # if not (layout.halign == 'fill' and layout.valign == 'fill'):
        #     self._compute_children(level)
        # =======================================================================
        # compute the cell positions if we know our width
        # the width/height of all our children
        # =======================================================================
        xoffset, _ = widget.viewport()
        if my.width.value is not None and all([c[0].data.cellwidth.value is not None for c in self.itercols()]):
            cum = layout.padding_left + xoffset
            for cells in self.itercols():
                for c in cells:
                    c.data.cellhpos.set(cum)
                cum += c.data.cellwidth.value + layout.hspace


    def _compute_verticals(self):
        my = self.data
        widget = self.widget
        layout = self.layout
        # indent = '   ' * level
        self.logger.debug('computing vertical dimensions for', widget.id, repr(widget), 'cell:', self.data.cellwidth,
                          self.data.cellheight, 'widget', self.data.width, self.data.height)
        _, fringe_height = widget.compute_fringe()
        fixrows = [i for i in range(self.rowcount()) if i not in layout.flexrows]
        flexrows = {f: v for f, v in layout.flexrows.items() if f < self.rowcount()}
        # =======================================================================
        # make cells of a row equal height
        # =======================================================================
        hmaxt = px(0)
        hmaxg = px(0)
        for i in range(self.rowcount()):
            hmax = px(0)
            for c in self.row(i):
                hmax = max(hmax, c.data.cellheight.min)
                hmaxg = max(hmax, hmaxg)
            for c in self.row(i):
                c.data.cellheight.min = hmax
                if i not in flexrows or layout.valign != 'fill':
                    c.data.cellheight.value = hmax
            hmaxt += hmax
        if layout.equalheights:
            hmaxt = hmaxg * self.rowcount()
            for cells in self.iterrows():
                for c in cells:
                    if i not in flexrows or layout.valign != 'fill':
                        c.data.cellheight.value = hmaxg
        # if layout.squared:
        #     m = max(hmaxg, wmaxg)
        #     hmaxt = m * self.rowcount()
        #     wmaxt = m * self.colcount()
        #     for cells in self.itercols():
        #         for c in cells:
        #             if i not in flexrows or not layout.valign == 'fill':
        # =======================================================================
        # if this widget already has a height specified, distribute the flexrows
        # over the remaining free space.
        # =======================================================================
        if my.height.value is not None and layout.valign == 'fill':  # and not RWT.VSCROLL in widget.style:
            if layout.equalheights:
                if fixrows and flexrows:
                    raise LayoutError('Layout is inconsistent: I was told to make columns in %s equal height, '
                                      'but you have manually specified flexrows. Remove them or set all rows be flexible.' % repr(self.widget))
                fixrows = []
                flexrows = {i: 1 for i in range(self.rowcount())}
            if not flexrows:
                raise LayoutError(
                    'Layout is underdetermined: I was told to fill %s vertically, but I do not have any flexrows. (created at %s)' % (
                    repr(self.widget), self.widget._created))
            if all([c.data.cellheight.value is not None for i in fixrows for c in self.row(i)]):
                occ = sum([self.row(i)[0].data.cellheight.value for i in fixrows if self.row(i)])
                occ += sum([self.row(i)[0].data.cellheight.min for i in flexrows if self.row(i)])
                free = px(my.height.value - occ - layout.vspace * (
                self.rowcount() - 1) - layout.padding_top - layout.padding_bottom - fringe_height)
                flexheights = pparti(free.value, [flexrows[i] for i in sorted(flexrows)])
                for fci, flexheight in zip(flexrows, flexheights):
                    for c in self.row(fci):
                        c.data.cellheight.value = px(flexheight + c.data.cellheight.min)

        #                 c.data.cellheight.value = c.data.cellwidth.value = m

        _, myheight = widget.compute_fringe()

        children_height = max(my.height.min, hmaxt + layout.vspace * (self.rowcount() - 1) + layout.padding_top + layout.padding_bottom)
        # =======================================================================
        # if the height of the cell is specified, adjust the height of the
        # widget in case that valign='fill'
        # =======================================================================
        if layout.valign == 'fill':
            my.height.value = my.cellheight.value
            my.cellheight.min = myheight + (children_height if not RWT.VSCROLL in widget.style else 0)
        else:
            my.height.value = myheight + (children_height if not RWT.VSCROLL in widget.style else 0)
            my.cellheight.min = my.height.value

        # order is is now handled by the dependency graph:
        # if not (layout.halign == 'fill' and layout.valign == 'fill'):
        #     self._compute_children(level)
        # =======================================================================
        # compute the cell positions if we know our width/height
        # the width/height of all our children
        # =======================================================================
        _, yoffset = widget.viewport()
        # if my.width.value is not None and all([c[0].data.cellwidth.value is not None for c in self.itercols()]):
        #     cum = layout.padding_left + xoffset
        #     for cells in self.itercols():
        #         for c in cells:
        #             c.data.cellhpos.set(cum)
        #         cum += c.data.cellwidth.value + layout.hspace
        if my.height.value is not None and all([c[0].data.cellheight.value is not None for c in self.iterrows()]):
            cum = layout.padding_top + yoffset
            for cells in self.iterrows():
                for c in cells:
                    c.data.cellvpos.set(cum)
                cum += c.data.cellheight.value + layout.vspace


    def __init__(self, widget, parent):
        LayoutAdapter.__init__(self, widget, parent)
    
    def prepare(self): pass
    
    def rowcount(self):
        if hasattr(self.layout, 'rows'):
            return self.layout.rows
        return math.ceil(len(self.children) / self.colcount())
    
    def colcount(self):
        if hasattr(self.layout, 'cols'):
            return self.layout.cols
        return math.ceil(len(self.children) / self.rowcount())
    
    def iterrows(self):
        for i in range(self.rowcount()):
            yield self.row(i)
            
    def itercols(self):
        for i in range(self.colcount()):
            c = self.col(i)
            if c: yield c 
    
    def row(self, i):
        i *= self.colcount()
        return self.children[i:min(len(self.children), i+self.colcount())]
    
    def col(self, i):
        return self.children[i::self.colcount()]
        
    def visualize_grid(self, indent):
        print(indent, self.rowcount(), 'x', self.colcount())
        for cells in self.iterrows():
            print(indent, ';'.join(c.widget.id for c in cells))
            
    def write(self, level=0, check=False):
        self.visualize_grid('  ' * (level+1))
        LayoutAdapter.write(self, level, check)
        
        
class RowLayoutAdapter(GridLayoutAdapter): pass
    
class ColumnLayoutAdapter(GridLayoutAdapter): pass 

class CellLayoutAdapter(GridLayoutAdapter):
    
    def __init__(self, widget, parent):
        GridLayoutAdapter.__init__(self, widget, parent)
        if len(widget.children) > 1:
            raise Exception('A cell cannot contain more than one element! (%s, children: %s)' % (repr(widget), list(map(repr, widget.children))))
    

class TerminalLayoutAdapter(LayoutAdapter): 
    
    def _compute_verticals(self):
        my = self.data
        widget = self.widget
        layout = self.layout
#         out(indent, 'computing layout for', widget.id)
        w, h = widget.compute_size()
        # my.width.value = max(ifnone(my.width.min, 0), w)
        my.height.value = max(ifnone(my.height.min, 0), h)
        # my.cellwidth.min = my.width.value + layout.padding_left + layout.padding_right
        my.cellheight.min = my.height.value + layout.padding_top + layout.padding_bottom
        # self._done = True

    def _compute_horizontals(self):
        my = self.data
        widget = self.widget
        layout = self.layout
        #         out(indent, 'computing layout for', widget.id)
        w, h = widget.compute_size()
        my.width.value = max(ifnone(my.width.min, 0), w)
        # my.height.value = max(ifnone(my.height.min, 0), h)
        my.cellwidth.min = my.width.value + layout.padding_left + layout.padding_right
        # my.cellheight.min = my.height.value + layout.padding_top + layout.padding_bottom


class StackLayoutAdapter(GridLayoutAdapter):
    def _compute_cells(self, level=0):
        my = self.data
        widget = self.widget
        layout = self.layout
        indent = '   ' * level
        self.logger.debug(indent, 'computing layout for', widget.id, repr(widget), 'cell:', self.data.cellwidth,
                          self.data.cellheight, 'widget', self.data.width, self.data.height)

        if not (layout.halign == 'fill' and layout.valign == 'fill'):
            self._compute_children(level)

        # my.cellwidth.min = max(my.width.min, mywidth)
        #         my.cellheight.min = max(my.height.min, myheight)
        fringe_width, fringe_height = widget.compute_fringe()
        # =======================================================================
        # if this widget already has a width specified, distribute the flexcols
        # over the remaining free space.
        # =======================================================================
        fixcols = [i for i in range(self.colcount()) if i not in layout.flexcols]
        flexcols = {f: v for f, v in layout.flexcols.items() if f < self.colcount()}
        if my.width.value is not None and layout.halign == 'fill':
            if layout.equalwidths:
                if fixcols and flexcols:
                    raise LayoutError(
                        'Layout is inconsistent: I was told to make columns in %s equal length, but you have manually specified flexcols. Remove them or set all columns be flexible.' % repr(
                            self.widget))
                fixcols = []
                flexcols = {i: 1 for i in range(self.colcount())}
            if not flexcols:
                raise Exception(
                    'Layout is underdetermined: I was told to fill %s horizontally, but I do not have any flexcols. (created at %s)' % (
                    repr(self.widget), self.widget._created))
            if all([c.data.cellwidth.value is not None for i in fixcols for c in self.col(i)]):
                for fci in flexcols:
                    for c in self.col(fci):
                        c.data.cellwidth.value = px(
                            my.cellwidth.value - layout.padding_left - layout.padding_right - fringe_width)
        # =======================================================================
        # if this widget already has a height specified, distribute the flexrows
        # over the remaining free space.
        # =======================================================================
        fixrows = [i for i in range(self.rowcount()) if i not in layout.flexrows]
        flexrows = {f: v for f, v in layout.flexrows.items() if f < self.rowcount()}
        if my.height.value is not None and layout.valign == 'fill':
            if layout.equalheights:
                if fixrows and flexrows:
                    raise LayoutError(
                        'Layout is inconsistent: I was told to make columns in %s equal height, but you have manually specified flexrows. Remove them or set all rows be flexible.' % repr(
                            self.widget))
                fixrows = []
                flexrows = {i: 1 for i in range(self.rowcount())}
            if not flexrows:
                raise Exception(
                    'Layout is underdetermined: I was told to fill %s vertically, but I do not have any flexrows. (created at %s)' % (
                    repr(self.widget), self.widget._created))
            if all([c.data.cellheight.value is not None for i in fixrows for c in self.row(i)]):
                for fci in flexrows:
                    for c in self.row(fci):
                        c.data.cellheight.value = px(
                            my.cellheight.value - layout.padding_top - layout.padding_bottom - fringe_height)
        # =======================================================================
        # make all cells of a column equal width and all cells of a row equal height
        # =======================================================================
        wmaxt = px(0)
        wmaxg = px(0)
        for i in range(self.colcount()):
            wmax = px(0)
            for c in self.col(i):
                #                 if RWT.HSCROLL in c.widget.style: continue
                wmax = max(wmax, c.data.cellwidth.min)
                wmaxg = max(wmax, wmaxg)
            for c in self.col(i):
                c.data.cellwidth.min = wmax
                if i not in flexcols or not layout.halign == 'fill':
                    c.data.cellwidth.value = wmax
            wmaxt += wmax
        if layout.equalwidths:
            wmaxt = wmaxg * self.colcount()
            for cells in self.itercols():
                for c in cells:
                    if i not in flexcols or not layout.halign == 'fill':
                        c.data.cellwidth.value = wmaxg
        hmaxt = px(0)
        hmaxg = px(0)
        for i in range(self.rowcount()):
            hmax = px(0)
            for c in self.row(i):
                #                 if RWT.VSCROLL in c.widget.style: continue
                hmax = max(hmax, c.data.cellheight.min)
                hmaxg = max(hmax, hmaxg)
            for c in self.row(i):
                c.data.cellheight.min = hmax
                if i not in flexrows or not layout.valign == 'fill':
                    c.data.cellheight.value = hmax
            hmaxt += hmax
        if layout.equalheights:
            hmaxt = hmaxg * self.rowcount()
            for cells in self.iterrows():
                for c in cells:
                    if i not in flexrows or not layout.valign == 'fill':
                        c.data.cellheight.value = hmaxg
        if layout.squared:
            m = max(hmaxg, wmaxg)
            hmaxt = m * self.rowcount()
            wmaxt = m * self.colcount()
            for cells in self.itercols():
                for c in cells:
                    if i not in flexrows or not layout.valign == 'fill':
                        c.data.cellheight.value = c.data.cellwidth.value = m
                        c._done = True

        mywidth, myheight = widget.compute_fringe()

        children_width = max(my.width.min, wmaxg + layout.padding_left + layout.padding_right)
        children_height = max(my.height.min, hmaxg + layout.padding_top + layout.padding_bottom)
        # =======================================================================
        # if the width/height of the cell is specified, adjust the width/height of the
        # widget in case that halign/valign='fill'
        # =======================================================================
        if layout.halign == 'fill':
            my.width.value = my.cellwidth.value
            my.cellwidth.min = mywidth + (children_width if not RWT.HSCROLL in widget.style else 0)
        else:
            my.width.value = mywidth + (children_width if not RWT.HSCROLL in widget.style else 0)
            my.cellwidth.min = my.width.value
        if layout.valign == 'fill':
            my.height.value = my.cellheight.value
            my.cellheight.min = myheight + (children_height if not RWT.VSCROLL in widget.style else 0)
        else:
            my.height.value = myheight + (children_height if not RWT.VSCROLL in widget.style else 0)
            my.cellheight.min = my.height.value

        if (layout.halign == 'fill' and layout.valign == 'fill'):
            self._compute_children(level)

        # compute the cell positions if we know our width/height
        # the width/height of all our children
        xoffset, yoffset = widget.viewport()
        if my.width.value is not None and all([c[0].data.cellwidth.value is not None for c in self.itercols()]):
            cum = layout.padding_left + xoffset
            for cells in self.itercols():
                for c in cells:
                    c.data.cellhpos.set(cum)
                    #                 cum += c.data.cellwidth.value + layout.hspace
        if my.height.value is not None and all([c[0].data.cellheight.value is not None for c in self.iterrows()]):
            cum = layout.padding_top + yoffset
            for cells in self.iterrows():
                for c in cells:
                    c.data.cellvpos.set(cum)


# cum += c.data.cellheight.value + layout.vspace
#         if my.width.value is not None and my.height.value is not None and\
#              (layout.halign != 'fill' and layout.valign != 'fill' or my.height.value is not None and my.width.value is not None):
#             self._done = True

class Layout(object):
    
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
    
    def __init__(self, cols=None, rows=None, flexrows=None, flexcols=None, minwidth=None, 
                 maxwidth=None, minheight=None, maxheight=None, valign=None, halign=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None, vspace=None, hspace=None, equalheights=None,
                 equalwidths=None, squared=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None):
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
        self.equalheights = equalheights
        self.equalwidths = equalwidths
        self.squared = squared 


class CellLayout(GridLayout): 
    
    def __init__(self, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_minwidth=None, 
                 cell_maxwidth=None, cell_minheight=None, cell_maxheight=None,
                 squared=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None):
        GridLayout.__init__(self, cols=1, flexcols={0: 1}, flexrows={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, squared=squared,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        padding=padding)


class RowLayout(GridLayout): 
    
    def __init__(self, flexrows=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalheights=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, vspace=None, padding=None):
        GridLayout.__init__(self, cols=1, flexrows=flexrows, flexcols={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalheights=equalheights,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right, 
                        vspace=vspace, padding=padding)
        

class ColumnLayout(GridLayout): 
    
    def __init__(self, flexcols=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalwidths=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, hspace=None, padding=None):
        GridLayout.__init__(self, rows=1, flexrows={0: 1}, flexcols=flexcols, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalwidths=equalwidths,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        hspace=hspace, padding=padding)
        
class StackLayout(GridLayout):
    
    def __init__(self, minwidth=None, 
                 maxwidth=None, minheight=None, maxheight=None, valign=None, halign=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None,
                 padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, padding=None):
        GridLayout.__init__(self, cols=1, 
                            minwidth=minwidth, maxwidth=maxwidth, minheight=minheight,
                            maxheight=maxheight,
                            valign=valign, halign=halign, cell_minwidth=cell_minwidth,
                            cell_minheight=cell_minheight, cell_maxwidth=cell_maxwidth,
                            cell_maxheight=cell_maxheight, padding_top=padding_top,
                            padding_bottom=padding_bottom, padding_left=padding_left,
                            padding_right=padding_right, padding=padding, vspace=None,
                            equalwidths=(halign=='fill'), equalheights=(valign=='fill'))
        
        
        
