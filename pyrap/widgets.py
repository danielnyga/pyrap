'''
Created on Oct 9, 2015

@author: nyga
'''
import os

from pyrap.clientjs import gen_clientjs
from pyrap.communication import RWTListenOperation, RWTSetOperation,\
    RWTCreateOperation, RWTCallOperation, RWTDestroyOperation
from pyrap.types import Event, px, BitField, BitMask, BoolVar, NumVar, Color,\
    parse_value, Var, VarCompound, BoundedDim, pc, StringVar
from pyrap.base import session
from pyrap.utils import RStorage, BiMap, out, ifnone, pparti, stop
from pyrap.events import OnResize, OnMouseDown, OnMouseUp, OnDblClick, OnFocus,\
    _rwt_mouse_event, OnClose, OnMove, OnSelect, _rwt_selection_event, OnDispose, \
    OnNavigate, OnModify
from pyrap.exceptions import WidgetDisposedError, LayoutError, ResourceError
from pyrap.constants import RWT, inf
from pyrap.themes import LabelTheme, ButtonTheme, CheckboxTheme, OptionTheme,\
    CompositeTheme, ShellTheme, EditTheme, ComboTheme, TabItemTheme, \
    TabFolderTheme, ScrolledCompositeTheme, ScrollBarTheme, GroupTheme, \
    SliderTheme, DropDownTheme, BrowserTheme
from pyrap.layout import GridLayout, Layout, LayoutAdapter, CellLayout
import md5
import time
from pyrap import pyraplog



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
            if hasattr(self, 'create_content'):
                self.create_content()
        return wrapper
    return outer
 

class Widget(object):
    
    _styles_ = BiMap({'visible': RWT.VISIBLE, 
                      'border': RWT.BORDER,
                      'enabled': RWT.ENABLED})
    
    _defstyle_ = BitField(RWT.VISIBLE | RWT.ENABLED)
    
    def __init__(self, parent, **options):
        self._disposed = True
        self.parent = parent
        self.children = []
        self.layout = Layout()
        self._update_layout_from_dict(options)
        self._font = None
        self._css = None
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
        self.on_focus = OnFocus()
        self.on_dispose = OnDispose()
        self.style = BitField(type(self)._defstyle_)
        for k, v in options.iteritems():
            if k in type(self)._styles_: self.style.setbit(type(self)._styles_[k:], v)

            
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
        elif op.event == 'MouseDown': self.on_mousedown.notify(_rwt_mouse_event(op))
        elif op.event == 'MouseDoubleClick': self.on_dblclick.notify(_rwt_mouse_event(op))
        elif op.event == 'Navigation': self.on_navigate.notify(_rwt_mouse_event(op))
        else: return False
        return True 
        
    def _handle_set(self, op):
        for key, value in op.args.iteritems():
            if key == 'bounds':
                self._bounds = map(px, value)
    
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
    
    @bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = map(px, bounds)
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
    
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
    def focus(self):
        session.runtime.windows.focus = self
    
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
    def color(self):
        return self.theme.color


    @color.setter
    @checkwidget
    def color(self, color):
        self.theme.color = parse_value(color, Color)
        session.runtime << RWTSetOperation(self.id, {'foreground': [int(round(v * 255)) for v in [self.theme.color.red, self.theme.color.green, self.theme.color.blue, self.theme.color.alpha]]})


    @property
    def font(self):
        if self._font is not None: return self._font
        else: return self.theme.font

    @font.setter
    @checkwidget
    def font(self, font):
        self._font = font
        session.runtime << RWTSetOperation(self.id, {'font': [font.family, font.size.value, font.bf, font.it]})

    @property
    def css(self):
        return self._css

    @css.setter
    @checkwidget
    def css(self, css):
        self._css = css
        session.runtime << RWTSetOperation(self.id, {'customVariant': 'variant_%s' % css})
        
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

    
    def compute_fringe(self):
        '''
        Computes the fringe of this widget.
        
        The fringe is defined for nonterminal widgets, i.e. widgets that 
        can contain other widgets and denotes the dimensions in x and y 
        directions that are occupied by the parent widget and cannot be
        part of the client area.
        '''
        return px(0), px(0)
    
    
    def viewport(self):
        return px(0), px(0)


