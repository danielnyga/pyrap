'''
Created on Oct 9, 2015

@author: nyga
'''

import mimetypes
import os
import time

import re

import dnutils
from dnutils import ifnone, allnone, first
from dnutils.debug import _caller, out
from dnutils.stats import stopwatch, print_stopwatches

from . import locations
from .base import session
from .communication import RWTSetOperation,\
    RWTCreateOperation, RWTCallOperation, RWTDestroyOperation
from .constants import RWT, GCBITS, CURSOR
from .events import OnResize, OnMouseDown, OnMouseUp, OnDblClick, OnFocus, \
    _rwt_mouse_event, OnClose, OnMove, OnSelect, _rwt_selection_event, OnDispose, \
    OnNavigate, OnModify, FocusEventData, _rwt_event, OnFinished, OnLongClick
from .exceptions import WidgetDisposedError
from .layout import Layout, CellLayout, StackLayout, materialize_adapters, ColumnLayout, RowLayout, GridLayout
from .ptypes import px, BitField, BoolVar, NumVar, Color,\
    parse_value, toint, Image
from .themes import LabelTheme, ButtonTheme, CheckboxTheme, OptionTheme, \
    CompositeTheme, ShellTheme, EditTheme, ComboTheme, TabItemTheme, \
    TabFolderTheme, ScrolledCompositeTheme, ScrollBarTheme, GroupTheme, \
    SliderTheme, DropDownTheme, BrowserTheme, ListTheme, MenuTheme, MenuItemTheme, TableItemTheme, TableTheme, \
    TableColumnTheme, CanvasTheme, ScaleTheme, ProgressBarTheme, SpinnerTheme, \
    SeparatorTheme, DecoratorTheme, LinkTheme, SashTheme, ToggleTheme, SashTheme
from .utils import RStorage, BiMap, BitMask
from collections import OrderedDict
import collections


def checkwidget(f, *args):
    def check(self, *args, **kwargs):
        if self.disposed:
            raise WidgetDisposedError('Widget wih ID %s is diposed.' % self.id)
        return f(self, *args, **kwargs)
    return check


def constructor(cls):
    def outer(f):
        def wrapper(self, *args, **kwargs):
            f(self, *args, **kwargs)
            if type(self).__name__ == cls:
                self._create_rwt_widget()
                # append the child to the parent
                if hasattr(self.parent, 'id') and not isinstance(self, Shell):
                    session.runtime << RWTSetOperation(self.parent.id, {'children': [c.id for c in self.parent.children]})
            self._disposed = False
            if type(self).__name__ == cls:
                if hasattr(self, 'create_content'):
                    type(self).create_content(self)
        return wrapper
    return outer


class Widget(object):
    
    _styles_ = BiMap({'visible': RWT.VISIBLE,
                      'border': RWT.BORDER,
                      'enabled': RWT.ENABLED})

    _defstyle_ = BitField(RWT.VISIBLE | RWT.ENABLED)

    class Layer(object):

        def __init__(self, widget):
            self.widget = widget
            self._layer = len(widget.parent.children)

        def __iadd__(self, i):
            if self.widget.parent.children is not None and self.widget in self.widget.parent.children:
                curidx = self.widget.parent.children.index(self.widget)
                self.layer = curidx + i

        def __isub__(self, i):
            if self.widget.parent.children is not None and self.widget in self.widget.parent.children:
                curidx = self.widget.parent.children.index(self.widget)
                self.layer = max(curidx - i, 0)

        @property
        def layer(self):
            return self._layer

        @layer.setter
        def layer(self, layer):
            if self.widget.parent.children is not None and self.widget in self.widget.parent.children:
                self.widget.parent.children.remove(self.widget)
                self.widget.parent.children.insert(layer, self.widget)
                session.runtime << RWTSetOperation(self.widget.parent.id, {'children': [x.id for x in self.widget.parent.children]})

            else:
                raise Exception(self.widget + " is not among its parent's children!")

    def __init__(self, parent, **options):
        self._disposed = True
        self.parent = parent
        self.children = []
        self.layout = Layout()
        self._update_layout_from_dict(options)
        self._zindex = None
        self._css = None
        self._menu = None
        self._layer = Widget.Layer(self)
        self._badge = None
        self._cursor = None
        self._tooltip = None
        self._decorator = None
        if self not in parent.children:
            parent.children.append(self)
        if self not in parent.children:
            self.children.append(self)
        self.id = session.runtime.windows.register(self, parent) 
        self._bounds = (px(0), px(0), px(0), px(0))
        # set up the event listeners
        self.on_resize = OnResize(self)
        self.on_mousedown = OnMouseDown(self)
        self.on_mouseup = OnMouseUp(self)
        self.on_dblclick = OnDblClick(self)
        self.on_navigate = OnNavigate(self)
        self.on_focus = OnFocus(self)
        self.on_dispose = OnDispose()
        self.style = BitField(type(self)._defstyle_)
        for k, v in options.items():
            if k in type(self)._styles_: self.style.setbit(type(self)._styles_[k:], v)
        # save meta information about where in the code the object
        # has been create for better debugging
        self._created = _caller(3)

    def __repr__(self):
        return '<%s id=%s%s at 0x%s>' % (self.__class__.__name__, self.id, '' if not hasattr(self, 'text') else (' text="%s"' % self.text), hash(self))

    def _update_layout_from_dict(self, d):
        if 'minwidth' in d:
            self.layout.minwidth = d['minwidth']
        if 'minheight' in d:
            self.layout.minheight = d['minheight']
        if 'halign' in d:
            self.layout.halign = d['halign']
        if 'valign' in d:
            self.layout.valign = d['valign']
        if 'maxwidth' in d:
            self.layout.maxwidth = d['maxwidth']
        if 'maxheight' in d:
            self.layout.maxheight = d['maxheight']
        if 'cell_minwidth' in d:
            self.layout.cell_minwidth = d['cell_minwidth']
        if 'cell_maxwidth' in d:
            self.layout.cell_maxwidth = d['cell_maxwidth']
        if 'cell_minheight' in d:
            self.layout.cell_minheight = d['cell_minheight']
        if 'cell_maxheight' in d:
            self.layout.cell_maxheight = d['cell_maxheight']
        if 'padding' in d:
            self.layout.padding_left, self.layout.padding_right, \
            self.layout.padding_bottom, self.layout.padding_top = [d['padding']] * 4
        if 'padding_left' in d:
            self.layout.padding_left = d['padding_left']
        if 'padding_right' in d:
            self.layout.padding_right = d['padding_right']
        if 'padding_bottom' in d:
            self.layout.padding_bottom = d['padding_bottom']
        if 'padding_top' in d:
            self.layout.padding_top = d['padding_top']
        
    def _handle_notify(self, op):
        if op.event == 'Resize': self.on_resize.notify()
        elif op.event == 'MouseUp': self.on_mouseup.notify(_rwt_mouse_event(op))
        elif op.event == 'MouseDown':
            if self._menu is None: self.on_mousedown.notify(_rwt_mouse_event(op))
            else:
                self._menu.unhide()
                session.runtime.push.set()
        elif op.event == 'MouseDoubleClick': self.on_dblclick.notify(_rwt_mouse_event(op))
        elif op.event == 'Navigation': self.on_navigate.notify(_rwt_mouse_event(op))
        else: return False
        return True 
        
    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'bounds':
                self._bounds = list(map(px, value))

    def _handle_call(self, op):
        pass
    
    def _rwt_options(self):
        options = RStorage()
        options.style = []
        if RWT.BORDER in self.style:
            options.style.append('BORDER')
        options.enabled = self.enabled
        options.parent = self.parent.id
        return options
    
    @checkwidget
    def dispose(self):
        for c in self.children: c.dispose()
        if self in self.parent.children:
            self.parent.children.remove(self)
        self.on_dispose.notify()
        self._disposed = True
        session.runtime << RWTDestroyOperation(self.id)
        del session.runtime.windows[self]
        
    @property
    def disposed(self):
        return self._disposed
        
    @property
    def bounds(self):
        return self._bounds
    
    @property
    def menu(self):
        return self._menu.id

    @menu.setter
    def menu(self, menu):
        self._menu = menu
        session.runtime << RWTSetOperation(self.id, {'menu': self._menu.id})

    @bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = list(map(px, bounds))
        if self.decorator is not None and not self.decorator.disposed:
            b_ = self.decorator.compute_relpos(self.bounds)
            self.decorator.bounds = b_
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
    
    @property
    def cursor(self):
        return self._cursor
    
    @cursor.setter
    def cursor(self, c):
        self._cursor = c
        session.runtime << RWTSetOperation(self.id, {'cursor': CURSOR.str(c)})
        
    @property
    def tooltip(self):
        return self._tooltip

    @tooltip.setter
    @checkwidget
    def tooltip(self, tooltip):
        self._tooltip = tooltip
        session.runtime << RWTSetOperation(self.id, {'toolTip': self._tooltip})

    @property
    def visible(self):
        return RWT.VISIBLE in self.style
    
    @visible.setter
    @checkwidget
    def visible(self, v):
        self.style.setbit(RWT.VISIBLE, v)
        session.runtime << RWTSetOperation(self.id, {'visibility': RWT.VISIBLE in self.style})
    
    @property
    def enabled(self):
        return RWT.ENABLED in self.style
    
    @enabled.setter
    @checkwidget
    def enabled(self, e):
        self.style.setbit(RWT.ENABLED, e)
        session.runtime << RWTSetOperation(self.id, {'enabled': self.enabled})
    
    @property
    def disabled(self):
        return not self.enabled
    
    @disabled.setter
    def disabled(self, d):
        self.enabled = not d
    
    @property
    def cursor_loc(self):
        ploc = self.parent.cursor_loc
        return px(ploc[0] - self._bounds[0]), px(ploc[1] - self._bounds[1])
    
    @property
    def width(self):
        return self._bounds[2]
    
    @property
    def height(self):
        return self._bounds[3]
    
    @checkwidget
    def focus(self, notify=False):
        session.runtime.windows.focus = self
        if notify:
            self.on_focus.notify(FocusEventData(self.id, True))

    @property
    def focused(self):
        return session.runtime.windows.focus == self
    
    @property
    def bg(self):
        return self.theme.bg
    
    @bg.setter
    @checkwidget
    def bg(self, color):
        self.theme.bg = parse_value(color, Color)
        session.runtime << RWTSetOperation(self.id, {'background': [int(round(v * 255)) for v in [self.theme.bg.red, self.theme.bg.green, self.theme.bg.blue, self.theme.bg.alpha]]})

    @property
    def bgimg(self):
        return self.theme.bgimg
    
    @bgimg.setter
    @checkwidget
    def bgimg(self, img):
        self.theme.bgimg = img
        if img is not None:
            res = session.runtime.mngr.resources.registerc(None, mimetypes.types_map['.%s' % img.fileext], img.content)
            img = [res.location, img.width.value, img.height.value]
        else: img = None
        session.runtime << RWTSetOperation(self.id, {'backgroundImage': img})

    @property
    def color(self):
        return self.theme.color

    @color.setter
    @checkwidget
    def color(self, color):
        self.theme.color = parse_value(color, Color)
        session.runtime << RWTSetOperation(self.id, {'foreground': [int(round(v * 255)) for v in [self.theme.color.red, self.theme.color.green, self.theme.color.blue, self.theme.color.alpha]]})

    @property
    def font(self):
        return self.theme.font

    @font.setter
    @checkwidget
    def font(self, font):
        self.theme._font = font
        session.runtime << RWTSetOperation(self.id, {'font': [font.family, font.size.value, font.bf, font.it]})

    @property
    def css(self):
        return self._css

    @css.setter
    @checkwidget
    def css(self, css):
        self._css = css
        session.runtime << RWTSetOperation(self.id, {'customVariant': 'variant_%s' % css})
        
    @property
    def badge(self):
        return self._badge
    
    @badge.setter
    @checkwidget
    def badge(self, text):
        self._badge = text
        if self._badge is None:
            text = ''
        session.runtime << RWTSetOperation(self.id, {'badge': text})
        
    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(None, img.mimetype, img.content)
            img = [res.location, img.width.value, img.height.value]
        else: img = None
        return img

    def compute_size(self):
        '''
        Compute the dimensions of space that this widget will occupy when displayed
        on the screen.
        
        This method is supposed to compute the `minimal` space that the widget
        will consume, i.e. in case that no ``fill`` is not specified for ``valign``
        and ``halign``.
        
        The default implementation by :class:``pyrap.Widget`` takes into account
        the dimensions resulting from the border, margin and padding specifications
        in the CSS theme.
        '''
        width = height = 0
        # border
        t, r, b, l = self.theme.borders
        width += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        height += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        # padding
        padding = self.theme.padding
        if padding:
            width += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            height += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        # margin
        margin = self.theme.margin
        if margin:
            width += ifnone(margin.left, 0) + ifnone(margin.right, 0)
            height += ifnone(margin.top, 0) + ifnone(margin.bottom, 0)
        return px(width), px(height)

    def shell(self):
        if isinstance(self, Shell):
            return self
        else:
            return self.parent.shell()

    def compute_fringe(self):
        '''
        Computes the fringe of this widget.
        
        The fringe is defined for nonterminal widgets, i.e. widgets that 
        can contain other widgets and denotes the dimensions in x and y 
        directions that are occupied by the parent widget and cannot be
        part of the client area.
        '''
        return px(0), px(0), px(0), px(0)

    @property
    def layer(self):
        return self._layer

    @layer.setter
    @checkwidget
    def layer(self, layer):
        self._layer.layer = layer
        
    @property
    def decorator(self):
        return self._decorator
    
    @decorator.setter
    def decorator(self, d):
        if self._decorator is not None:
            try: self._decorator.dispose()
            except: pass
        if d is None: return
        self._decorator = Decorator(self.parent, **d)
        self._decorator.visible = True
        self._decorator.bounds = self._decorator.compute_relpos(self.bounds)


