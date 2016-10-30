'''
Created on Oct 9, 2015

@author: nyga
'''

import mimetypes
import time

import ptypes
from pyrap import pyraplog, locations
from pyrap.base import session
from pyrap.communication import RWTSetOperation,\
    RWTCreateOperation, RWTCallOperation, RWTDestroyOperation
from pyrap.constants import RWT
from pyrap.events import OnResize, OnMouseDown, OnMouseUp, OnDblClick, OnFocus,\
    _rwt_mouse_event, OnClose, OnMove, OnSelect, _rwt_selection_event, OnDispose, \
    OnNavigate, OnModify
from pyrap.exceptions import WidgetDisposedError
from pyrap.layout import Layout, LayoutAdapter, CellLayout,\
    StackLayout
from pyrap.ptypes import px, BitField, BoolVar, NumVar, Color,\
    parse_value
from pyrap.themes import LabelTheme, ButtonTheme, CheckboxTheme, OptionTheme,\
    CompositeTheme, ShellTheme, EditTheme, ComboTheme, TabItemTheme, \
    TabFolderTheme, ScrolledCompositeTheme, ScrollBarTheme, GroupTheme, \
    SliderTheme, DropDownTheme, BrowserTheme, ListTheme, MenuTheme, MenuItemTheme, TableItemTheme, TableTheme, \
    TableColumnTheme, CanvasTheme, ScaleTheme
from pyrap.utils import RStorage, BiMap, out, ifnone, stop


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
        self._zindex = None
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
    #
    # @property
    # def zindex(self):
    #     return self._zindex
    #
    # @zindex.setter
    # @checkwidget
    # def zindex(self, zindex):
    #     self._zindex = zindex


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
                out(session.runtime.windows)
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
        self._selidx = -1

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

    def select(self, idx):
        self._selidx = idx
        session.runtime << RWTSetOperation(self.id, {'selectionIndex': idx, 'text': self.selected})


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
    _styles_ = Widget._styles_ + {'markup': RWT.MARKUP,
                                  'wrap': RWT.WRAP}
    _defstyle_ = BitField(Widget._defstyle_ | RWT.MARKUP)
    
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
    
    
    
class ScrolledComposite(Composite):

    _rwt_class_name_ = 'rwt.widgets.ScrolledComposite'
    
    _styles_ = Composite._styles_ + BiMap({'hscroll': RWT.HSCROLL,
                                           'vscroll': RWT.VSCROLL})

    @constructor('ScrolledComposite')
    def __init__(self, parent,**options):
        Widget.__init__(self, parent, **options)
        self.theme = ScrolledCompositeTheme(self, session.runtime.mngr.theme)
        self._content = None
        self.layout = CellLayout(halign='fill', valign='fill')
        self._hbar, self._vbar = None, None
        
    def create_content(self):
        if RWT.HSCROLL in self.style:
            self._hbar = ScrollBar(self, orientation=RWT.HORIZONTAL)
            self._hbar.visible = True
        if RWT.VSCROLL in self.style:
            self._vbar = ScrollBar(self, orientation=RWT.VERTICAL)
            self._vbar.visible = True
        self.content = Composite(self)


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
        self.layout = StackLayout(halign=self.layout.halign, 
                                  valign=self.layout.valign,
                                  padding_top=self.layout.padding_top,
                                  padding_right=self.layout.padding_right,
                                  padding_bottom=self.layout.padding_bottom,
                                  padding_left=self.layout.padding_left)

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

    @checkwidget
    def addtab(self, title='', img=None, idx=None):
        item = TabItem(self, idx=ifnone(idx, len(self.items)), text=title)
        container = Composite(self)
        container.layout = CellLayout(halign='fill', valign='fill')
        item.control = container
        self.items.append(item)
        return container

    @property
    def items(self):
        return self._items

    def rmitem(self, idx):
        self.items.pop(idx).dispose()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    @checkwidget
    def selected(self, item):
        if type(item) is int:
            item = self.items[item]
        if not isinstance(item, TabItem): raise TypeError('Expected type %s, got %s.' % (TabItem.__name__, type(item).__name__))
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