class Display(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Display'
    
    @constructor('Display')
    def __init__(self, parent):
        Widget.__init__(self, parent)
        self._cursor_loc = (px(0), px(0))
        
        
    def _handle_set(self, op):
        for k, v in op.args.iteritems():
            if k not in ('cursorLocation', ): Widget._handle_set(self, op) 
            if k == 'cursorLocation': self._cursor_loc = map(px, v)
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
    _defstyle_ = Widget._defstyle_ | RWT.VISIBLE | RWT.ACTIVE

    _logger = pyraplog.getlogger(__name__, level=pyraplog.DEBUG)
    
    @constructor('Shell')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ShellTheme(self, session.runtime.mngr.theme)
        self._title = options.get('title')
        self.on_close = OnClose(self)
        self.on_move = OnMove(self)
    
    def create_content(self):
        self.content = Composite(self)
        self.content.layout = CellLayout(halign='fill', valign='fill')
        self.on_resize += self.dolayout
        
        
    def _handle_notify(self, op):
        if op.event not in ('Close', 'Move'): return Widget._handle_notify(self, op)
        if op.event == 'Close': self.on_close.notify()
        elif op.event == 'Move': self.on_move.notify()
        
        
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
            if self.title is not None:
                options.text = self.title
        if RWT.CLOSE in self.style:
            options.showClose = True
            options.allowClose = True
        options.resizable = (RWT.RESIZE in self.style)
        out(self.style.readable(RWT))
        if RWT.MODAL in self.style:
            options.style.append('APPLICATION_MODAL')
        if RWT.MAXIMIZE in self.style:
            options.showMaximize = True
            options.allowMaximize = True
        if RWT.MINIMIZE in self.style:
            options.showMinimize = True
            options.allowMinimize = True
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        if RWT.CLOSE in self.style:
            self.on_close += self.dispose
        
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
        if m: 
            self._maximize()
#             session.runtime.display.on_resize += self.dolayout
            
        
    @property
    def parent_shell(self):
        p = self.parent
        while True:
            if isinstance(p, Shell): return p
            if not hasattr(p, 'parent'): return None
            p = p.parent

    @property
    def client_rect(self):
        area = [0, 0] + list(self.bounds[2:])
        padding = self.theme.padding
        if padding:
            area[0] += padding.left
            area[2] -= padding.left + padding.right
            area[1] += padding.top
            area[3] -= padding.top + padding.bottom
        if self.title: 
            area[3] -= self.theme.title_height
            area[1] += self.theme.title_height
        top, right, bottom, left = self.theme.borders
        area[0] += ifnone(left, 0, lambda b: b.width)
        area[2] -= ifnone(left, 0, lambda b: b.width) + ifnone(right, 0, lambda b: b.width)
        area[1] += ifnone(top, 0, lambda b: b.width)
        area[3] -= ifnone(top, 0, lambda b: b.width) + ifnone(bottom, 0, lambda b: b.width)
        return area
    
    @checkwidget
    def close(self):
        self.on_close.notify()
    
    def _maximize(self):
        self.bounds = session.runtime.display.bounds
        

    def dolayout(self):
        started = time.time()
        if self.maximized:
            self._maximize()
        x, y, w, h = self.client_rect
        self.content.layout.cell_minwidth = w
        self.content.layout.cell_maxwidth = w
        self.content.layout.cell_minheight = h
        self.content.layout.cell_maxheight = h
        self.content.layout.maxheight = h
        self.content.layout.minheight = h
        self.content.layout.maxwidth = w
        self.content.layout.minwidth = w
        self.content.bounds = x, y, w, h
        layout = LayoutAdapter.create(self.content, None)
        layout.data.cellhpos.set(x)
        layout.data.cellvpos.set(y)
        layout.compute()
        end = time.time()
        self._logger.debug('layout computations took %s sec' % (end - started))
#         layout.write()


    def onresize_shell(self):
        self.dolayout()
        
    def compute_fringe(self):
        width, height = self.compute_size()
        
        


class Combo(Widget):

    _rwt_class_name_ = 'rwt.widgets.Combo'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Combo')
    def __init__(self, parent, items='', editable=True, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ComboTheme(self, session.runtime.mngr.theme)
        self._items = items
        self.on_select = OnSelect(self)
        self._editable = editable
        self._selidx = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.items = self._items
        options.style.append("DROP_DOWN")
        options.editable = self._editable
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)


    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
        for padding in (self.theme.padding, self.theme.itempadding):
            if padding:
                w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
                h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        w += ifnone(self.theme.btnwidth, 0)
        return w, h


    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.iteritems():
            if key == 'selectionIndex':
                self._selidx = value


    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_selection_event(op))
        return True

    @property
    def selected(self):
        return self.items[self._selidx]

    @property
    def items(self):
        return self._items

    @items.setter
    @checkwidget
    def items(self, items):
        self._items = items
        session.runtime << RWTSetOperation(self.id, {'items': self.items})


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
        self._selidx = None
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
        for key, value in op.args.iteritems():
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
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Label')
    def __init__(self, parent, text='', img=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = LabelTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._img = img

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.img: 
            options.image = self._get_rwt_img(self.img)
        else:
            options.text = self.text
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)
        
        
    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width.value, img.height.value]
        else: img = None
        return img
        

    @property
    def img(self):
        return self._img

    @property
    def text(self):
        return self._text
    
    
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
        if self.img is not None:
            w, h = self.img.size
        else:
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h