class Display(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Display'
    
    @constructor('Display')
    def __init__(self, parent):
        Widget.__init__(self, parent)
        self._cursor_loc = (px(0), px(0))

    def _handle_set(self, op):
        for k, v in op.args.items():
            if k not in ('cursorLocation', ): Widget._handle_set(self, op) 
            if k == 'cursorLocation':
                self._cursor_loc = list(map(px, v))
            if k == 'focusControl':
                if v in session.runtime.windows:
                    session.runtime.windows._set_focus(session.runtime.windows[v])
                    session.runtime.windows[v].focus()
    
    def _create_rwt_widget(self):
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_)
        
    @Widget.cursor_loc.getter
    def cursor_loc(self):
        return self._cursor_loc


class Shell(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Shell'
    _styles_ =  Widget._styles_ + {'active':    RWT.ACTIVE,
                                   'maximized': RWT.MAXIMIZED,
                                   'minimized': RWT.MINIMIZED,
                                   'btnclose':  RWT.CLOSE,
                                   'btnmin':    RWT.MINIMIZE,
                                   'btnmax':    RWT.MAXIMIZE,
                                   'resize':    RWT.RESIZE,
                                   'titlebar':  RWT.TITLE,
                                   'modal':     RWT.MODAL}
    _defstyle_ = (Widget._defstyle_ | RWT.ACTIVE | RWT.TITLE | RWT.RESIZE | RWT.MAXIMIZE | RWT.CLOSE | RWT.MINIMIZE) & ~RWT.VISIBLE

    _logger = dnutils.getlogger(__name__, level=dnutils.DEBUG)
    
    @constructor('Shell')
    def __init__(self, **options):
        parent = options.get('parent')
        if parent is None:
            parent = session.runtime.display
        else:
            del options['parent']
        Widget.__init__(self, parent, **options)
        self.theme = ShellTheme(self, session.runtime.mngr.theme)
        self._title = options.get('title')
        self.on_close = OnClose(self)
        self.on_move = OnMove(self)
        self._tabseq = []
        self._packed = False
        if self._title is not None:
            self.style |= RWT.BORDER

    def create_content(self):
        self.content = Composite(self)
        self.content.layout = CellLayout(halign='fill', valign='fill')
        # self.on_resize += self.dolayout

    def _handle_notify(self, op):
        if op.event not in ('Close', 'Move'): return Widget._handle_notify(self, op)
        if op.event == 'Close': self.on_close.notify()
        elif op.event == 'Move': self.on_move.notify()

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'mode':
                if value in ('maximized', 'minimized'):
                    self.style |= {'maximized': RWT.MAXIMIZED, 'minimized': RWT.MINIMIZED}[value]
                else:
                    del self.style[RWT.MINIMIZED | RWT.MAXIMIZED]

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.active = self.active
        if self.maximized:
            options.mode = 'maximized'
        options.visibility = self.visible
        if hasattr(options, 'parent'): del options['parent']
        parentshell = self.parent_shell
        if parentshell is not None:
            options.parentShell = parentshell.id
        if self.title is not None or RWT.TITLE in self.style:
            options.style.append('TITLE')
            options.style.append('BORDER')
            options.text = ifnone(self.title, '')
        if RWT.CLOSE in self.style:
            options.showClose = True
            options.allowClose = True
        options.resizable = (RWT.RESIZE in self.style)
        if RWT.MODAL in self.style:
            options.style.append('APPLICATION_MODAL')
        if RWT.MAXIMIZE in self.style:
            options.showMaximize = True
            options.allowMaximize = True
        if RWT.MINIMIZE in self.style:
            options.showMinimize = True
            options.allowMinimize = True
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
#         if RWT.CLOSE in self.style:
        self.on_close += self.dispose
        
    @property
    def tabseq(self):
        return self._tabseq
    
    @tabseq.setter
    @checkwidget
    def tabseq(self, widgets):
        self._tabseq = widgets
        for i, w in enumerate(widgets):
            session.runtime << RWTSetOperation(w.id, {'tabIndex': (i+1)})

    @property
    def title(self):
        return self._title
    
    @title.setter
    @checkwidget
    def title(self, t):
        self._title = t
        session.runtime << RWTSetOperation(self.id, {'text': self._title})
        
    @property
    def active(self):
        return RWT.ACTIVE in self.style
    
    @active.setter
    @checkwidget
    def active(self, a):
        self.style |= RWT.ACTIVE
    
    @property
    def maximized(self):
        return RWT.MAXIMIZED in self.style
    
    @maximized.setter
    @checkwidget
    def maximized(self, m):
        self.style.setbit(RWT.MAXIMIZED, m)
        session.runtime << RWTSetOperation(self.id, {'mode': 'maximized'})

    @property
    def parent_shell(self):
        p = self.parent
        while True:
            if isinstance(p, Shell): return p
            if not hasattr(p, 'parent'): return None
            p = p.parent

    @property
    def client_rect(self):
        t, r, b, l = self.compute_fringe()
        _, _, w, h = self.bounds
        return l, t, w - l - r, h - t - b

    @checkwidget
    def close(self):
        self.on_close.notify()

    def show(self, pack=False):
        self.visible = True
        self.dolayout(pack)

    def dolayout(self, pack=False):
        if pack is None:
            pack = self._packed
        else:
            self._packed = pack
        with stopwatch('/pyrap/layout'):
            # materialize the layout tree
            adapter = materialize_adapters(self)
            if not pack or self.maximized:
                adapter.hpos, adapter.vpos, adapter.width, adapter.height = self.client_rect
            else:
                adapter.hpos, adapter.vpos, adapter.width, adapter.height = None, None, None, None
            adapter.run()
            if pack and not self.maximized:
                adapter.hpos, adapter.vpos, _, _ = self.client_rect
                adapter.width, adapter.height = adapter.preferred_size()
                t, r, b, l = self.compute_fringe()
                w = max(adapter.width + l + r, ifnone(self.layout.minwidth, 0))
                h = max(adapter.height + t + b, ifnone(self.layout.minheight, 0))
                adapter.widget.bounds = adapter.hpos + adapter.layout.padding_left, \
                                        adapter.vpos + adapter.layout.padding_top, \
                                        adapter.width - adapter.layout.padding_left - adapter.layout.padding_right, \
                                        adapter.height - adapter.layout.padding_top - adapter.layout.padding_bottom
                _, _, dispw, disph = session.runtime.display.bounds
                xpos = int(round(dispw.value / 2. - w / 2.))
                ypos = int(round(disph.value / 2. - h / 2.))
                self.bounds = xpos, ypos, w, h
                if not allnone((self.layout.minwidth, self.layout.minheight)):
                    self.dolayout()

    def onresize_shell(self):
        self.dolayout()
        
    def compute_fringe(self):
        top, right, bottom, left = 0, 0, 0, 0
        padding = self.theme.padding
        if padding:
            left += padding.left
            right += padding.right
            bottom += padding.top
            top += padding.top
        if self.title is not None or RWT.TITLE in self.style:
            top += self.theme.title_height
        return top, right, bottom, left


class Combo(Widget):

    _rwt_class_name_ = 'rwt.widgets.Combo'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Combo')
    def __init__(self, parent, items=None, editable=True, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ComboTheme(self, session.runtime.mngr.theme)
        self._items = []
        self._editable = editable
        self._setitems(ifnone(items, []))
        self._text = None
        self.on_select = OnSelect(self)
        self.on_modify = OnModify(self)
        self._selidx = -1

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.items = list(map(str, self._items))
        options.style.append("DROP_DOWN")
        options.editable = self._editable
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX', self.shell())
        for padding in (self.theme.padding, self.theme.itempadding):
            if padding:
                w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
                h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        w += ifnone(self.theme.btnwidth, 0)
        return w, h

    def _setitems(self, items):
        if self._editable:
            if isinstance(items, list):
                self._items = items
            else:
                raise TypeError('Items must be of type list in editable combo!')
        else:
            if items is None:
                items = []
            if isinstance(items, dict):
                if not all([type(i) is str for i in items]):
                    raise TypeError('All keys in an item dictionary must be strings.')
                else:
                    self._items = OrderedDict(((k, items[k]) for k in sorted(items)))
            elif type(items) in (list, tuple):
                items = OrderedDict(((str(i), i) for i in items))
            else: raise TypeError('Invalid type for List items: %s' % type(items))
            self._items = items

    def additems(self, items):
        if self._editable:
            if isinstance(items, list):
                self.items.extend(items)
            else:
                raise TypeError('Items must be of type list in editable combo!')
        else:
            if isinstance(items, dict):
                if not all([type(i) is str for i in items]):
                    raise TypeError('All keys in an item dictionary must be strings.')
                else:
                    _items = dict(self._items)
                    _items.update(items)
                    self.items = _items
            elif type(items) in (list, tuple):
                _items = dict(self._items)
                _items.update({k: k for k in items})
                self.items = _items
            else:
                raise TypeError('Invalid type for dictionary items: %s' % type(items))

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'selectionIndex':
                self._selidx = value
            if key == 'text':
                self._text = value

    def _handle_notify(self, op):
        events = {'Selection': self.on_select, 'Modify': self.on_modify}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        elif op.event == 'Selection':
            events[op.event].notify(_rwt_selection_event(op))
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    def showlist(self, show):
        session.runtime << RWTCallOperation(self.id, 'showList', show)

    @property
    def text(self):
        return self._text

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    @property
    def selection(self):
        if self._editable:
            return self.items[self._selidx]
        else:
            return self.items[list(self.items.keys())[self._selidx]]

    @selection.setter
    def selection(self, sel):
        if self._editable:
            self._selidx = self._items.index(sel) if sel is not None else None
            txt = self._items[self._selidx]
        else:
            self._selidx = list(self._items.keys()).index(sel) if sel is not None else None
            txt = list(self._items.keys())[self._selidx]
        self._text = txt
        session.runtime << RWTSetOperation(self.id, {'selectionIndex': self._selidx, 'text': txt})

    @property
    def selidx(self):
        return self._selidx

    @selidx.setter
    def selidx(self, idx):
        self._selidx = idx
        if self._editable:
            txt = self._items[self._selidx]
        else:
            txt = self._items.values()[self._selidx]
        session.runtime << RWTSetOperation(self.id, {'selectionIndex': self._selidx, 'text': txt})

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self._setitems(items)
        if self._editable:
            items = self.items
        else:
            # cast to list as dict_keys object is not jsonifiable
            items = list(self.items.keys())
        session.runtime << RWTSetOperation(self.id, {'items': items})


class DropDown(Widget):

    _rwt_class_name_ = 'rwt.widgets.DropDown'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('DropDown')
    def __init__(self, parent, items='', markupEnabled=True, visible=False, visibleItemCount=5, **options):
        Widget.__init__(self, parent, **options)
        self.theme = DropDownTheme(self, session.runtime.mngr.theme)
        self._items = items
        self._markupEnabled = markupEnabled
        self.on_select = OnSelect(self)
        self._visibleitemcount = visibleItemCount
        self._visible = visible
        self._selidx = -1
        if self in parent.children:
            parent.children.remove(self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.items = self._items
        options.markupEnabled = self._markupEnabled
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def compute_size(self):
        w, h = 0,0
        for padding in (self.theme.padding, self.theme.itempadding):
            if padding:
                w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
                h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h

    @property
    def items(self):
        return self._items

    @items.setter
    @checkwidget
    def items(self, items):
        self._items = items
        session.runtime << RWTSetOperation(self.id, {'items': self.items})

    @property
    def visibleitemcount(self):
        return self._visibleitemcount

    @visibleitemcount.setter
    @checkwidget
    def visibleitemcount(self, visibleitemcount):
        self._visibleitemcount = visibleitemcount
        session.runtime << RWTSetOperation(self.id, {'visibleItemCount': self.visibleitemcount})

    @property
    def visible(self):
        return self._visible

    @visible.setter
    @checkwidget
    def visible(self, visible):
        self._visible = visible
        session.runtime << RWTSetOperation(self.id, {'visible': self.visible})

    @property
    def selected(self):
        return self.items[self._selidx]

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'selectionIndex':
                self._selidx = value

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True


class Label(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Label'
    _styles_ = Widget._styles_ + {'markup': RWT.MARKUP,
                                  'wrap': RWT.WRAP}
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Label')
    def __init__(self, parent, text='', img=None, textalign='left', **options):
        Widget.__init__(self, parent, **options)
        self.theme = LabelTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._img = img
        self._textalign = textalign

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.img: 
            options.image = self._get_rwt_img(self.img)
        else:
            options.text = self.text
        options.alignment = self._textalign
        if RWT.MARKUP in self.style:
            options.markupEnabled = True
            options.customVariant = 'variant_markup'
        if RWT.WRAP in self.style:
            options.style.append('WRAP')
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    @property
    def textalign(self):
        return self._textalign

    @textalign.setter
    @checkwidget
    def textalign(self, align):
        if align not in ('left', 'right', 'center'):
            raise ValueError('Illegal text alignment: %s' % align)
        self._textalign = align
        session.runtime << RWTSetOperation(self.id, {'alignment': self._textalign})

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(None, img.mimetype, img.content)
            img = [res.location, img.width.value, img.height.value]
        else: img = None
        return img

    @property
    def img(self):
        return self._img

    @property
    def text(self):
        return self._text

    @property
    def color(self):
        return self._color

    @color.setter
    @checkwidget
    def color(self, color):
        self._color = color
        session.runtime << RWTSetOperation(self.id, {'foreground': [int(round(255 * self.color.red)),
                                                                    int(round(255 * self.color.green)),
                                                                    int(round(255 * self.color.blue)),
                                                                    int(round(255 * self.color.alpha))]})

    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {'image': self._get_rwt_img(self.img)})


    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})
        
    def compute_size(self):
        w, h = 0, 0
        if self.img is not None:
            w, h = self.img.size
        elif RWT.WRAP not in self.style:
            lines = self._text.split('\n' if RWT.MARKUP not in self.style else '<br>')
            w += max([session.runtime.textsize_estimate(self.theme.font, l, self.shell())[0] for l in lines])
            _, h = session.runtime.textsize_estimate(self.theme.font, 'X', self.shell())
            h *= len(lines)
        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h


class Link(Widget):
    _rwt_class_name_ = 'rwt.widgets.Link'
    _styles_ = Widget._styles_ + {'wrap': RWT.WRAP}
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Link')
    def __init__(self, parent, text='', img=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = LinkTheme(self, session.runtime.mngr.theme)
        self.on_select = OnSelect(self)
        self._origtext = text
        self._img = img
        self._txtids = []
        self._links = []
        self._parse(text)
        self._displaytext = ''.join([x[0] for x in self._txtids])

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = self._txtids
        options.style.append('NONE')
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        # if the user has specified a href in any of the link tags of the text,
        # we will try to open it (either in he given target, or in _blank.
        # For any other link tags, the user has to specify their own listener
        # function. Note that the user can differ which of the link tags has
        # been clicked by the index value in the args of the event that has
        # been triggered (see open()).
        if any([l.get('href', None) is not None for l in self._links]):
            self.on_select += self._open

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(None, img.mimetype, img.content)
            img = [res.location, img.width.value, img.height.value]
        else:
            img = None
        return img

    def _parse(self, text):
        sidx = 0
        for i, x in enumerate(re.finditer('(<a(\s*href=(?:\"|\')(?P<href>.*?)(?:\'|\"))?(\s*target=(?:\"|\')(?P<target>.*)(?:\"|\'))?>(?P<txt>.*?)</a>)', text)):
            self._txtids.append([text[sidx:x.start()], None])
            self._txtids.append([x.groupdict().get('txt'), i])
            self._links.append(x.groupdict())
            sidx = x.end()
        self._txtids.append([text[sidx:], None])

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'selectionIndex':
                self._selidx = value

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    def _open(self, ev):
        lset = self._links[ev.args[0].get('index')]
        if lset.get('href') is not None:
            session.runtime.executejs('window.open("{}", "{}");'.format(ifnone(lset.get('href'), ''), ifnone(lset.get('target'), '_blank')))

    @property
    def img(self):
        return self._img

    @property
    def text(self):
        return self._text

    @property
    def color(self):
        return self._color

    @color.setter
    @checkwidget
    def color(self, color):
        self._color = color
        session.runtime << RWTSetOperation(self.id, {
            'foreground': [int(round(255 * self.color.red)),
                           int(round(255 * self.color.green)),
                           int(round(255 * self.color.blue)),
                           int(round(255 * self.color.alpha))]})

    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {
            'image': self._get_rwt_img(self.img)})

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    def compute_size(self):
        if self.img is not None:
            w, h = self.img.size
        else:
            lines = self._displaytext.split('\n')
            w = max(
                [session.runtime.textsize_estimate(self.theme.font, l, self.shell())[0] for l
                 in lines])
            _, h = session.runtime.textsize_estimate(self.theme.font, 'X', self.shell())
            h *= len(lines)
        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h


class Separator(Widget):
    _rwt_class_name_ = 'rwt.widgets.Separator'
    _styles_ = Widget._styles_ + {'vertical': RWT.VERTICAL, 
                                'horizontal': RWT.HORIZONTAL}
    _defstyle_ = BitField(Widget._defstyle_) | RWT.SEPARATOR
    
    @constructor('Separator')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = SeparatorTheme(self, session.runtime.mngr.theme)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.SEPARATOR in self.style:
            options.style.append('SEPARATOR')
        if RWT.HORIZONTAL in self.style:
            options.style.append('HORIZONTAL')
        elif RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)


    def compute_size(self):
        line = self.theme.linewidth
        if RWT.HORIZONTAL in self.style:
            return 0, line
        else: return line, 0
        
        
