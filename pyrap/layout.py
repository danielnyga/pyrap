'''
Created on Dec 2, 2015

@author: nyga
'''
from pyrap.types import pc, BoundedDim, Var, VarCompound, px, parse_value
from pyrap.utils import out, ifnone, pparti
from pyrap.constants import inf, RWT
from pyrap.exceptions import LayoutError
import math


class LayoutData(object):
    
    def __init__(self, layout):
        self.cellwidth = BoundedDim(ifnone(layout.cell_minwidth, 0), ifnone(layout.cell_maxwidth, inf))
        self.cellheight = BoundedDim(ifnone(layout.cell_minheight, 0), ifnone(layout.cell_maxheight, inf))
        self.cellhpos = Var(None)
        self.cellvpos = Var(None)
        self.halign = layout.halign
        self.valign = layout.valign
        self.width = BoundedDim(ifnone(layout.minwidth, 0), ifnone(layout.maxwidth, inf))
        self.height = BoundedDim(ifnone(layout.minheight, 0), ifnone(layout.maxheight, inf))
        self.hpos = Var(None)
        self.vpos = Var(None)
        self.dimensions = VarCompound(self.height, self.width, self.cellheight, self.cellwidth, self.cellhpos, self.cellvpos)

    @property
    def completed(self):
        return self.dimensions.all_defined
    
    @property
    def changed(self):
        return self.dimensions.dirty
    
    def clean(self):
        return self.dimensions.clean()
    

class LayoutAdapter(object): 

    def __init__(self, widget, parent):
        self.widget = widget
        self.layout = widget.layout
        self.data = LayoutData(self.layout)
        self.children = []
        self.parent = parent
#         self.write()
    
    def prepare(self): pass
    
    @staticmethod
    def create(widget, parent):
        layout = widget.layout
        if type(layout) in (GridLayout, RowLayout, ColumnLayout, CellLayout):
            if type(layout) is GridLayout:
                layout = GridLayoutAdapter(widget, parent)
            elif type(layout) is RowLayout:
                layout = RowLayoutAdapter(widget, parent)
            elif type(layout) is ColumnLayout:
                layout = ColumnLayoutAdapter(widget, parent)
            elif type(layout) is CellLayout:
                layout = CellLayoutAdapter(widget, parent)
            layout.children.extend([layout.create(w, layout) for w in widget.children])
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
    
    def compute(self): 
        while True:
            self.clean()
            self._compute_cells()
            if not self.changed: break
#         self.write(check=True)
        self._compute_widget()
    
    def _compute(self):
        raise Exception('Not implemented.')
    
    
    def write(self, level=0, check=False):
        indent = '   ' * (level + 1)
        if check:
            ok = all([self.data.cellwidth(), self.data.cellheight(), self.data.cellhpos(), self.data.cellvpos()]) 
        else:
            ok = True
        if not ok:
            indent = '-->' + indent[3:]
        print indent, '%s [%s]  (x: %s y: %s) width: [%s ; %s ; %s] height: [%s ; %s ; %s]' % (repr(self.widget), ','.join([w.widget.id for w in self.children]), 
                                                                                                   str(self.data.cellhpos), str(self.data.cellvpos), 
                                                                                                   str(self.data.cellwidth.min), str(self.data.cellwidth.value), str(self.data.cellwidth.max),
                                                                                                   str(self.data.cellheight.min), str(self.data.cellheight.value), str(self.data.cellheight.max))
        for c in self.children:
            c.write(level+1, check=check)
            
    def _compute_widget(self):
        x, y, width, height = None, None, None, None
        # horizontal position
        layout = self.layout
        if self.layout.halign == 'fill':
            x = self.data.cellhpos()
            width = self.data.cellwidth()
        elif self.layout.halign == 'left':
            x = self.data.cellhpos()
            width = self.data.width.min
        elif self.layout.halign == 'right':
            x = self.data.cellhpos() + self.data.cellwidth() - self.data.width.min
            width = self.data.width.min
        elif self.layout.halign == 'center':
            x = self.data.cellhpos() + pc(50).of(self.data.cellwidth()) - pc(50).of(self.data.width.min)
            width = self.data.width.min
        # vertical position
        if self.layout.valign == 'fill':
            y = self.data.cellvpos()
            height = self.data.cellheight()
        elif self.layout.valign == 'top':
            y = self.data.cellvpos()
            height = self.data.height.min
        elif self.layout.valign == 'bottom':
            y = self.data.cellvpos() + self.data.cellheight() - self.data.height.min
            height = self.data.height.min
        elif self.layout.valign == 'center':
            y = self.data.cellvpos() + pc(50).of(self.data.cellheight()) - pc(50).of(self.data.height.min)
            height = self.data.height.min
        self.widget.bounds = x, y, width, height
        for c in self.children:
            c._compute_widget()
    

