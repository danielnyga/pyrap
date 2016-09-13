'''
Created on Oct 9, 2015

@author: nyga
'''
from pyrap.communication import RWTListenOperation, RWTSetOperation,\
    RWTCreateOperation, RWTCallOperation, RWTDestroyOperation
from pyrap.types import Event, px, BitField, BitMask, BoolVar, NumVar, Color,\
    parse_value, Var, VarCompound, BoundedDim, pc
from pyrap.base import session
from pyrap.utils import RStorage, BiMap, out, ifnone, pparti, stop
from pyrap.events import OnResize, OnMouseDown, OnMouseUp, OnDblClick, OnFocus,\
    _rwt_mouse_event, OnClose, OnMove, OnSelect, _rwt_selection_event, OnDispose, \
    OnNavigate
from pyrap.exceptions import WidgetDisposedError, LayoutError, ResourceError
from pyrap.constants import RWT, inf
from pyrap.themes import LabelTheme, ButtonTheme, CheckboxTheme, OptionTheme,\
    CompositeTheme, ShellTheme, EditTheme, ComboTheme, TabItemTheme, \
    TabFolderTheme, GroupTheme
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
            self.layout.padding_left = d['padding_right']
        if 'padding_bottom' in d:
            self.layout.padding_left = d['padding_bottom']
        if 'padding_top' in d:
            self.layout.padding_left = d['padding_top']
        
        
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
        return ifnone(self._css, 'csscclass')

    @css.setter
    @checkwidget
    def css(self, css):
        self._css = css
        session.runtime << RWTSetOperation(self.id, {'customVariant': 'variant_%s' % css, 'active': True, 'visibility': True, 'mode': 'maximized'})


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
#         self.content.bg = Color('red')
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
        options.children = None
        options.tabIndex = 8
        options.editable = self._editable
        session.runtime << RWTCreateOperation(id_=self.id, clazz=self._rwt_class_name_, options=options)


    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'X')
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
        width, height = session.runtime.textsize_estimate(self.theme.font, self._text)
        padding = self.theme.padding
        if padding:
            width += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            height += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        top, right, bottom, left = self.theme.borders
        width += ifnone(left, 0, lambda b: b.width) + ifnone(right, 0, lambda b: b.width)
        height += ifnone(top, 0, lambda b: b.width) + ifnone(bottom, 0, lambda b: b.width)
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
                self._checked = value

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
    _defstyle_ = BitField(Widget._defstyle_ | RWT.BORDER)
    
    @constructor('Edit')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = EditTheme(self, session.runtime.mngr.theme)
        
    
    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)
    
    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
        if self.theme.padding:
            w += self.theme.padding.left + self.theme.padding.right
            h += self.theme.padding.top + self.theme.padding.bottom
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h 
        
    
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
        return 0, 0



class TabFolder(Widget):

    _rwt_class_name_ = 'rwt.widgets.TabFolder'
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('TabFolder')
    def __init__(self, parent, style='TOP', **options):
        Widget.__init__(self, parent, **options)
        self.theme = TabFolderTheme(self, session.runtime.mngr.theme)
        self._style = style


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


    @property
    def style(self):
        return self._style


    @style.setter
    @checkwidget
    def style(self, style):
        self._style = style
        session.runtime << RWTSetOperation(self.id, {'style': [self._style]})

    def compute_size(self):
        return 0, 0


class TabItem(Widget):

    _rwt_class_name_ = 'rwt.widgets.TabItem'
    _defstyle_ = BitField(Widget._defstyle_)


    @constructor('TabItem')
    def __init__(self, parent, idx=None, text=None, img=None, tooltip=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = TabItemTheme(self, session.runtime.mngr.theme)
        self._idx = idx
        self._text = text + idx
        self._tooltip = tooltip
        self._img = img


    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self.img:
            options.image = self._get_rwt_img(self.img)
        if self.text:
            options.text = self.text
        if self.tooltip:
            options.toolTip = self.tooltip
        if self.idx:
            options.index = self.index
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


    def compute_size(self):
        return 0, 0
    
    
class Group(Widget):
    
    _rwt_class_name_ = 'rwt.widgets.Group'
    _defstyle_ = BitField(Widget._defstyle_)
    
    @constructor('Group')
    def __init__(self, parent, text='', **options):
        Widget.__init__(self, parent, **options)
        self.theme = GroupTheme(self, session.runtime.mngr.theme)
        self._text = text
        
        
    def _create_rwt_widget(self):
        options = Composite._rwt_options(self)
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
        session.runtime << RWTSetOperation(self.id, {'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})
        
    def compute_size(self):
        return 0, 0
    
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
        
    