class Button(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Button'
    _styles_ = Widget._styles_ + {'markup': RWT.MARKUP}
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Button')
    def __init__(self, parent, text='', img=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ButtonTheme(self, session.runtime.mngr.theme)
        self.on_select = OnSelect(self)
        self.on_long_click = OnLongClick(self)
        self._text = text
        self._img = img
        self.compute_textsize = True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.img:
            options.image = self._get_rwt_img(self.img)
        options.text = self.text
        options.style.append('PUSH')
        options.tabIndex = 1
        if RWT.MARKUP in self.style:
            options.markupEnabled = True
            options.customVariant = 'variant_markup'
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(None, img.mimetype, img.content)
            img = [res.location, img.width.value, img.height.value]
        else: img = None
        return img

    @property
    def img(self):
        return self._img

    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {'image': self._get_rwt_img(self.img)})

    @property
    def text(self):
        return self._text
    
    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_select, 'LongClick': self.on_long_click}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True 
    
    def compute_size(self):
        width, height = Widget.compute_size(self)
        if self.compute_textsize:
            tw, th = session.runtime.textsize_estimate(self.theme.font, self._text.replace('\n', '<br>'), self.shell())
        else:
            tw, th = 0, 0
        width += tw
        height += th
        if self.img is not None:
            w, h = self.img.size
            width += w
            height += (h - px(h)) if (h > px(h)) else 0
        return width, height
    
    
class Checkbox(Widget):
    _rwt_class_name_ = 'rwt.widgets.Button'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Checkbox')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = CheckboxTheme(self, session.runtime.mngr.theme)
        self.on_checked = OnSelect(self)
        self._text = text
        self._checked = BoolVar(value=options.get('checked'))
        self._checked.on_change += lambda *x: self._rwt_set_checkmark()
        self._boundvars = []

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = self._text
        options.style.append('CHECK')
        options.style.append('LEFT')
        options.tabIndex = 1
        if self.checked is not None:
            options.selection = self.checked
        options.grayed = True if (self.checked is None) else False
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        self.on_checked += lambda *_: True

    def bind(self, var):
        if not type(var) in (NumVar, BoolVar):
            raise Exception('Can only bind variables of type NumVar and BoolVar')
        self._checked.bind(var)
        self._boundvars.append(var)

    @property
    def checked(self):
        return self._checked()
    
    @checked.setter
    def checked(self, c):
        self._checked.set(c)

    @checkwidget        
    def _rwt_set_checkmark(self):
        options = RStorage()
        if self.checked is not None:
            options.selection = self.checked
        options.grayed = True if (self.checked is None) else False
        session.runtime << RWTSetOperation(self.id, options)
        
    @property
    def text(self):
        return self._text
    
    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    def dispose(self):
        for v in self._boundvars:
            # make sure bound variable will not try to notify disposed widget
            v.unbind()
        Widget.dispose(self)
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_checked}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True 

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._checked.set(value)
    
    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        textheight = px(h) 
        for padding in (self.theme.padding, self.theme.fipadding):
            if padding:
                w += self.theme.padding.left + self.theme.padding.right
                h += self.theme.padding.top + self.theme.padding.bottom
        for t, r, b, l in(self.theme.borders, self.theme.fiborders): 
            w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
            h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        w += self.theme.icon.width.value
        h += (self.theme.icon.height.value - textheight) if (self.theme.icon.height.value > textheight) else 0
        w += self.theme.spacing
        return w, h


class Toggle(Checkbox, Button):
    _rwt_class_name_ = 'rwt.widgets.Button'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Toggle')
    def __init__(self, parent, text='', texts=None, **options):
        Button.__init__(self, parent, text=text, **options)
        Checkbox.__init__(self, parent, text=text, **options)
        self.theme = ToggleTheme(self, session.runtime.mngr.theme)
        self._texts = texts

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = self._text
        options.style.append('TOGGLE')
        # options.style.append('LEFT')
        options.tabIndex = 1
        if self.checked is not None:
            options.selection = self.checked
        options.grayed = True if (self.checked is None) else False
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        self._update_text()
        if self._texts:
            self.on_checked += self._update_text

    @property
    def texts(self, txts):
        if len(txts) != 2:
            raise ValueError('attribute must be tuple of length 2')
        self._texts = txts
        self._update_text()

    def _update_text(self, *_):
        if self._texts:
            checked = 1 if self.checked else 0
            self.text = self._texts[checked]

    @checkwidget
    def _rwt_set_checkmark(self):
        Checkbox._rwt_set_checkmark(self)
        self._update_text()

    def compute_size(self):
        return Button.compute_size(self)


class Option(Widget):
    _rwt_class_name_ = 'rwt.widgets.Button'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Option')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = OptionTheme(self, session.runtime.mngr.theme)    
        self.on_checked = OnSelect(self)
        self._text = str(text()) if isinstance(text, collections.Callable) else str(text)
        self._checked = BoolVar(options.get('checked', False))

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = str(self._text()) if isinstance(self._text, collections.Callable) else str(self._text)
        options.style.append('RADIO')
        options.tabIndex = 1
        options.selection = self.checked()
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def bind(self, b):
        self._checked.bind(b)

    @property
    def checked(self):
        return self._checked
    
    @checked.setter
    @checkwidget
    def checked(self, c):
        self._checked.set(c)
        session.runtime << RWTSetOperation(self.id, {'selection': self._checked()})
        
    @property
    def text(self):
        return self._text
    
    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_checked}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_event(op))
        return True 

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._checked.set(value)

    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        textheight = px(h) 
        for padding in (self.theme.padding, self.theme.fipadding):
            if padding:
                w += self.theme.padding.left + self.theme.padding.right
                h += self.theme.padding.top + self.theme.padding.bottom
        for t, r, b, l in(self.theme.borders, self.theme.fiborders): 
            w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
            h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        w += self.theme.icon.width.value
        h += (self.theme.icon.height.value - textheight) if (self.theme.icon.height.value > textheight) else 0
        w += self.theme.spacing
        return w, h
    
    
class Edit(Widget):
    
    _rwt_class_name = 'rwt.widgets.Text'
    _styles_ = Widget._styles_ + {'multiline': RWT.MULTI,
                                  'wrap': RWT.WRAP,
                                  'alignleft': RWT.LEFT,
                                  'password': RWT.PASSWORD}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.BORDER | RWT.LEFT)

    @constructor('Edit')
    def __init__(self, parent, text=None, editable=True, message=None, search=False, **options):
        Widget.__init__(self, parent, **options)
        self.theme = EditTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._message = message
        self._editable = editable
        self._selection = None
        self._search = search
        self.on_modify = OnModify(self)
        
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.text:
            options.text = self.text
        if self._message:
            options.message = self._message
        if self._search:
            options.style.append('SEARCH')
        options.editable = self._editable
        if RWT.MULTI in self.style:
            options.style.append('MULTI')
        if RWT.WRAP in self.style:
            options.style.append('WRAP')
        if RWT.LEFT in self.style:
            options.style.append('LEFT')
        if RWT.PASSWORD in self.style:
            options.style.append('PASSWORD')
            options.echoChar = '?'
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        width, height = Widget.compute_size(self)
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX', self.shell())
        width += w
        height += h
        return width, height

    @property
    def text(self):
        return self._text

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': text})

    @property
    def message(self):
        return self._message

    @message.setter
    @checkwidget
    def message(self, message):
        self._message = message
        session.runtime << RWTSetOperation(self.id, {'message': message})

    def _handle_notify(self, op):
        events = {'Modify': self.on_modify}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_event(op))
        return True 

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._selection = value
            if key == 'text':
                self._text = value