class GridLayoutAdapter(LayoutAdapter): 
    
    def __init__(self, widget, parent):
        LayoutAdapter.__init__(self, widget, parent)
    
    def prepare(self): pass
    
    def rowcount(self):
        if hasattr(self.layout, 'rows'):
            return self.layout.rows
        return int(math.ceil(len(self.children) / float(self.colcount())))
    
    def colcount(self):
        if hasattr(self.layout, 'cols'):
            return self.layout.cols
        return int(math.ceil(len(self.children) / float(self.rowcount())))
    
    def iterrows(self):
        for i in range(self.rowcount()):
            yield self.row(i)
            
    def itercols(self):
        for i in range(self.colcount()):
            yield self.col(i)
    
    def row(self, i):
        i *= self.colcount()
        return self.children[i:min(len(self.children), i+self.colcount())]
    
    def col(self, i):
        return self.children[i::self.colcount()]
        
    def visualize_grid(self, indent):
        print indent, self.rowcount(), 'x', self.colcount()
        for cells in self.iterrows():
            print indent, ';'.join(c.widget.id for c in cells)
            
    def write(self, level=0, check=False):
        self.visualize_grid('  ' * (level+1))
        LayoutAdapter.write(self, level, check)
        
        
    def _compute_children(self, level):
        indent = '   ' * level
        while True:
            changed = False
            for c in self.children: 
                c.clean()
                c._compute_cells(level+1)
                changed |= c.changed
            if not changed: break
#             out(indent, self.widget.id, 'has changed. again')
#         out(indent, 'no changes in', self.widget.id)
        
    def _compute_cells(self, level=0):
        self._compute_children(level)
        indent = '   ' * level
        my = self.data
        widget = self.widget
        layout = self.layout
        out(indent, 'computing layout for', widget.id)

        # we have a fixed width, so distribute the columns over it
        fixcols = [i for i in range(self.colcount())  if i not in layout.flexcols]
        flexcols = [f for f in layout.flexcols if f < self.colcount()]
        if my.cellwidth() is not None and layout.halign == 'fill':
            if layout.equalwidths:
                if fixcols and flexcols:
                    raise LayoutError('Layout is inconsistent: I was told to make columns in %s equal length, but you have manually specified flexcols. Remove them or set all columns be flexible.' % repr(self.widget))
                fixcols = []
                flexcols = {i: 1 for i in range(self.colcount())}
            if not flexcols:
                raise Exception('Layout is underdetermined: I was told to fill %s horizontally, but I do not have any flexcols.' % repr(self.widget))
            if all([c.data.cellwidth() is not None for i in fixcols for c in self.col(i)]):
                occ = sum([self.col(i)[0].data.cellwidth() for i in fixcols])
                occ += sum([self.col(i)[0].data.cellwidth.min for i in flexcols])
                free = my.cellwidth() - occ - layout.hspace * (self.colcount() - 1) - layout.padding_left - layout.padding_right
                flexwidths = pparti(free.value, [layout.flexcols[f] for f in flexcols])
                for fci, flexwidth in zip(flexcols, flexwidths):
                    for c in self.col(fci):
                        c.data.cellwidth.value = px(flexwidth + c.data.cellwidth.min)
            
        # we have a fixed height, so distribute the rows over it
        fixrows = [i for i in range(self.rowcount())  if i not in layout.flexrows]
        flexrows = [f for f in layout.flexrows if f < self.rowcount()]
        if my.cellheight() is not None and layout.valign == 'fill':
            if not flexrows:
                raise Exception('Layout is underdetermined: I was told to fill %s vertically, but I do not have any flexrows.' % repr(self.widget))
            if all([c.data.cellheight() is not None for i in fixrows for c in self.row(i)]):
                occ = sum([self.row(i)[0].data.cellheight() for i in fixrows])
                occ += sum([self.row(i)[0].data.cellheight.min for i in flexrows])
                free = my.cellheight() - occ - layout.vspace * (self.rowcount() - 1) - layout.padding_top - layout.padding_bottom
                flexheights = pparti(free.value, [layout.flexrows[r] for r in flexrows])
                for fci, flexheight in zip(flexrows, flexheights):
                    for c in self.row(fci):
                        c.data.cellheight.value = px(flexheight + c.data.cellheight.min)
                            
        # make all cells of a column equal width and all cells of a row equal height
        wmaxt = px(0)
        wmaxg = px(0)
        for i in range(self.colcount()):
            wmax = px(0)
            for c in self.col(i): 
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
        
        if my.width.min == 0:
            my.width.min = my.cellwidth.min
        if my.height.min == 0:
            my.height.min = my.cellheight.min
        my.cellwidth.min = max(my.cellwidth.min, wmaxt + layout.hspace * (self.colcount() - 1) + layout.padding_left + layout.padding_right)
        my.cellheight.min = max(my.cellheight.min, hmaxt + layout.vspace * (self.rowcount() - 1) + layout.padding_top + layout.padding_bottom)
        
        if RWT.MAXIMIZED in self.widget.style:
            self.data.cellhpos.set(layout.padding_left) 
            self.data.cellvpos.set(layout.padding_top)
        # compute the cell positions if we know our width/height 
        # the width/height of all our children
        if my.cellwidth() is not None and all([c[0].data.cellwidth() is not None for c in self.itercols()]):
            cum = layout.padding_left
            for cells in self.itercols():
                for c in cells: 
                    c.data.cellhpos.set(cum)
                cum += c.data.cellwidth() + layout.hspace
        if my.cellheight() is not None and all([c[0].data.cellheight() is not None for c in self.iterrows()]):
            cum = layout.padding_top
            for cells in self.iterrows():
                for c in cells:
                    c.data.cellvpos.set(cum)
                cum += c.data.cellheight() + layout.vspace 
    
        