class Button(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Button'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Button')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = ButtonTheme(self, session.runtime.mngr.theme)
        self.on_select = OnSelect(self)
        self._text = text

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = self.text
        options.style.append('PUSH')
        options.tabIndex = 1
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    @property
    def text(self):
        return self._text
    
    @text.setter
    @checkwidget
    def text(self, text):
        self._text = text
        session.runtime << RWTSetOperation(self.id, {'text': self._text})
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True 
    
    def compute_size(self):
        width, height = Widget.compute_size(self)
        tw, th = session.runtime.textsize_estimate(self.theme.font, self._text)
        width += tw
        height += th
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


    def bind(self, var):
        if not type(var) in (NumVar, BoolVar):
            raise Exception('Can only bind variables of type NumVar and BoolVar')
        self._checked.bind(var)

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
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_checked}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True 

    def _handle_set(self, op):
        for key, value in op.args.iteritems():
            if key == 'selection':
                self._checked.set(value)
    
    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
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


class Option(Widget):
    _rwt_class_name_ = 'rwt.widgets.Button'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Option')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = OptionTheme(self, session.runtime.mngr.theme)    
        self.on_checked = OnSelect(self)
        self._text = str(text()) if callable(text) else str(text)
        self._checked = BoolVar(options.get('checked', False))

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.text = str(self._text()) if callable(self._text) else str(self._text)
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
        else: events[op.event].notify()
        return True 

    def _handle_set(self, op):
        for key, value in op.args.iteritems():
            if key == 'selection':
                self._checked.set(value)

    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
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
                                  'alignleft': RWT.LEFT}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.BORDER | RWT.LEFT)

    @constructor('Edit')
    def __init__(self, parent, text=None, editable=True, message=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = EditTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._message = message
        self._editable = editable
        self._selection = None
        self.on_modify = OnModify(self)
        
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.text:
            options.text = self.text
        if self._message:
            options.message = self._message
        options.editable = self._editable
        if RWT.MULTI in self.style:
            options.style.append('MULTI')
        if RWT.WRAP in self.style:
            options.style.append('WRAP')
        if RWT.LEFT in self.style:
            options.style.append('LEFT')

        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        width, height = Widget.compute_size(self)
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
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
        
    def _handle_notify(self, op):
        events = {'Modify': self.on_modify}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify()
        return True 

    def _handle_set(self, op):
        for key, value in op.args.iteritems():
            if key == 'selection':
                self._selection = value
            if key == 'text':
                self._text = value
        
    
class Composite(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Composite'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Composite')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = CompositeTheme(self, session.runtime.mngr.theme)
        
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)
        
    @Widget.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = map(px, bounds)
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        session.runtime << RWTSetOperation(self.id, {'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})
        
    def compute_size(self):
        return Widget.compute_size(self)
    
    
class ScrolledComposite(Composite):

    _rwt_class_name_ = 'rwt.widgets.ScrolledComposite'
    
    _styles_ = Composite._styles_ + BiMap({'hscroll': RWT.HSCROLL,
                                           'vscroll': RWT.VSCROLL})

    @constructor('ScrolledComposite')
    def __init__(self, parent,**options):
        Widget.__init__(self, parent, **options)
        self.theme = ScrolledCompositeTheme(self, session.runtime.mngr.theme)
        self._content = None
        self._hbar, self._vbar = None, None
        
    def create_content(self):
        if RWT.HSCROLL in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
        if RWT.VSCROLL in self.style:
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        out(self.style)
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
    def __init__(self, parent, tabpos='TOP', **options):
        Widget.__init__(self, parent, **options)
        self.theme = TabFolderTheme(self, session.runtime.mngr.theme)
        self._tabpos = tabpos
        self._items = []
        self.on_select = OnSelect(self)
        self._selected = None
        self._tooltip = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append(self._tabpos)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)

    @Composite.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = map(px, bounds)
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        session.runtime << RWTSetOperation(self.id, {'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})

    @property
    def items(self):
        return self._items

    def remove_item(self, idx):
        self.items.pop(idx).dispose()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    @checkwidget
    def selected(self, item):
        self._selected = item.id
        for i in self.items:
            i.selected = 0
        item.selected = 1
        session.runtime << RWTSetOperation(self.id, {'selection': self._selected})

    @property
    def tooltip(self):
        return self._tooltip

    @tooltip.setter
    @checkwidget
    def tooltip(self, tooltip):
        self._tooltip = tooltip
        session.runtime << RWTSetOperation(self.id, {'toolTip': self._tooltip})


    def compute_size(self):
        width, height = Composite.compute_size(self)
        # content container border
        t, r, b, l = self.theme.container_borders
        width += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        height += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        itemsizes = [i.compute_size() for i in self.items]
        if itemsizes:
            width += max([s[0] for s in itemsizes])
            height += max([s[1] for s in itemsizes])
        return width, height

    
    def compute_fringe(self):
        width, height = self.compute_size()
        itemsizes = [i.compute_size() for i in self.items]
        if itemsizes:
            width -= max([s[0] for s in itemsizes])
        return width, height
    

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
        self._bounds = map(px, bounds)
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        session.runtime << RWTSetOperation(self.id, {'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})

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
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
        width += w
        height += h
        return width, height


class Slider(Widget):
    _rwt_class_name_ = 'rwt.widgets.Slider'
    _styles_ = Widget._styles_ + {'horizontal': RWT.HORIZONTAL,
                                  'vertical': RWT.VERTICAL}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.HORIZONTAL)


    @constructor('Slider')
    def __init__(self, parent, minimum=0, maximum=100, selection=100, increment=1, orientation=RWT.HORIZONTAL, **options):
        Widget.__init__(self, parent, **options)
        self.theme = SliderTheme(self, session.runtime.mngr.theme)
        self.orientation = orientation
        self._minimum = minimum
        self._maximum = maximum
        self._selection = selection
        self._increment = increment
        if self not in parent.children:
            parent.children.append(self)


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.HORIZONTAL in self.style:
            options.style.append('HORIZONTAL')
        if RWT.VERTICAL in self.style:
            options.style.append('VERTICAL')
        options.minimum = self._minimum
        options.maximum = self._maximum
        options.selection = self._selection
        options.increment = self._increment
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)


    @property
    def selection(self):
        return self._selection


    @selection.setter
    @checkwidget
    def selection(self, selection):
        self._selection = selection
        session.runtime << RWTSetOperation(self.id, {'selection': self.selection})


    def compute_size(self):
        width, height = 0, 0
        return width, height


class Group(Composite):
    
    _rwt_class_name_ = 'rwt.widgets.Group'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Group')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = GroupTheme(self, session.runtime.mngr.theme)
        self._text = text
        
        
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
        self._bounds = map(px, bounds)
        session.runtime << RWTSetOperation(self.id, {'bounds': [b.value for b in self.bounds]})
        
    def compute_size(self):
        width, height = Composite.compute_size(self)
        # frame border
        t, r, b, l = self.theme.frame_borders
        width += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        height += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        # frame padding
        padding = self.theme.frame_padding
        if padding:
            width += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            height += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        # frame margin
        margin = self.theme.frame_margin
        if margin:
            width += ifnone(margin.left, 0) + ifnone(margin.right, 0)
            height += ifnone(margin.top, 0) + ifnone(margin.bottom, 0)
        return px(width), px(height)
        
    def compute_fringe(self):
        width, height = self.compute_size()
        return width, height
    
    
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
    def __init__(self, parent, url='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = BrowserTheme(self, session.runtime.mngr.theme)
        self._url = url
        self._FN_TEMPLATE = "(function(){{{}}})();"


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        options.style.append('NONE')
        options.url = self.url
        out(options)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)


    @property
    def url(self):
        return self._url


    @url.setter
    @checkwidget
    def url(self, url):
        self._url = url
        session.runtime << RWTSetOperation(self.id, {'url': self.url})


    def eval(self, fn):
        session.runtime << RWTCallOperation(self.id, 'evaluate', args={'script': self._FN_TEMPLATE.format(fn)})


    def compute_size(self):
        return 0, 0


class Menu(Widget):

    _rwt_class_name = 'rwt.widgets.Menu'
    _styles_ = Widget._styles_ + {'bar': RWT.BAR, 'dropdown': RWT.DROP_DOWN}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.BAR)


    @constructor('Menu')
    def __init__(self, parent, index=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = EditTheme(self, session.runtime.mngr.theme)
        self._index = index
        self._mIndex = 0


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.BAR in self.style:
            options.style.append('BAR')
        if RWT.BAR in self.style:
            options.style.append('DROP_DOWN')
        options.mnemonicIndex = self._mIndex
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)


    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
        return w, h


    def unhide(self):
        session.runtime << RWTCallOperation(self.id, 'unhideItems', {'reveal': True})


class MenuItem(Widget):

    _rwt_class_name = 'rwt.widgets.MenuItem'
    _styles_ = Widget._styles_ + {'cascade': RWT.CASCADE,
                                  'push': RWT.PUSH,
                                  'separator': RWT.SEPARATOR}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.PUSH)


    @constructor('MenuItem')
    def __init__(self, parent, text=None, img=None, index=0, **options):
        Widget.__init__(self, parent, **options)
        self.theme = EditTheme(self, session.runtime.mngr.theme)
        self._text = text
        self._img = img
        self._index = index
        self._menu = None
        self._mIndex = None


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if RWT.PUSH in self.style:
            options.style.append('PUSH')
        if RWT.CASCADE in self.style:
            options.style.append('CASCADE')
        if RWT.SEPARATOR in self.style:
            options.style.append('SEPARATOR')
        options.index = self._index
        if self.text:
            options.text = self.text
        if self.img:
            options.image = self._get_rwt_img(self.img)
        if self._menu:
            options.menu = self._menu.id
        if self._mIndex:
            options.mnemonicIndex = self._mIndex
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)


    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
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


    # ["create", "w296", "rwt.widgets.MenuItem",
    #  {"parent": "w62", "style": ["PUSH"], "index": 0, "text": "Import...",
    #   "mnemonicIndex": 0,
    #   "image": ["rwt-resources/generated/d3074efb.gif", 16, 16]}]



# class Grid(Composite):
#     @constructor('Grid')
#     def __init__(self, columns, parent, **options):
#         Composite.__init__(self, parent, **options)
#         self.layout_settings = GridLayout(columns)
        
 
# class Row(Grid): pass
#  
# class Col(Grid): pass
#  
# class Cell(Grid): pass
#     