class Composite(Widget):
    '''A generic container that holds other widgets.'''

    _styles_ = Widget._styles_ + BiMap({})
    _rwt_class_name_ = 'rwt.widgets.Composite'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Composite')
    def __init__(self, parent, layout=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = CompositeTheme(self, session.runtime.mngr.theme)
        if layout is not None:
            self.layout = layout

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
        
    @Widget.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = list(map(px, bounds))
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        session.runtime << RWTSetOperation(self.id, {'clientArea': map(int, self.client_rect)})
        
    def compute_size(self):
        return Widget.compute_size(self)

    @property
    def client_rect(self):
        t, r, b, l = self.compute_fringe()
        _, _, w, h = self.bounds
        return l, t, w - l - r, h - t - b


class Cols(Composite):
    '''A composite only consisting of horizontally queued widgets.'''

    @constructor
    def __init__(self, parent, **options):
        Composite.__init__(self, parent, **options)
        self.layout = ColumnLayout(minwidth=options.get('minwidth'),
                                   maxwidth=options.get('maxwidth'),
                                   minheight=options.get('minheight'),
                                   maxheight=options.get('maxheight'),
                                   valign=options.get('valign'),
                                   halign=options.get('halign'),
                                   cell_minwidth=options.get('cell_minwidth'),
                                   cell_maxwidth=options.get('cell_maxwidth'),
                                   cell_minheight=options.get('cell_minheight'),
                                   cell_maxheight=options.get('cell_maxheight'),
                                   padding_top=options.get('padding_top'),
                                   padding_bottom=options.get('padding_bottom'),
                                   padding_left=options.get('padding_left'),
                                   padding_right=options.get('padding_right'),
                                   padding=options.get('padding'),
                                   hspace=options.get('hspace'),
                                   equalwidths=options.get('equalwidths'))


class Rows(Composite):
    '''A composite only consisting of vertically queued widgets.'''

    @constructor
    def __init__(self, parent, **options):
        Composite.__init__(self, parent, **options)
        self.layout = RowLayout(minwidth=options.get('minwidth'),
                                maxwidth=options.get('maxwidth'),
                                minheight=options.get('minheight'),
                                maxheight=options.get('maxheight'),
                                valign=options.get('valign'),
                                halign=options.get('halign'),
                                cell_minwidth=options.get('cell_minwidth'),
                                cell_maxwidth=options.get('cell_maxwidth'),
                                cell_minheight=options.get('cell_minheight'),
                                cell_maxheight=options.get('cell_maxheight'),
                                padding_top=options.get('padding_top'),
                                padding_bottom=options.get('padding_bottom'),
                                padding_left=options.get('padding_left'),
                                padding_right=options.get('padding_right'),
                                padding=options.get('padding'),
                                vspace=options.get('vspace'),
                                equalheights=options.get('equalheights'))


class Grid(Composite):
    '''A composite that arragnes its children in a grid.'''

    @constructor
    def __init__(self, parent, **options):
        Composite.__init__(self, parent, cols=None, rows=None, **options)
        self.layout = GridLayout(cols=options.get('cols'),
                                 rows=options.get('rows'),
                                 minwidth=options.get('minwidth'),
                                 maxwidth=options.get('maxwidth'),
                                 minheight=options.get('minheight'),
                                 maxheight=options.get('maxheight'),
                                 valign=options.get('valign'),
                                 halign=options.get('halign'),
                                 cell_minwidth=options.get('cell_minwidth'),
                                 cell_maxwidth=options.get('cell_maxwidth'),
                                 cell_minheight=options.get('cell_minheight'),
                                 cell_maxheight=options.get('cell_maxheight'),
                                 padding_top=options.get('padding_top'),
                                 padding_bottom=options.get('padding_bottom'),
                                 padding_left=options.get('padding_left'),
                                 padding_right=options.get('padding_right'),
                                 padding=options.get('padding'),
                                 hspace=options.get('hspace'),
                                 vspace=options.get('vspace'))


class StackedComposite(Composite):
    '''
    A composite that stacks its elements in z direction.
    '''
    @constructor('StackedComposite')
    def __init__(self, parent, **options):
        Composite.__init__(self, parent, **options)
        self.layout = StackLayout(minwidth=options.get('minwidth'), 
                                  maxwidth=options.get('maxwidth'), 
                                  minheight=options.get('minheight'), 
                                  maxheight=options.get('maxheight'), 
                                  valign=options.get('valign'), 
                                  halign=options.get('halign'), 
                                  cell_minwidth=options.get('cell_minwidth'), 
                                  cell_maxwidth=options.get('cell_maxwidth'), 
                                  cell_minheight=options.get('cell_minheight'), 
                                  cell_maxheight=options.get('cell_maxheight'), 
                                  padding_top=options.get('padding_top'), 
                                  padding_bottom=options.get('padding_bottom'), 
                                  padding_left=options.get('padding_left'), 
                                  padding_right=options.get('padding_right'), 
                                  padding=options.get('padding'))
        self._selection = None
        
    @property
    def selection(self):
        return self._selection
    
    @selection.setter
    def selection(self, c):
        if type(c) is int:
            c = self.children[c]
        self._selection = c
        for c_ in self.children:
            c_.visible = c_ is self._selection
    
    @property
    def selidx(self):
        return self.children.index(self.selection)
    
    @selidx.setter
    @checkwidget
    def selidx(self, i):
        self.selection = i
        
    
class ScrolledComposite(Composite):

    _rwt_class_name_ = 'rwt.widgets.ScrolledComposite'
    
    _styles_ = Composite._styles_ + BiMap({'hscroll': RWT.HSCROLL,
                                           'vscroll': RWT.VSCROLL})

    @constructor('ScrolledComposite')
    def __init__(self, parent,**options):
        Composite.__init__(self, parent, **options)
        self.theme = ScrolledCompositeTheme(self, session.runtime.mngr.theme)
        self._content = None
        self.layout = CellLayout(exceed='truncate', halign=self.layout.halign, valign=self.layout.valign,
                                 minwidth=self.layout.minwidth, minheight=self.layout.minheight,
                                 cell_minwidth=self.layout.cell_minwidth, cell_minheight=self.layout.cell_minheight)
        self._hbar, self._vbar = None, None
        
    def create_content(self):
        if RWT.HSCROLL in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
        if RWT.VSCROLL in self.style:
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True
        self.content = Composite(self, layout=CellLayout())

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.HSCROLL in self.style:
            options.style.append('H_SCROLL')
        if RWT.VSCROLL in self.style:
            options.style.append('V_SCROLL')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
        self.pos = (0, 0)

    @property
    def pos(self):
        raise Exception('You cannot retrieve the current scroll position')
        
    @pos.setter
    def pos(self, p):
        session.runtime << RWTSetOperation(self.id, {'origin': p})

    @property
    def hbar(self):
        return self._hbar
    
    @property
    def vbar(self):
        return self._vbar

    @property
    def content(self):
        return self._content

    @content.setter
    @checkwidget
    def content(self, content):
        self._content = content
        session.runtime << RWTSetOperation(self.id, {'content': content.id})

    def compute_size(self):
        width, height = Widget.compute_size(self)
        if RWT.HSCROLL in self.style:
            width += self._hbar.theme.minheight
            height += self._hbar.theme.width
        if RWT.VSCROLL in self.style:
            height += self._vbar.theme.minheight
            width += self._vbar.theme.width
        return width, height

class ScrollBar(Widget):

    _rwt_class_name_ = 'rwt.widgets.ScrollBar'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('ScrollBar')
    def __init__(self, parent, orientation=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ScrollBarTheme(self, session.runtime.mngr.theme)
        self.orientation = orientation
        if self in parent.children:
            parent.children.remove(self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.orientation == RWT.HORIZONTAL:
            options.style.append('HORIZONTAL')
        elif self.orientation == RWT.VERTICAL:
            options.style.append('VERTICAL')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)


class TabFolder(Composite):

    _rwt_class_name_ = 'rwt.widgets.TabFolder'
    _defstyle_ = BitField(Composite._defstyle_ | RWT.TOP)
    _styles_ = Composite._styles_ + {'tabpos': RWT.TOP}

    @constructor('TabFolder')
    def __init__(self, parent, tabpos='top', **options):
        Widget.__init__(self, parent, **options)
        self.theme = TabFolderTheme(self, session.runtime.mngr.theme)
        if tabpos == 'top':
            self.style |= RWT.TOP
        elif tabpos != 'bottom':
            raise ValueError('illegal parameter value for tabpos: %s' % tabpos)
        else:
            del self.style[RWT.TOP]
        self._items = []
        self.on_select = OnSelect(self)
        self._selected = None
        self.layout = StackLayout(halign=self.layout.halign, 
                                  valign=self.layout.valign,
                                  minwidth=self.layout.minwidth,
                                  minheight=self.layout.minheight,
                                  cell_minwidth=self.layout.cell_minwidth,
                                  cell_minheight=self.layout.cell_minheight,
                                  padding_top=self.layout.padding_top,
                                  padding_right=self.layout.padding_right,
                                  padding_bottom=self.layout.padding_bottom,
                                  padding_left=self.layout.padding_left)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.TOP in self.style:
            options.style.append('TOP')
        else:
            options.style.append('BOTTOM')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
        self.on_select += self._select

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True

    @checkwidget
    def addtab(self, title='', img=None, idx=None):
        item = TabItem(self, idx=ifnone(idx, len(self.items)), text=title)
        container = Composite(self)
        container.layout = CellLayout(halign='fill', valign='fill')
        item.control = container
        self.items.append(item)
        return item

    @property
    def items(self):
        return self._items

    def rmitem(self, idx):
        self.items.pop(idx).dispose()

    def _select(self, args):
        self.selected = session.runtime.windows[args.item]

    @property
    def selected(self):
        return self._selected

    @selected.setter
    @checkwidget
    def selected(self, item):
        if type(item) is int:
            item = self.items[item]
        if not isinstance(item, TabItem): raise TypeError('Expected type %s, got %s.' % (TabItem.__name__, type(item).__name__))
        self._selected = item
        for i in self.items:
            i.selected = 0
        item.selected = 1
        session.runtime << RWTSetOperation(self.id, {'selection': self._selected.id})

    def compute_size(self):
        width, height = Composite.compute_size(self)
        t, r, b, l = self.compute_fringe()
        width += l + r
        height += t + b
        width += sum([i.compute_size()[0] for i in self.items])
        # content container border
        return width, height

    def compute_fringe(self):
        top, right, bottom, left = 0, 0, 0, 0
        t, r, b, l = self.theme.container_borders
        top += ifnone(t, 0, lambda b: b.width)
        right += ifnone(r, 0, lambda b: b.width)
        bottom += ifnone(b, 0, lambda b: b.width)
        left += ifnone(l, 0, lambda b: b.width)
        itemsizes = [i.compute_size() for i in self.items]
        if itemsizes:
            height = max([s[1] for s in itemsizes])
            if RWT.TOP in self.style:
                top += height
            else:
                bottom += height
        return top, right, bottom, left
    

class TabItem(Widget):

    _rwt_class_name_ = 'rwt.widgets.TabItem'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('TabItem')
    def __init__(self, parent, idx=0, text=None, img=None, tooltip=None, control=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TabItemTheme(self, session.runtime.mngr.theme)
        self._idx = idx
        self._text = text
        self._tooltip = tooltip
        self._img = img
        self._control = control
        if self in parent.children:
            parent.children.remove(self)
        self.parent.items.insert(idx, self)
        self.selected = False


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.img:
            options.image = self._get_rwt_img(self.img)
        if self.text:
            options.text = self.text
        if self.tooltip:
            options.toolTip = self.tooltip
        if self._control:
            options.control = self._control.id
        if 'style' in options:
            del options['style']
        if 'enabled' in options:
            del options['enabled']
        options.id = self.id
        options.index = self.idx
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width, img.height]
        else:
            img = None
        return img

    @Widget.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = list(map(px, bounds))
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        # session.runtime << RWTSetOperation(self.id, {'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})

    @property
    def idx(self):
        return self._idx

    @idx.setter
    @checkwidget
    def idx(self, idx):
        self._idx = idx
        session.runtime << RWTSetOperation(self.id, {'index': self._idx})

    @property
    def text(self):
        return self._text

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    @property
    def tooltip(self):
        return self._tooltip

    @tooltip.setter
    @checkwidget
    def tooltip(self, tooltip):
        self._tooltip = tooltip
        session.runtime << RWTSetOperation(self.id, {'toolTip': self._tooltip})

    @property
    def img(self):
        return self._img

    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {'image': self._get_rwt_img(self.img)})

    @property
    def content(self):
        return self._control

    @property
    def control(self):
        return self._control

    @control.setter
    @checkwidget
    def control(self, control):
        self._control = control
        session.runtime << RWTSetOperation(self.id, {'control': control.id})

    def compute_size(self):
        width, height = Widget.compute_size(self)
        if self.img is not None:
            w, h = self.img.size
        else:
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        width += w
        height += h
        return width, height


class Scale(Widget):
    _rwt_class_name_ = 'rwt.widgets.Scale'
    _styles_ = Widget._styles_ + {}
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('Scale')
    def __init__(self, parent, inc=None, pageinc=None, orientation=RWT.HORIZONTAL, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ScaleTheme(self, session.runtime.mngr.theme)
        self.style |= orientation
        self._minimum = None
        self._maximum = None
        self._selection = None
        self._inc = inc
        self._pageinc = pageinc
        self.on_select = OnSelect(self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        line_resource_name = 'resource/widget/rap/scale/h_line.gif'
        if RWT.HORIZONTAL in self.style:
            options.style.append('HORIZONTAL')
        elif RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
            line_resource_name = 'resource/widget/rap/scale/v_line.gif'
        if self.minimum:
            options.minimum = self._minimum
        if self.maximum:
            options.maximum = self._maximum
        if self.selection:
            options.selection = self._selection
        if self.inc:
            options.pageIncrement = self._increment
        # for some reason the line of the scale is not directly themable
        # via CSS, so we fake a CSS class "Scale-Line" that holds the line image
        # and make it available under a constant resource name
        line = self.theme.lineimg
        session.runtime.mngr.resources.registerc(line_resource_name, line.mimetype, line.content)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._selection = value

    @property
    def selection(self):
        return self._selection

    @selection.setter
    @checkwidget
    def selection(self, selection):
        self._selection = selection
        session.runtime << RWTSetOperation(self.id, {'selection': self.selection})

    @property
    def pageinc(self):
        return self._pageinc

    @pageinc.setter
    @checkwidget
    def pageinc(self, inc):
        self._pageinc = inc
        session.runtime << RWTSetOperation(self.id, {'pageIncrement': self.pageinc})

    @property
    def inc(self):
        return self._inc

    @inc.setter
    @checkwidget
    def inc(self, inc):
        self._inc = inc
        session.runtime << RWTSetOperation(self.id, {'pageIncrement': self.inc})

    @property
    def minimum(self):
        return self._minimum

    @minimum.setter
    @checkwidget
    def minimum(self, minimum):
        self._minimum = minimum
        session.runtime << RWTSetOperation(self.id, {'minimum': self.minimum})

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    @checkwidget
    def maximum(self, maximum):
        self._maximum = maximum
        session.runtime << RWTSetOperation(self.id, {'maximum': self.maximum})

    def compute_size(self):
        w, h = Widget.compute_size(self)
        h += (19) * 2 + 3 # constant vertical offset of the thumb
        w += 2 * 8 # constant horizontal offset of the thumb
        if self.theme.bgimg is not None and self.theme.bgimg != 'none':
            w += self.theme.bgimg.width.value
            h += self.theme.bgimg.height.value
        return (w, h) if RWT.HORIZONTAL in self.style else (h, w)



class Slider(Widget):
    _rwt_class_name_ = 'rwt.widgets.Slider'
    _styles_ = Widget._styles_ + {'horizontal': RWT.HORIZONTAL,
                                  'vertical': RWT.VERTICAL}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.HORIZONTAL)


    @constructor('Slider')
    def __init__(self, parent, minimum=None, maximum=None, selection=None, increment=None, horizontal=True, thumb=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = SliderTheme(self, session.runtime.mngr.theme)
        self.orientation = horizontal
        self._minimum = minimum
        self._maximum = maximum
        self._selection = selection
        self._increment = increment
        self._thumb = thumb
        self.on_select = OnSelect(self)
        if self not in parent.children:
            parent.children.append(self)


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.HORIZONTAL in self.style:
            options.style.append('HORIZONTAL')
        elif RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
        if self.minimum:
            options.minimum = self._minimum
        if self.maximum:
            options.maximum = self._maximum
        if self.selection:
            options.selection = self._selection
        if self.increment:
            options.pageIncrement = self._increment
        if self.thumb:
            options.thumb = self._thumb
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)

    @property
    def selection(self):
        return self._selection

    @selection.setter
    @checkwidget
    def selection(self, selection):
        self._selection = selection
        session.runtime << RWTSetOperation(self.id, {'selection': self.selection})

    @property
    def thumb(self):
        return self._thumb

    @thumb.setter
    @checkwidget
    def thumb(self, thumb):
        self._thumb = thumb
        session.runtime << RWTSetOperation(self.id, {'thumb': self.thumb})

    @property
    def increment(self):
        return self._increment

    @increment.setter
    @checkwidget
    def increment(self, increment):
        self._increment = increment
        session.runtime << RWTSetOperation(self.id, {'pageIncrement': self.increment})

    @property
    def selection(self):
        return self._selection

    @selection.setter
    @checkwidget
    def selection(self, selection):
        self._selection = selection
        session.runtime << RWTSetOperation(self.id, {'selection': self.selection})

    @property
    def minimum(self):
        return self._minimum

    @minimum.setter
    @checkwidget
    def minimum(self, minimum):
        self._minimum = minimum
        session.runtime << RWTSetOperation(self.id, {'minimum': self.minimum})

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    @checkwidget
    def maximum(self, maximum):
        self._maximum = maximum
        session.runtime << RWTSetOperation(self.id, {'maximum': self.maximum})

    def compute_size(self):
        w, h = Widget.compute_size(self)

        # add widths/heights of up- and down icons depending on orientation
        if RWT.HORIZONTAL in self.style:
            w += sum([x.width.value for x in self.theme.icons]) + ifnone(self.thumb, 0, self.thumb)
            h += max([x.height.value for x in self.theme.icons])
        elif RWT.VERTICAL in self.style:
            w += max([x.width.value for x in self.theme.icons])
            h += sum([x.height.value for x in self.theme.icons]) + ifnone(self.thumb, 0, self.thumb)

        # add borders
        for t, r, b, l in (self.theme.borders, self.theme.bordersthumb):
            w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
            h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)

        # add paddings
        for padding in [self.theme.padding] + self.theme.paddingicons:
            if padding:
                w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
                h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)

        #horizontal:
        # w = icondownwidth + iconupwidth + iconthumbwidth + borderslider-left/right + borderthumb-left/right + self.thumb
        # h = max(icondownheight/iconupheight/iconthumbheight) + borderslider-top/bottom + borderthumb-top/bottom

        #vertical:
        # w = max(icondownwidth/iconupwidth/iconthumbwidth) + borderslider-left/right + burderthumb-left/right
        # h = icondownheight + iconupheight + iconthumbheight + borderslider-top/bottom + borderthumb-top/bottom + self.thumb

        return w, h