class Scale(Widget):
    _rwt_class_name_ = 'rwt.widgets.Scale'
    _styles_ = Widget._styles_ + {}
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('Scale')
    def __init__(self, parent, minimum=None, maximum=None, selection=None, inc=None, pageinc=None, orientation=RWT.HORIZONTAL, thumb=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = ScaleTheme(self, session.runtime.mngr.theme)
        self.style |= orientation
        self._minimum = minimum
        self._maximum = maximum
        self._selection = selection
        self._inc = inc
        self._pageinc = pageinc
        self.on_select = OnSelect(self)
#         if self not in parent.children:
#             parent.children.append(self)


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
        return self._pageIncrement

    @pageinc.setter
    @checkwidget
    def pageinc(self, inc):
        self._pageinc = inc
        session.runtime << RWTSetOperation(self.id, {'pageIncrement': self.pageIncrement})

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
        if RWT.HORIZONTAL in self.style:
            h += 9 + 9 # constant vertical offset of the thumb
            w += 2 * 8 # constant horizontal offset of the thumb
        if RWT.VERTICAL in self.style:
            h += 2 * 8 # constant vertical offset of the thumb
            w += 9 + 9 # constant horizontal offset of the thumb
        if self.theme.bgimg is not None and self.theme.bgimg != 'none':
            w += self.theme.bgimg.width.value
            h += self.theme.bgimg.height.value
        # add borders
#         t, r, b, l = self.theme.thumb_borders
#         w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
#         h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h



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
                                  'separator': RWT.SEPARATOR}
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


    def compute_size(self):
        w, h = Widget.compute_size(self)
        if self.text:
            w_, h_ = session.runtime.textsize_estimate(self.theme.font, self.text)
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


    # ["create", "w296", "rwt.widgets.MenuItem",
    #  {"parent": "w62", "style": ["PUSH"], "index": 0, "text": "Import...",
    #   "mnemonicIndex": 0,
    #   "image": ["rwt-resources/generated/d3074efb.gif", 16, 16]}]



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
        self._items = items if items is not None else []
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
        options.items = map(str, self._items)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
        
    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else: events[op.event].notify(_rwt_selection_event(op))
        return True
    
    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.iteritems():
            if key == 'selection':
                self._selidx = value
    
    @Widget.bounds.setter
    def bounds(self, b):
        Widget.bounds.fset(self, b)
        self.setitemheight()

    def setitemheight(self):
        if self.itemheight is None:
            _, h = session.runtime.textsize_estimate(self.theme.font, 'X')
            if self.markup:
                lines = [len(i.split('<br>')) for i in map(str, self.items)]
                if lines:
                    h *= max(lines)
        else:
            h = self.itemheight
        padding = self.theme.item_padding
        if padding:
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        session.runtime << RWTSetOperation(self.id, {'itemDimensions': [self.bounds[2].value, h.value]})

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
    
    @property
    def items(self):
        return self._items
    
    @items.setter
    def items(self, items):
        self._items = items
        session.runtime << RWTSetOperation(self.id, {'items': map(str, self._items)})
        self.setitemheight()
        
    @property
    def selection(self):
        sel = [self.items[i] for i in self._selidx]
        if RWT.MULTI not in self.style: sel = sel[0]
        return sel
    
    @selection.setter
    def selection(self, sel):
        if type(sel) not in (list, tuple) and RWT.MULTI in self.style:
            raise TypeError('Expected list or tuple, got %s' % type(sel))
        if RWT.MULTI not in self.style: sel = [sel]
        sel = [self.items.index(s) for s in sel]
        self.selidx = sel
        
    @property
    def selidx(self):
        return self._selidx
    
    @selidx.setter
    def selidx(self, sel):
        if type(sel) not in (list, tuple) and RWT.MULTI in self.style:
            raise TypeError('Expected list or tuple, got %s' % type(sel))
        if not RWT.MULTI in self.style: sel = [sel]
        session.runtime << RWTSetOperation(self.id, {'selection': sel})
    
    def compute_size(self):
        return 0, 0
    
    def compute_fringe(self):
        return 0, 0