class RowLayoutAdapter(GridLayoutAdapter): pass
    
class ColumnLayoutAdapter(GridLayoutAdapter): pass 

class CellLayoutAdapter(GridLayoutAdapter):
    
    def __init__(self, widget, parent):
        GridLayoutAdapter.__init__(self, widget, parent)
        if len(widget.children) > 1:
            raise Exception('A cell cannot contain more than one element! (%s, children: %s)' % (repr(widget), map(repr, widget.children)))
    

class TerminalLayoutAdapter(LayoutAdapter): 
    
    def _compute_cells(self, level=0):
        indent = '   ' * level
        my = self.data
        widget = self.widget
        layout = self.layout
#         out(indent, 'computing layout for', widget.id)
        w, h = widget.compute_size()
        my.width.min = max(my.width.min, w)
        my.height.min = max(my.height.min, h)
        my.cellwidth.min = my.width.min + layout.padding_left + layout.padding_right 
        my.cellheight.min = my.height.min + layout.padding_top + layout.padding_bottom 
        


class Layout(object):
    
    PADDING_TOP = px(0)
    PADDING_RIGHT = px(0)
    PADDING_BOTTOM = px(0)
    PADDING_LEFT = px(0)
    H_ALIGN = 'center'
    V_ALIGN = 'center'
    
    def __init__(self, minwidth=None, maxwidth=None, minheight=None, 
                 maxheight=None, valign=None, halign=None, padding_top=None,
                 padding_right=None, padding_bottom=None, padding_left=None,
                 cell_minwidth=None, cell_maxwidth=None, cell_minheight=None,
                 cell_maxheight=None):
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
        self.padding_top = ifnone(padding_top, type(self).PADDING_TOP)
        self.padding_right = ifnone(padding_right, type(self).PADDING_RIGHT)
        self.padding_bottom = ifnone(padding_bottom, type(self).PADDING_BOTTOM)
        self.padding_left = ifnone(padding_left, type(self).PADDING_LEFT)
        

class GridLayout(Layout):
    
#     PADDING_TOP = px(0)
#     PADDING_RIGHT = px(0)
#     PADDING_BOTTOM = px(0)
#     PADDING_LEFT = px(0)
    
    HSPACE = px(10)
    VSPACE = px(10)
    
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
                 padding_left=None, padding_right=None):
        Layout.__init__(self, minwidth=minwidth, maxwidth=maxwidth, minheight=minheight, 
                        maxheight=maxheight, valign=valign, halign=halign,
                        cell_minwidth=cell_minwidth, cell_maxwidth=cell_maxwidth,
                        cell_minheight=cell_minheight, cell_maxheight=cell_maxheight,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right)
        if len([a for a in (cols, rows) if a is not None]) != 1:
            raise LayoutError('You need to specify either the number of rows or the number of cols in a grid layout.')
        if cols is not None:
            self.cols = cols
        elif rows is not None:
            self.rows = rows
        self.flexrows = ifnone(flexrows, {})
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
                 padding_left=None, padding_right=None):
        GridLayout.__init__(self, cols=1, flexcols={0: 1}, flexrows={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, squared=squared,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right)

class RowLayout(GridLayout): 
    
    def __init__(self, flexrows=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalheights=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, vspace=None):
        GridLayout.__init__(self, cols=1, flexrows=flexrows, flexcols={0: 1}, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalheights=equalheights,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right, 
                        vspace=vspace)
        

class ColumnLayout(GridLayout): 
    
    def __init__(self, flexcols=None, minwidth=None, maxwidth=None, minheight=None,
                 maxheight=None, valign=None, halign=None, cell_maxwidth=None, 
                 cell_minheight=None, cell_maxheight=None, cell_minwidth=None,
                 equalwidths=None, padding_top=None, padding_bottom=None,
                 padding_left=None, padding_right=None, hspace=None):
        GridLayout.__init__(self, rows=1, flexrows={0: 1}, flexcols=flexcols, maxwidth=maxwidth,
                        minwidth=minwidth, minheight=minheight, maxheight=maxheight,
                        valign=valign, halign=halign, cell_minwidth=cell_minwidth, 
                        cell_maxwidth=cell_maxwidth, cell_minheight=cell_minheight, 
                        cell_maxheight=cell_maxheight, equalwidths=equalwidths,
                        padding_top=padding_top, padding_bottom=padding_bottom,
                        padding_left=padding_left, padding_right=padding_right,
                        hspace=hspace)
    