class Group(Composite):
    
    _rwt_class_name_ = 'rwt.widgets.Group'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Group')
    def __init__(self, parent, text='', layout=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = GroupTheme(self, session.runtime.mngr.theme)
        self._text = text
        if layout is not None:
            self.layout = layout

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        options.text = self.text
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
    
    @property
    def text(self):
        return self._text

    @text.setter
    @checkwidget    
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})
        
    @Widget.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = list(map(px, bounds))
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})

    def compute_size(self):
        width, height = Composite.compute_size(self)
        t, r, b, l = self.compute_fringe()
        return width + l + r, height + t + b

    def compute_fringe(self):
        top, right, bottom, left = (0, 0, 0, 0)
        # frame border
        t, r, b, l = self.theme.frame_borders
        top += ifnone(t, 0, lambda b: b.width)
        right += ifnone(r, 0, lambda b: b.width)
        bottom += ifnone(b, 0, lambda b: b.width)
        left += ifnone(l, 0, lambda b: b.width)
        # frame padding
        padding = self.theme.frame_padding
        if padding:
            top += ifnone(padding.top, 0)
            right += ifnone(padding.right, 0)
            bottom += ifnone(padding.bottom, 0)
            left += ifnone(padding.left, 0)
        # frame margin
        margin = self.theme.frame_margin
        if margin:
            left += ifnone(margin.left, 0)
            right += ifnone(margin.right, 0)
            bottom += ifnone(margin.bottom, 0)
            top += ifnone(margin.top, 0)
        # group margin
        margin = self.theme.margin
        if margin:
            top += ifnone(margin.top, 0)
            right += ifnone(margin.right, 0)
            bottom += ifnone(margin.bottom, 0)
            left += ifnone(margin.left, 0)
        return top, right, bottom, left

        # width, height = self.compute_size()
        # return width, height
    
    def viewport(self):
        x = y = 0
        # border
        t, _, _, l = self.theme.borders
        x += ifnone(l, 0, lambda b: b.width)
        y += ifnone(t, 0, lambda b: b.width)
        # padding
        padding = self.theme.padding
        if padding:
            x += ifnone(padding.left, 0)
            y += ifnone(padding.top, 0)
        # margin
        margin = self.theme.margin
        if margin:
            x += ifnone(margin.left, 0)
            y += ifnone(margin.top, 0)
        # label border
        t, _, _, l = self.theme.label_borders
        y += ifnone(t, 0, lambda b: b.width)
        # label padding
        padding = self.theme.label_padding
        if padding:
            y += ifnone(padding.top, 0)
        #label margin
        margin = self.theme.label_margin
        if margin:
            y += ifnone(margin.top, 0)
        # frame border
        t, r, b, l = self.theme.frame_borders
        x += ifnone(l, 0, lambda b: b.width)
        y += ifnone(t, 0, lambda b: b.width)
        # frame padding
        padding = self.theme.frame_padding
        if padding:
            x += ifnone(padding.left, 0)
            y += ifnone(padding.top, 0)
        # frame margin
        margin = self.theme.frame_margin
        if margin:
            x += ifnone(margin.left, 0)
            y += ifnone(margin.top, 0)
        return px(x), px(y)


class Browser(Widget):
    _rwt_class_name_ = 'rwt.widgets.Browser'
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('Browser')
    def __init__(self, parent, url=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = BrowserTheme(self, session.runtime.mngr.theme)
        self._url = self._loadurl(url)
        self._FN_TEMPLATE = "(function(){{{}}})();"

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        options.url = self.url
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)

    def _loadurl(self, url):
        '''
        Will check is either a valid url, an already registered file
        or a local file.
        If it is a local file, it will register the resource and
        provide the location as the url.
        Note: The url is only being checked for a valid format,
        there is no guarantee that the url actually exists.
        :param url:     the input url
        :return:        either the input url or a resource location
                        of a registered resource file
        '''
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if url:
            m = regex.match(url)
            if m:
                return url
            elif session.runtime.mngr.resources.get(url):
                return session.runtime.mngr.resources.get(url).location
            elif os.path.isfile(os.path.abspath(url)):
                with open(os.path.abspath(url), 'rb') as f:
                    res = session.runtime.mngr.resources.registerf(url, 'text/html', f)
                    return res.location
            else:
                raise Exception('URL "{}" is not a valid url or existing local file!'.format(url))
        else:
            with open(os.path.join(locations.rc_loc, 'static', 'html', 'blank.html'), encoding='utf8') as f:
                res = session.runtime.mngr.resources.registerf('_blank.html', 'text/html', f)
            return res.location

    @property
    def url(self):
        return self._url


    @url.setter
    @checkwidget
    def url(self, url):
        self._url = self._loadurl(url)
        session.runtime << RWTSetOperation(self.id, {'url': self.url})


    def eval(self, fn):
        session.runtime << RWTCallOperation(self.id, 'evaluate', args={'script': self._FN_TEMPLATE.format(fn)})


    def compute_size(self):
        return 0, 0


class Menu(Widget):

    _rwt_class_name = 'rwt.widgets.Menu'
    _styles_ = Widget._styles_ + {'bar': RWT.BAR, 'dropdown': RWT.DROP_DOWN, 'popup': RWT.POPUP}
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('Menu')
    def __init__(self, parent, index=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = MenuTheme(self, session.runtime.mngr.theme)
        self._index = index
        self._mIndex = 0
        self._items = []
        if self in parent.children and RWT.DROP_DOWN in self.style:
            parent.children.remove(self)


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.DROP_DOWN in self.style:
            options.style.append('DROP_DOWN')
        elif RWT.BAR in self.style:
            options.style.append('BAR')
        elif RWT.POPUP in self.style:
            options.style.append('POP_UP')
        options.mnemonicIndex = self._mIndex
        # options.customVariant = 'variant_navigation'
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)


    def compute_size(self):
        w, h = Widget.compute_size(self)
        sizes = [i.compute_size() for i in self.items]
        if RWT.BAR in self.style:
            w = sum([w for w, _ in sizes])
            h = max([h for _, h in sizes])
        elif RWT.DROP_DOWN in self.style:
            w = max([w for w, _ in sizes])
            h = sum([h for _, h in sizes])
        return w, h


    def unhide(self):
        session.runtime << RWTCallOperation(self.id, 'unhideItems', {'reveal': True})


    def additem(self, text=None, img=None, index=0, **options):
        item = MenuItem(self, text=text, img=img, index=index, **options)
        self.items.append(item)
        return item

    @property
    def items(self):
        return self._items

    def rmitem(self, idx):
        self.items.pop(idx).dispose()