class Table(Widget):

    _rwt_class_name_ = 'rwt.widgets.Grid'

    _styles_ = Composite._styles_ + BiMap({'noscroll': RWT.NOSCROLL,
                                           'single': RWT.SINGLE,
                                           'multi': RWT.MULTI})

    @constructor('Table')
    def __init__(self, parent, markupenabled=False, bgimg=None, indentwidth=0, items=0, itemheight=25, headervisible=True, headerheight=30, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableTheme(self, session.runtime.mngr.theme)
        self._markupenabled = markupenabled
        self._hbar, self._vbar = None, None
        self._bgimg = bgimg
        self._indentwidth = indentwidth
        self._columncount = 0
        self._itemcount = items
        self._itemheight = itemheight
        self._headervisible = headervisible
        self._headerheight = headerheight
        self._colsmoveable = False
        self._columns = []
        self._items = []

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
        options.appearance = 'table'
        options.indentionWidth = self._indentwidth
        options.markupEnabled = self._markupenabled
        options.headerHeight = self._headerheight
        options.itemHeight = self._itemheight
        options.treeColumn = -1
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name_, options)


    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width.value, img.height.value]
        return img

    @property
    def hbar(self):
        return self._hbar

    @property
    def vbar(self):
        return self._vbar

    @property
    def items(self):
        return self._items

    @items.setter
    @checkwidget
    def items(self, items):
        self._items = items

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

    @property
    def itemcount(self):
        return self._itemcount

    @itemcount.setter
    @checkwidget
    def itemcount(self, items):
        self._itemcount = items
        session.runtime << RWTSetOperation(self.id, {'itemCount': items})

    @property
    def itemheight(self):
        return self._itemheight

    @itemheight.setter
    @checkwidget
    def itemheight(self, itemheight):
        self._itemheight = itemheight
        session.runtime << RWTSetOperation(self.id, {'itemheight': itemheight})

    def linesvisible(self, visible):
        session.runtime << RWTSetOperation(self.id, {'linesVisible': visible})

    def backgroundimg(self, imgpath):
        session.runtime << RWTSetOperation(self.id, {'backgroundImage': self._get_rwt_img(self.img)})

    def headervisible(self, visible):
        self._headervisible = visible
        session.runtime << RWTSetOperation(self.id, {'headerVisible': visible})

    def headerheight(self, h):
        self._headerheight = h
        session.runtime << RWTSetOperation(self.id, {'headerHeight': h})

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
        for i, col in enumerate(self.cols):
            col.left = left
            width = col.w
            imgwidth = 0
            for item in self.items:
                imgwidth = max(imgwidth, item.imgwidth(i))

            imgleft = left + col.theme.padding.left.value
            textleft = imgleft + imgwidth
            textwidth = max(0, width - col.theme.padding.left.value - imgwidth)
            metrics.append([col.idx, left, width, imgleft, imgwidth, textleft, textwidth])
            left += width
        session.runtime << RWTSetOperation(self.id, {'itemMetrics': metrics})

    def additem(self, texts, index=None, **options):
        TableItem(self, idx=index, texts=texts, **options)
        self.itemcount = max(self.itemcount, len(self.items))
        self.itemmetrics()

    def addcol(self, text, tooltip=None, **options):
        TableColumn(self, text=text, tooltip=tooltip, **options)
        self.colcount = max(self.colcount, len(self.cols))
        session.runtime << RWTSetOperation(self.id, {'columnOrder': [c.id for c in self._columns]})
        self.itemmetrics()