class MenuItem(Widget):

    _rwt_class_name = 'rwt.widgets.MenuItem'
    _styles_ = Widget._styles_ + {'cascade': RWT.CASCADE,
                                  'push': RWT.PUSH,
                                  'separator': RWT.SEPARATOR,
                                  'check': RWT.CHECK,
                                  'radio': RWT.RADIO}
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('MenuItem')
    def __init__(self, parent, text=None, img=None, index=0, menu=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = MenuItemTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._img = img
        self._index = index
        self._menu = menu
        self._mIndex = None
        if self in self.parent.children:
            self.parent.children.remove(self)
        self.parent.items.append(self)
        self.on_select = OnSelect(self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.PUSH in self.style:
            options.style.append('PUSH')
        elif RWT.CASCADE in self.style:
            options.style.append('CASCADE')
        elif RWT.SEPARATOR in self.style:
            options.style.append('SEPARATOR')
        elif RWT.RADIO in self.style:
            options.style.append('RADIO')
        elif RWT.CHECK in self.style:
            options.style.append('CHECK')
        options.index = self._index
        if self.text:
            options.text = self.text
        if self.img:
            options.image = self._get_rwt_img(self.img)
        if self._menu:
            options.menu = self._menu.id
        if self._mIndex:
            options.mnemonicIndex = self._mIndex
        # options.customVariant = 'variant_navigation'
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True

    def _handle_set(self, op):
        Widget._handle_set(self, op)
                
    def compute_size(self):
        w, h = Widget.compute_size(self)
        if self.text:
            w_, h_ = session.runtime.textsize_estimate(self.theme.font, self.text, self.shell())
            w += w_
            h += h_
        return w, h


    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width.value, img.height.value]
        return img


    @property
    def img(self):
        return self._img


    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {
            'image': self._get_rwt_img(self.img)})

    @property
    def text(self):
        return self._text


    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': text})