class TableItem(Widget):

    _rwt_class_name_ = 'rwt.widgets.GridItem'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('TableItem')
    def __init__(self, parent, texts=None, idx=None, images=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableItemTheme(self, session.runtime.mngr.theme)
        self._idx = idx if idx else parent.itemcount
        self._texts = texts
        self._images = images
        if self in parent.children:
            parent.children.remove(self)
        self.parent.items.insert(self._idx, self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if 'style' in options:
            del options['style']
        if 'enabled' in options:
            del options['enabled']
        options.texts = self._texts
        options.index = self.idx
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width.value, img.height.value]
        return img

    @property
    def idx(self):
        return self._idx

    @idx.setter
    @checkwidget
    def idx(self, idx):
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
        w = px(0)
        if self.images:
            if self.images[idx] is not None:
                _, w, _ = self.images[idx]
        return w


    def compute_size(self):
        width, height = Widget.compute_size(self)
        if self.img is not None:
            w, h = self.img.size
        else:
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
        width += w
        height += h

        self.parent.itemmetrics(width, height)
        return width, height


class TableColumn(Widget):

    _rwt_class_name_ = 'rwt.widgets.GridColumn'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('TableColumn')
    def __init__(self, parent, text=None, tooltip=None, width=50, img=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TableColumnTheme(self, session.runtime.mngr.theme)
        self._idx = parent.colcount
        self._text = text
        self._tooltip = tooltip
        self._width = width
        self._img = img
        self._moveable = parent.colsmoveable
        self.on_move = OnMove(self)
        self.on_select = OnSelect(self)

        if parent.cols:
            col = parent.cols[-1]
            self._left = col.left + col.w
        else:
            self._left = 0

        if self in parent.children:
            parent.children.remove(self)
        self.parent.cols.insert(self._idx, self)

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if 'style' in options:
            del options['style']
        if 'enabled' in options:
            del options['enabled']
        options.text = self._text
        options.index = self.idx
        options.width = self._width
        options.left = self._left
        options.moveable = self._moveable

        if self._tooltip:
            options.toolTip = self._tooltip
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)

    def _get_rwt_img(self, img):
        if img is not None:
            res = session.runtime.mngr.resources.registerc(img.filename, 'image/%s' % img.fileext, img.content)
            img = [res.location, img.width.value, img.height.value]
        return img

    def _handle_call(self, op):
        if op.method == 'move': self.mv(op.args)

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
    def w(self):
        return self._width

    @w.setter
    @checkwidget
    def w(self, width):
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

    def imgwidth(self):
        if self.img:
            _, w, _ = self._get_rwt_img(self.img)
        else:
            w = 0
        return w

    def compute_size(self):
        width, height = Widget.compute_size(self)
        if self.img is not None:
            w, h = self.img.size
        else:
            w, h = session.runtime.textsize_estimate(self.theme.font, self._text)
        width += w
        height += h
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
        
    
    def __init__(self, _id, parent):
        self.id = _id
        self.parent = parent
        
    def _create_rwt_widget(self):
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, {'parent': self.parent.id})
    
    def init(self, width, height):
        session.runtime << RWTCallOperation(self.id, 'init', {'width': width, 
                                                              'height': height,
                                                              'font': [['Verdana', 'Helvetica', 'sans-serif'], 14, False, False],
                                                              'fillStyle': [0, 255, 255, 255],
                                                              'strokeStyle': [74, 74, 74, 255]})
        
    def draw(self, operations):
        '''Sends the drawing operations to the client.
        Must be a list of :class:`pyrap.GC.Operation` objects.'''
        session.runtime << RWTCallOperation(self.id, 'draw', {'operations': [o.json() for o in operations]})
        
        

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
        
        
    @Widget.bounds.setter
    def bounds(self, b):
        Widget.bounds.fset(self, b)
        self.gc.init(b[2].value, b[3].value)
        self.gc.draw(self.operations)