class List(Widget):
    _rwt_class_name = 'rwt.widgets.List'
    _styles_ = Widget._styles_ + {'multi': RWT.MULTI,
                                  'hscroll': RWT.HSCROLL,
                                  'vscroll': RWT.VSCROLL}
    _defstyle_ = Widget._defstyle_ |  RWT.BORDER
    
    @constructor('List')
    def __init__(self, parent, items=None, markup=False, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ListTheme(self, session.runtime.mngr.theme)
        self._items = None
        self._itemidx = None
        self._setitems(items)
        self._selidx = []
        self.on_select = OnSelect(self)
        self._markup = markup
        self._itemheight = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.MULTI in self.style:
            options.style.append('MULTI')
        else:
            options.style.append('SINGLE')
        options.markupEnabled = self._markup
        options.items = list(map(str, self._items))
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True
    
    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'selection':
                self._selidx = value
    
    @Widget.bounds.setter
    def bounds(self, b):
        Widget.bounds.fset(self, b)
        self.setitemheight()

    def setitemheight(self):
        h = self._computeitemheight()
        session.runtime << RWTSetOperation(self.id, {'itemDimensions': [max(0, self.bounds[2].value), h.value]})

    def _computeitemheight(self):
        if self.itemheight is None:
            _, h = session.runtime.textsize_estimate(self.theme.font, 'X', self.shell())
            if self.markup:
                lines = [len(i.split('<br>')) for i in self.items]
                if lines:
                    h *= max(lines)
        else:
            h = self.itemheight
        padding = self.theme.item_padding
        if padding:
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        return max(0, h)


    def create_content(self):
        if RWT.HSCROLL in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
        if RWT.VSCROLL in self.style:
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True
        self.content = Composite(self)
    
    @property
    def markup(self):
        return self._markup
    
    @markup.setter
    def markup(self, m):
        self._markup = m
        session.runtime << RWTSetOperation(self.id, {'markupEnabled': self._markup})
    
    @property
    def itemheight(self):
        return self._itemheight
    
    @itemheight.setter
    def itemheight(self, h):
        self._itemheight = h
        self.bounds = self.bounds # update the bounds
    
    def _setitems(self, items):
        if items is None:
            items = []
        if isinstance(items, dict):
            if not all([type(i) is str for i in items]): 
                raise TypeError('All keys in an item dictionary must be strings.')
            if type(items) is dict:
                self._items = OrderedDict(((k, items[k]) for k in sorted(items)))
        elif type(items) in (list, tuple):
            items = OrderedDict(((str(i), i) for i in items))
        else: raise TypeError('Invalid type for List items: %s' % type(items))
        self._items = items
            
    @property
    def items(self):
        return self._items
    
    @items.setter
    def items(self, items):
        self._setitems(items)
        session.runtime << RWTSetOperation(self.id, {'items': list(self.items.keys())})
        self.setitemheight()

    @property
    def selection(self):
        sel = [self.items[list(self.items.keys())[i]] for i in self._selidx]
        if RWT.MULTI not in self.style: 
            if not sel: return None
            sel = sel[0]
        return sel
    
    @selection.setter
    def selection(self, sel):
        if RWT.MULTI in self.style:
            if type(sel) is list:
                raise TypeError('Expected list, got %s' % type(sel))
            sel = [list(self._items.values()).index(s) for s in sel]
        else:
            sel = list(self._items.values()).index(sel) if sel is not None else None
        self.selidx = sel
        
    @property
    def selidx(self):
        if RWT.MULTI not in self.style:
            if not self._selidx: return None
            else: return self._selidx[0]
        return self._selidx
    
    @selidx.setter
    def selidx(self, sel):
        if type(sel) is not list:
            if RWT.MULTI in self.style:
                raise TypeError('Expected list, got %s' % type(sel))
            else: 
                sel = [sel] if sel is not None else []
        self._selidx = sel
        session.runtime << RWTSetOperation(self.id, {'selectionIndices': sel})
    
    def compute_size(self):
        h = w = 0
        if RWT.VSCROLL not in self.style:
            h = len(self.items) * self._computeitemheight()
        return w, h
    
    # def compute_fringe(self):
    #     return 0, 0


class Table(Widget):

    _rwt_class_name_ = 'rwt.widgets.Grid'

    _styles_ = Widget._styles_ + BiMap({'noscroll': RWT.NOSCROLL,
                                        'single': RWT.SINGLE,
                                        'multi': RWT.MULTI,
                                        'check': RWT.CHECK})
    _defstyle_ = Widget._defstyle_ | RWT.SINGLE | RWT.BORDER

    @constructor('Table')
    def __init__(self, parent, markupenabled=False, bgimg=None, indentwidth=0, items=0,
                 itemheight=25, headervisible=True, headerheight=30, linesvisible=True,
                 colsmoveable=False, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableTheme(self, session.runtime.mngr.theme)
        self._markupenabled = markupenabled
        self._hbar, self._vbar = None, None
        self._bgimg = bgimg
        self._indentwidth = indentwidth
        self._columncount = 0
        self._itemcount = items
        self._itemheight = itemheight
        self._linesvisible = linesvisible
        self._headervisible = headervisible
        self._headerheight = headerheight
        self._colsmoveable = colsmoveable
        self._columns = []
        self._items = []
        self._selection = []
        self._sortedby = None

    def create_content(self):
        if RWT.NOSCROLL not in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.SINGLE in self.style:
            options.style.append('SINGLE')
        elif RWT.MULTI in self.style:
            options.style.append('MULTI')
        if RWT.CHECK in self.style:
            options.style.append('CHECK')
            options.checkBoxMetrics = [4, 21]
        options.appearance = 'table'
        options.indentionWidth = self._indentwidth
        options.markupEnabled = self._markupenabled
        options.headerVisible = self._headervisible
        options.headerHeight = self._headerheight
        options.linesVisible = self._linesvisible
        options.itemHeight = self._itemheight
        options.treeColumn = -1
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._selection = [session.runtime.windows[id_].idx for id_ in value]

    @property
    def hbar(self):
        return self._hbar

    @property
    def vbar(self):
        return self._vbar

    @property
    def items(self):
        return list(self._items)

    @items.setter
    @checkwidget
    def items(self, items):
        for i, item in enumerate(items):
            if item not in self.items:
                raise ValueError('item %s not found in table. Create new items using Table.additem().' % (item))
            item._setidx(i)
        self._items = items
        session.runtime << RWTCallOperation(self.id, 'update', {})
        session.runtime << RWTSetOperation(self.id, {'itemCount': len(self._items)})

    @property
    def cols(self):
        return self._columns

    @cols.setter
    @checkwidget
    def cols(self, cols):
        self._columns = cols
        session.runtime << RWTSetOperation(self.id, {'columnOrder': [c.id for c in self._columns]})

    @property
    def colcount(self):
        return self._columncount

    @colcount.setter
    @checkwidget
    def colcount(self, colcount):
        self._columncount = colcount
        session.runtime << RWTSetOperation(self.id, {'columnCount': colcount})

    # @property
    # def itemcount(self):
    #     return self._itemcount

    # @itemcount.setter
    # @checkwidget
    # def itemcount(self, items):
    #     self._itemcount = items
    #     session.runtime << RWTSetOperation(self.id, {'itemCount': items})

    @property
    def itemheight(self):
        return self._itemheight

    @itemheight.setter
    @checkwidget
    def itemheight(self, itemheight):
        self._itemheight = itemheight
        session.runtime << RWTSetOperation(self.id, {'itemheight': itemheight})

    def linesvisible(self, visible):
        self._linesvisible = visible
        session.runtime << RWTSetOperation(self.id, {'linesVisible': visible})

    def backgroundimg(self, imgpath):
        session.runtime << RWTSetOperation(self.id, {'backgroundImage': self._get_rwt_img(self.img)})

    def headervisible(self, visible):
        self._headervisible = visible
        session.runtime << RWTSetOperation(self.id, {'headerVisible': visible})

    @property
    def colsmoveable(self):
        return self._colsmoveable

    @colsmoveable.setter
    @checkwidget
    def colsmoveable(self, moveable):
        self._colsmoveable = moveable
        for c in self.cols:
            c.moveable(moveable)

    def itemmetrics(self):
        metrics = []
        left = 0
        maxheight = 0
        for i, col in enumerate(self.cols):
            width, height = map(int, col.compute_size())
            width = ifnone(col.width, width)
            maxheight = max(height, maxheight)
            col.left = left
            session.runtime << RWTSetOperation(col.id, {'width': width})
            imgwidth = 0
            for item in self.items:
                imgwidth = int(max(imgwidth, item.imgwidth(i)))
            imgleft = left + col.theme.padding.left.value
            if RWT.CHECK in self.style and i == 0:
                imgleft += self.theme.checkbox_width + self.theme.checkbox_margin.left + self.theme.checkbox_margin.right
            textleft = imgleft + imgwidth
            if imgwidth and self.items:
                textleft += item.theme.cell_spacing
            textwidth = max(0, width - textleft + left)
            metrics.append([col.idx, left, width, imgleft, imgwidth, textleft, textwidth])
            left += width
        session.runtime << RWTSetOperation(self.id, {'itemMetrics': [[int(e) for e in m] for m in metrics]})
        session.runtime << RWTSetOperation(self.id, {'headerHeight': int(maxheight)})

    def additem(self, texts, index=None, **options):
        item = TableItem(self, idx=index, texts=texts, **options)
        session.runtime << RWTSetOperation(self.id, {'itemCount': len(self._items)})
        return item

    def rmitem(self, item):
        if type(item) is int:
            item = self._items[item]
        item.dispose()
        self._items.remove(item)
        try:
            self._selection.remove(item.idx)
        except ValueError: pass
        for i in self._items[item.idx:]:
            i._setidx(i.idx - 1)
            if i.idx + 1 in self._selection:
                self._selection.remove(i.idx + 1)
                self._selection.append(i.idx)
        session.runtime << RWTSetOperation(self.id, {'itemCount': len(self.items)})

    def addcol(self, text, tooltip=None, moveable=False, sortable=False, **options):
        col = TableColumn(self, text=text, tooltip=tooltip, moveable=moveable, sortable=sortable, **options)
        self.colcount = max(self.colcount, len(self.cols))
        session.runtime << RWTSetOperation(self.id, {'columnOrder': [c.id for c in self._columns]})
        return col

    def compute_size(self):
        self.itemmetrics()
        return Widget.compute_size(self)

    @property
    def selection(self):
        sel = [self.items[i] for i in self._selection]
        if RWT.MULTI in self.style:
            return sel
        else:
            return first(sel)

    def sortby(self, column, direction):
        self._sortedby = column, direction
        session.runtime << RWTSetOperation(self.id, {'sortColumn': column.id, 'sortDirection': direction})

    @property
    def sortedby(self):
        return self._sortedby

    def update_table(self):
        session.runtime << RWTCallOperation(self.id, 'update', {})


class Tree(Table):

    _rwt_class_name_ = 'rwt.widgets.Grid'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Tree')
    def __init__(self, parent, markupenabled=False, bgimg=None, indentwidth=0, items=0,
                 itemheight=25, headervisible=True, headerheight=30, linesvisible=True,
                 colsmoveable=False, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableTheme(self, session.runtime.mngr.theme)
        self._markupenabled = markupenabled
        self._hbar, self._vbar = None, None
        self._bgimg = bgimg
        self._indentwidth = indentwidth
        self._columncount = 0
        self._itemcount = items
        self._itemheight = itemheight
        self._linesvisible = linesvisible
        self._headervisible = headervisible
        self._headerheight = headerheight
        self._colsmoveable = False
        self._columns = []
        self._items = []
        self._selection = []

    def create_content(self):
        if RWT.NOSCROLL not in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.SINGLE in self.style:
            options.style.append('SINGLE')
        elif RWT.MULTI in self.style:
            options.style.append('MULTI')
        if RWT.CHECK in self.style:
            options.style.append('CHECK')
            options.checkBoxMetrics = [4, 21]
        options.appearance = 'tree'
        options.indentionWidth = self._indentwidth
        options.markupEnabled = self._markupenabled
        options.headerVisible = self._headervisible
        options.headerHeight = self._headerheight
        options.linesVisible = self._linesvisible
        options.itemHeight = self._itemheight
        options.treeColumn = -1
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)


class TableItem(Widget):

    _rwt_class_name_ = 'rwt.widgets.GridItem'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('TableItem')
    def __init__(self, parent, texts=None, idx=None, images=None, data=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableItemTheme(self, session.runtime.mngr.theme)
        self._idx = idx if idx else len(parent.items)
        self._texts = texts
        self._images = images
        if self in parent.children:
            parent.children.remove(self)
        self.parent._items.insert(self._idx, self)
        self.data = data

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if 'style' in options:
            del options['style']
        if 'enabled' in options:
            del options['enabled']
        options.texts = self._texts
        options.index = self.idx
        if self.images:
            options.images = [None if i is None else self._get_rwt_img(i) for i in self._images]
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True

    @property
    def idx(self):
        return self._idx

    @checkwidget
    def _setidx(self, idx):
        self._idx = idx
        session.runtime << RWTSetOperation(self.id, {'index': self._idx})

    @property
    def texts(self):
        return self._texts

    @texts.setter
    @checkwidget
    def texts(self, texts):
        self._texts = texts
        session.runtime << RWTSetOperation(self.id, {'texts': self._texts})

    @property
    def images(self):
        return self._images

    @images.setter
    @checkwidget
    def images(self, images):
        self._images = images
        session.runtime << RWTSetOperation(self.id, {'images': [self._get_rwt_img(i) for i in images]})

    def imgwidth(self, idx):
        w = 0
        if self.images:
            if self.images[idx] is not None:
                _, w = self.images[idx].size
        return w

    def compute_size(self):
        width, height = Widget.compute_size(self)
        if self.img is not None:
            w, h = self.imgwidth()
            w += '3'
        else:
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        width += w
        height += h

        self.parent.itemmetrics(width, height)
        return width, height


class TableColumn(Widget):

    _rwt_class_name_ = 'rwt.widgets.GridColumn'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('TableColumn')
    def __init__(self, parent, text=None, tooltip=None, width=None, img=None, moveable=False, check=False,
                 sortable=False, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableColumnTheme(self, session.runtime.mngr.theme)
        self._idx = parent.colcount
        self._text = text
        self._tooltip = tooltip
        self._width = width
        self._check = check
        self._img = img
        self._moveable = parent.colsmoveable
        self.on_move = OnMove(self)
        self.on_select = OnSelect(self)
        self._left = 0
        self._sortable = sortable
        if self in parent.children:
            parent.children.remove(self)
        self.parent.cols.insert(self._idx, self)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = self._text
        options.index = self.idx
        options.width = self._width
        options.left = self._left
        options.moveable = self._moveable
        if self._check:
            options.check = True
        if self._tooltip:
            options.toolTip = self._tooltip
        if self.img:
            options.image = self._get_rwt_img(self.img)
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        if self._sortable:
            self.on_select += self.togglesort

    def togglesort(self, _):
        if not self._sortable:
            raise AttributeError('column is not sortable')
        sortedby = self.parent.sortedby
        if sortedby is None:
            direction = 'down'
        else:
            oldcol, direction = sortedby
        self.parent.sortby(self, 'up' if (direction == 'down' or oldcol is not self) else 'down')

    def _resize(self, width):
        self._width = width
        self.parent.itemmetrics()

    def _handle_call(self, op):
        if op.method == 'move': self.mv(op.args)
        if op.method == 'resize': self._resize( **op.args)

    def mv(self, args):
        self.parent.cols.remove(self)
        for i, c in enumerate(self.parent.cols):
            if c.left < args.left:
                if i != len(self.parent.cols)-1: continue
                else:
                    self.parent.cols.append(self)
                    break
            else:
                self.parent.cols.insert(i, self)
                break
        self.parent.itemmetrics()
        session.runtime << RWTSetOperation(self.parent.id, {'columnOrder': [c.id for c in self.parent.cols]})

    @property
    def idx(self):
        return self._idx

    @idx.setter
    @checkwidget
    def idx(self, idx):
        self._idx = idx

    @property
    def text(self):
        return self._text

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    @property
    def img(self):
        return self._img

    @img.setter
    @checkwidget
    def img(self, img):
        self._img = img
        session.runtime << RWTSetOperation(self.id, {'image': self._get_rwt_img(self.img)})

    @property
    def width(self):
        return self._width

    @width.setter
    @checkwidget
    def width(self, width):
        self._width = width
        session.runtime << RWTSetOperation(self.id, {'width': width})

    @property
    def left(self):
        return self._left

    @left.setter
    @checkwidget
    def left(self, left):
        self._left = left
        session.runtime << RWTSetOperation(self.id, {'left': left})

    def compute_size(self):
        width, height = Widget.compute_size(self)
        wimg, himg = 0, 0
        if self.img is not None:
            wimg, himg = self.img.size
            wimg += 2
        wtxt, htxt = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        width += wimg + wtxt + 1 if self.parent._linesvisible else 0
        height += max(himg, htxt)
        return width, height

    def moveable(self, moveable):
        if moveable:
            self.on_select += self.mv
        else:
            self.on_select -= self.mv
        session.runtime << RWTSetOperation(self.id, {'moveable': moveable})

    def alignment(self, alignment):
        session.runtime << RWTSetOperation(self.id, {'alignment': alignment})


class GC(object):
    '''the graphics context'''
    _rwt_class_name = 'rwt.widgets.GC'

    class Operation(object):
        '''Abstract base class for all GC Operations'''

        def json(self): raise NotImplemented()


    class save(Operation):
        '''Saves the current state of the GC'''
        def json(self): return ['save']


    class restore(Operation):
        '''Restores the most recently saved state of the GC'''
        def json(self): return ['restore']


    class moveto(Operation):
        '''Moves the cursor to the given coordinates.'''
        def __init__(self, x, y):
            GC.Operation.__init__(self)
            self.x = x
            self.y = y
        
        def json(self):
            return ['moveTo', self.x, self.y]


    class lineto(Operation):
        '''Draws a line from the current cursor position to the given coordinates.'''
        def __init__(self, x, y):
            GC.Operation.__init__(self)
            self.x = x
            self.y = y
            
        def json(self):
            return ['lineTo', self.x, self.y]


    class linewidth(Operation):
        '''Sets the line width to the given size.'''
        def __init__(self, w):
            GC.Operation.__init__(self)
            self.w = w
            
        def json(self):
            return ['lineWidth', self.w]


    class stroke(Operation):
        '''Operation to actually paint?'''
        def json(self):
            return ['stroke']


    class draw_grid(Operation):
        '''Draws a grid filling the whole canvas.'''
        def __init__(self, stepwidthX, stepwidthY, color):
            GC.Operation.__init__(self)
            self.stepwidthX = stepwidthX
            self.stepwidthY = stepwidthY
            self.color = color

        def json(self):
            return ['drawGrid', self.stepwidthX, self.stepwidthY, self.color]


    class stroke_style(Operation):
        '''Sets the color and opacity of the stroke.'''
        def __init__(self, color):
            GC.Operation.__init__(self)
            self.color = parse_value(color, Color)

        def json(self):
            return ['strokeStyle', [int(round(255 * self.color.red)), 
                                    int(round(255 * self.color.green)), 
                                    int(round(255 * self.color.blue)), 
                                    int(round(255 * self.color.alpha))]]

    class fill_style(Operation):
        '''Sets the color and opacity of the fill.'''
        def __init__(self, color):
            GC.Operation.__init__(self)
            self.color = parse_value(color, Color)

        def json(self):
            return ['fillStyle', [int(round(255 * self.color.red)),
                                    int(round(255 * self.color.green)),
                                    int(round(255 * self.color.blue)),
                                    self.color.alpha]]


    class fill_text(Operation):
        '''Sets the color and opacity of the text fill.'''
        _styles_ = BiMap({'mnemonic': GCBITS.DRAW_MNEMONIC,
                          'delimiter': GCBITS.DRAW_DELIMITER,
                          'tab': GCBITS.DRAW_TAB,
                          'aligncenterx': GCBITS.ALIGN_CENTERX,
                          'aligncentery': GCBITS.ALIGN_CENTERY})
        _defstyle_ = BitField(GCBITS.DRAW_DELIMITER | GCBITS.DRAW_TAB)

        def __init__(self, text, x, y, **options):
            GC.Operation.__init__(self)
            self.text = text
            self.x = x
            self.y = y
            self.style = BitField(type(self)._defstyle_)
            for k, v in options.items():
                if k in type(self)._styles_: self.style.setbit( type(self)._styles_[k:], v)

        def json(self):
            drawMnemonic = GCBITS.DRAW_MNEMONIC in self.style
            drawDelimiter = GCBITS.DRAW_DELIMITER in self.style
            drawTab = GCBITS.DRAW_TAB in self.style
            aligncenterx = GCBITS.ALIGN_CENTERX in self.style
            aligncentery = GCBITS.ALIGN_CENTERY in self.style
            return ['fillText', self.text, drawMnemonic, drawDelimiter, drawTab, self.x, self.y, aligncenterx, aligncentery ]


    class stroke_text(Operation):
        '''Sets the color and opacity of the text stroke.'''
        _styles_ = BiMap({'mnemonic': GCBITS.DRAW_MNEMONIC,
                          'delimiter': GCBITS.DRAW_DELIMITER,
                          'tab': GCBITS.DRAW_TAB,
                          'aligncenterx': GCBITS.ALIGN_CENTERX,
                          'aligncentery': GCBITS.ALIGN_CENTERY})
        _defstyle_ = BitField(GCBITS.DRAW_DELIMITER | GCBITS.DRAW_TAB)
        def __init__(self, text, x, y, **options):
            GC.Operation.__init__(self)
            self.text = text
            self.x = x
            self.y = y
            self.style = BitField(type(self)._defstyle_)
            for k, v in options.items():
                if k in type(self)._styles_: self.style.setbit( type(self)._styles_[k:], v)

        def json(self):
            drawMnemonic = GCBITS.DRAW_MNEMONIC in self.style
            drawDelimiter = GCBITS.DRAW_DELIMITER in self.style
            drawTab = GCBITS.DRAW_TAB in self.style
            aligncenterx = GCBITS.ALIGN_CENTERX in self.style
            aligncentery = GCBITS.ALIGN_CENTERY in self.style
            return ['strokeText', self.text, drawMnemonic, drawDelimiter, drawTab, self.x, self.y, aligncenterx, aligncentery ]


    class draw_image(Operation):
        '''Draws an image'''
        def __init__(self, imgpath, x, y):
            GC.Operation.__init__(self)
            self.imgpath = imgpath
            self.x = x
            self.y = y

        def json(self):
            return ['drawImage', self.imgpath, self.x, self.y]


    class begin_path(Operation):
        '''Initializes a new path'''
        def json(self): return ['beginPath']


    class fill(Operation):
        '''Issues a fill operation'''
        def json(self): return ['fill']


    class ellipse(Operation):
        '''Draws an ellipse'''
        def __init__(self, x, y, rx, ry, rot, start, end, clockwise=True):
            GC.Operation.__init__(self)
            self.x = x
            self.y = y
            self.rx = rx
            self.ry = ry
            self.rot = rot
            self.start = start
            self.end = end
            self.clockwise = clockwise
            
        def json(self):
            return ['ellipse', self.x, self.y, self.rx, self.ry, self.rot, self.start, self.end, not self.clockwise]


    class font(Operation):
        '''Sets the font of the text'''
        _styles_ = BiMap({'bold': GCBITS.BOLD,
                          'normal': GCBITS.NORMAL,
                          'italic': GCBITS.ITALIC})
        _defstyle_ = BitField(GCBITS.NORMAL)
        def __init__(self, font, fontsize, **options):
            self.font = font.split(',') # needs to be a list with fallback options
            self.fontsize = fontsize
            self.style = BitField(type(self)._defstyle_)
            for k, v in options.items():
                if k in type(self)._styles_: self.style.setbit(type(self)._styles_[k:], v)

        def json(self):
            if GCBITS.NORMAL in self.style:
                self.bold = False
                self.italic = False
            else:
                self.bold = GCBITS.BOLD in self.style
                self.italic = GCBITS.ITALIC in self.style
            return ['font', [self.font, self.fontsize, self.bold, self.italic]]


    class rect(Operation):
        '''Draws a rectangle'''
        def __init__(self, x, y, w, h):
            GC.Operation.__init__(self)
            self.x = x
            self.y = y
            self.w = w
            self.h = h

        def json(self):
            return ['rect', self.x, self.y, self.w, self.h]

    class erase(Operation):
        '''Erases a rectangular area'''
        def __init__(self, x, y, w, h):
            GC.Operation.__init__(self)
            self.x = x
            self.y = y
            self.w = w
            self.h = h

        def json(self):
            return ['clearRect', self.x, self.y, self.w, self.h]


    def __init__(self, _id, parent):
        self.id = _id
        self.parent = parent
        
    def _create_rwt_widget(self):
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, {'parent': self.parent.id})
    
    def init(self, width, height):
        session.runtime << RWTCallOperation(self.id, 'init', {'width': width, 
                                                              'height': height,
                                                              'font': [['Verdana', 'Helvetica', 'sans-serif'], 14, False, False],
                                                              'fillStyle': [255, 255, 255, 255],
                                                              'strokeStyle': [74, 74, 74, 255]})
        
    def draw(self, operations):
        '''Sends the drawing operations to the client.
        Must be a list of :class:`pyrap.GC.Operation` objects.'''
        session.runtime << RWTCallOperation(self.id, 'draw', {'operations': [o.json() for o in operations]})
        
    def __enter__(self):
        self.parent.clear()
        return self
        
    def __exit__(self, e, t, tb):
        if e is not None: raise e
        self.parent.draw()
        

class Canvas(Widget):
    '''HTML5 2D canvas widget'''
    _rwt_class_name = 'rwt.widgets.Canvas'
    _styles_ = Widget._styles_ + {}
    _defstyle_ = Widget._defstyle_
    
    @constructor('Canvas')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = CanvasTheme(self, session.runtime.mngr.theme)
        self.gc = GC('%s.gc' % self.id, self)
        self.operations = []

    def __lshift__(self, op):
        self.operations.append(op)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        self.gc._create_rwt_widget()

    def draw(self):
        self.gc.draw(self.operations)

    @Widget.bounds.setter
    def bounds(self, b):
        Widget.bounds.fset(self, b)
        self.gc.init(*toint((b[2], b[3])))
        self.draw()
        
    def clear(self):
        self.operations = []
        
        
class ProgressBar(Widget):
    '''Represents a progress bar.'''
    _rwt_class_name = 'rwt.widgets.ProgressBar'
    _styles_ = Widget._styles_ + {'horizontal': RWT.HORIZONTAL,
                                  'vertical': RWT.VERTICAL,
                                  'infinite': RWT.INFINITE}
    _defstyle_ = Widget._defstyle_ | RWT.HORIZONTAL
    
    @constructor('ProgressBar')
    def __init__(self, parent, vmax=100, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ProgressBarTheme(self, session.runtime.mngr.theme)
        self._value = 0
        self._max = vmax
        
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.HORIZONTAL in self.style:
            options.style.append('HORIZONTAL')
        elif RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
        if RWT.INFINITE in self.style:
            options.style.append('INDETERMINATE')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        
    @property
    def max(self):
        return self._max
    
    @max.setter
    @checkwidget
    def max(self, m):
        self._max = m
        session.runtime << RWTSetOperation(self.id, {'maximum': self._max})
        
    @property
    def value(self):
        return self._value
    
    @value.setter
    @checkwidget
    def value(self, v):
        self._value = v
        session.runtime << RWTSetOperation(self.id, {'selection': self._value})
        
    def compute_size(self):
        return self.theme.minwidth, px(15)
            
    
class Spinner(Widget):
    _rwt_class_name = 'rwt.widgets.Spinner'
    _styles_ = Widget._styles_ + {}
    _defstyle_ = Widget._defstyle_ | RWT.BORDER
    
    @constructor('Spinner')
    def __init__(self, parent, vmin=0, vmax=100, digits=0, inc=1, pinc=10, sel=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = SpinnerTheme(self, session.runtime.mngr.theme)
        self._vmin = vmin
        self._vmax = vmax
        self._digits = digits
        self._inc = inc
        self._pinc = pinc
        self._sel = sel
        self.on_modify = OnSelect(self)
    
        
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        self.min = self._vmin
        self.max = self._vmax
        self.digits = self._digits
        self.inc = self._inc
        self.pinc = self._pinc
        self.selection = self._sel
        
    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'selection':
                self._sel = value
    
    def _handle_notify(self, op):
        events = {'Selection': self.on_modify}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True 
    
    @property
    def min(self):
        return self._vmin
    
    @min.setter
    def min(self, val):
        self._vmin = val
        session.runtime << RWTSetOperation(self.id, {'minimum': self._vmin})
        
    @property
    def max(self):
        return self._vmax
    
    @max.setter
    def max(self, val):
        self._vmax = val
        session.runtime << RWTSetOperation(self.id, {'maximum': self._vmax})
        
    @property
    def digits(self):
        return self._digits
    
    @digits.setter
    def digits(self, dig):
        self._digits = dig
        session.runtime << RWTSetOperation(self.id, {'digits': self._digits})
        
    @property
    def inc(self):
        return self._inc
    
    @inc.setter
    def inc(self, i):
        self._inc = i
        session.runtime << RWTSetOperation(self.id, {'increment': self._inc})
    
    @property
    def pinc(self):
        return self._pinc
    
    @pinc.setter
    def pinc(self, i):
        self._pinc = i
        session.runtime << RWTSetOperation(self.id, {'pageIncrement': self._pinc})
        
    @property
    def selection(self):
        return self._sel
    
    @selection.setter
    def selection(self, v):
        if type(v) is float:
            v = self.asint(v)
        if v is not None and (type(v) is not int or v < self._vmin or v > self._vmax):
            raise ValueError('invalid type or value: "%s" (must be integer in [%s, %s]' % (v, self._vmin, self._vmax))
        self._sel = v
        session.runtime << RWTSetOperation(self.id, {'selection': self._sel}) 
        
    def asfloat(self, sel):
        if sel is None: return None
        divisor = 10 ** self._digits
        return float(sel) / divisor
    
    def asint(self, val):
        s = str(val)
        before, behind = s.split('.')
        before = int(before)
        if self.digits:
            behind_ = behind[:self.digits + 1]
            if len(behind_) > self.digits:
                behind = int(round(float(behind_) / 10))
            else: behind = int(behind_)
            before = before * (10 ** self.digits)
        else:
            behind = 0
        return before + behind
    
    def compute_size(self):
        w, h = Widget.compute_size(self)
        w1, w2 = self.theme.button_widths
        text = max(str(self.min), str(self.max)) + 'XX'
        if self.digits:
            text += '.'
        tw, th = session.runtime.textsize_estimate(self.theme.font, text, self.shell())
        w += max(w1, w2)
        w += tw
        h += th
        return w, h


class FileUpload(Widget):
    _rwt_class_name_ = 'rwt.widgets.FileUpload'
    _styles_ = Widget._styles_ + {'multi': RWT.MULTI,}
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('FileUpload')
    def __init__(self, parent, text=None, accepted=None, **options):
        Widget.__init__(self, parent, **options)
        if accepted is None:
            accepted = []
        self.theme = ButtonTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._accepted = accepted
        self._fnames = []
        self._files = []
        self._token = None
        self.on_select = OnSelect(self)
        self.on_finished = OnFinished(self)
        self.handler = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        if RWT.MULTI in self.style:
            options.style.append('MULTI')
        if self._text:
            options.text = self._text
        options.style.append('PUSH')
        options.accepted = self._accepted
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
        self.on_select += self._upload

    def _handle_notify(self, op):
        events = {'Selection': self.on_select, 'Finished': self.on_finished}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        elif op.event == 'Selection':
            events[op.event].notify(_rwt_selection_event(op))
        elif op.event == 'Finished':
            events[op.event].notify()
        return True

    def _handle_set(self, op):
        for key, value in op.args.items():
            if key == 'bounds':
                self._bounds = list(map(px, value))
            if key == 'fileNames':
                self.filenames = value

    def _upload(self, *_):
        token, url = session.runtime.servicehandlers.fileuploadhandler.accept(self.filenames)
        self._token = token
        session.runtime << RWTCallOperation(self.id, 'submit', { 'url': url })

    def compute_size(self):
        width, height = Widget.compute_size(self)
        tw, th = session.runtime.textsize_estimate(self.theme.font, self._text, self.shell())
        width += tw
        height += th
        return width, height

    @property
    def text(self):
        return self._text

    @property
    def token(self):
        return self._token

    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})

    @property
    def filename(self):
        if self._fnames:
            return self._fnames[0]
        else:
            return None

    @filename.setter
    @checkwidget
    def filename(self, fname):
        self._fnames[0] = fname

    @property
    def filenames(self):
        return self._fnames

    @filenames.setter
    @checkwidget
    def filenames(self, fnames):
        self._fnames = fnames

    @property
    def files(self):
        return self._files


def error(text, halign=None, valign=None):
    return {'icon': 'error', 'text': text, 'halign': halign, 'valign': valign}

def warning(text, halign=None, valign=None):
    return {'icon': 'warning', 'text': text, 'halign': halign, 'valign': valign}

def info(text, halign=None, valign=None):
    return {'icon': 'info', 'text': text, 'halign': halign, 'valign': valign}

def accept(text, halign=None, valign=None   ):
    return {'icon': 'accept', 'text': text, 'halign': halign, 'valign': valign} 
        
class Decorator(Widget):
    _rwt_class_name = 'rwt.widgets.ControlDecorator'
    _styles_ = Widget._styles_
    _defstyle_ = Widget._defstyle_
    
    @constructor('Decorator')
    def __init__(self, parent, icon, text, halign=None, valign=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = DecoratorTheme(self, session.runtime.mngr.theme)
        if self in parent.children:
            parent.children.remove(self)
        self._icon = icon
        self._text = text
        if halign is None:
            self.halign = self.theme.image_position[1]
        else:
            self.halign = halign
        if valign is None:
            self.valign = self.theme.image_position[0]
        else:
            self.valign = valign
        
    
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.halign == 'right':
            options.style.append('RIGHT')
        elif self.halign == 'left':
            options.style.append('LEFT')
        else: raise ValueError('Illegal value for horizontal position of a control decorator: "%s"' % self.halign)
        if self.valign == 'top':
            options.style.append('TOP')
        elif self.valign == 'bottom':
            options.style.append('BOTTOM')
        elif self.valign == 'center':
            options.style.append('CENTER')
        else: raise ValueError('Illegal value for vertical position of a control decorator: "%s"' % self.valign)
        options.text = self._text
        if isinstance(self._icon, Image):
            rc = session.runtime.mngr.resources.registerc(name=None, content_type=self._icon.mimetype, content=self._icon.content)
            self.iconwidth = self._icon.width
            self.iconheight = self._icon.height
            options.image = [rc.location, self._icon.width.value, self._icon.height.value]
        else:
            if self._icon == 'info':
                img = self.theme.icon_information
            elif self._icon == 'error':
                img = self.theme.icon_error
            elif self._icon == 'warning':
                img = self.theme.icon_warning
            elif self._icon == 'accept':
                img = self.theme.icon_accept
            else: raise ValueError('unknown icon name: "%s"' % self._icon)
            rc = session.runtime.mngr.resources.getbycontent(img.content)
            options.image = [rc.location, img.width.value, img.height.value]
            self.iconwidth = img.width
            self.iconheight = img.height
        options.visible = True
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        
    
    def compute_relpos(self, bounds):
        x, y, w, h = bounds
        x_, y_ = None, None
        if self.halign == 'left':
            x_ = x - self.theme.spacing - self.iconwidth
        else:
            x_ = x + w + self.theme.spacing
        if self.valign == 'top':
            y_ = y
        elif self.valign == 'center':
            y_ = y + h / 2 - self.iconheight / 2
        elif self.valign == 'bottom':
            y_ = y + h - self.iconheight
        w_ = self.iconwidth
        h_ = self.iconheight
        return x_, y_, w_, h_


class Sash(Widget):

    _rwt_class_name = 'rwt.widgets.Sash'

    _styles_ = Widget._styles_
    _defstyle_ = Widget._defstyle_

    @constructor('Sash')
    def __init__(self, parent, orientation, **options):
        Widget.__init__(self, parent, **options)
        self.theme = SashTheme(self, session.runtime.mngr.theme)
        self.orientation = orientation
        if self.orientation in ('v', 'vertical'):
            self.style |= RWT.VERTICAL
        elif self.orientation == ('h', 'horizontal'):
            self.style |= RWT.HORIZONTAL
        self.on_select = OnSelect(self)

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
        else:
            options.style.append('HORIZONTAL')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w = self.theme.width
        return (w, 0) if RWT.VERTICAL in self.style else (0, w)
