'''
Created on Nov 21, 2016

@author: nyga
'''
from pyrap.widgets import Shell, constructor, Label, Composite, Button,\
    ProgressBar, StackedComposite, checkwidget, Checkbox, Spinner, Edit,\
    Separator, Canvas
from pyrap.themes import DisplayTheme
import pyrap
from pyrap.constants import DLG, CURSOR
from pyrap.layout import ColumnLayout, RowLayout, StackLayout, GridLayout,\
    CellLayout
from pyrap.utils import out, ifnone
from threading import current_thread
from pyrap.ptypes import px, BoolVar, parse_value, Color, Image
from pyrap.threads import sleep, SessionThread, DetachedSessionThread
from pyrap.base import session
from pyrap.engine import PushService
import os


def msg_box(parent, title, text, icon):
    msg = MessageBox(parent, title, text, icon)
    msg.dolayout(True)
    msg.on_close.wait()
    return msg.answer
    
def ask_question(parent, title, text, buttons):
    msg = QuestionBox(parent, title, text, buttons, DLG.QUESTION)
    msg.dolayout(True)
    msg.on_close.wait()
    return msg.answer

def ask_yesnocancel(parent, title, text):
    return ask_question(parent, title, text, ['yes', 'no', 'cancel'])

def ask_yesno(parent, title, text):
    return ask_question(parent, title, text, ['yes', 'no'])

def ask_okcancel(parent, title, text):
    return ask_question(parent, title, text, ['ok', 'cancel'])

def msg_ok(parent, title, text):
    return msg_box(parent, title, text, DLG.INFORMATION)

def msg_warn(parent, title, text):
    return msg_box(parent, title, text, DLG.WARNING)

def msg_err(parent, title, text):
    return msg_box(parent, title, text, DLG.ERROR)
    

class MessageBox(Shell):
    '''
    Represents a simple message box.
    '''
    
    @constructor('MessageBox')    
    def __init__(self, parent, title, text, icon=None, modal=True, resize=False, btnclose=True):
        Shell.__init__(self, parent, title=title, titlebar=True, border=True, 
                       btnclose=btnclose, resize=resize, modal=modal)
        self.icontheme = DisplayTheme(self, pyrap.session.runtime.mngr.theme)
        self.text = text
        self.icon = {DLG.INFORMATION: self.icontheme.icon_info,
                     DLG.QUESTION: self.icontheme.icon_question,
                     DLG.WARNING: self.icontheme.icon_warning,
                     DLG.ERROR: self.icontheme.icon_error}.get(icon)
        self.answer = None
        
    def answer_and_close(self, a):
        self.answer = a
        self.close()
        
    def create_content(self):
        Shell.create_content(self)
        mainarea = Composite(self.content)
        mainarea.layout = ColumnLayout(padding=10, hspace=5)
        img = None
        if self.icon is not None:
            img = Label(mainarea, img=self.icon, valign='top', halign='left')
            
        textarea = Composite(mainarea)
        textarea.layout = RowLayout()
        text = Label(textarea, self.text, halign='left')
        
        buttons = Composite(textarea)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right', valign='bottom')
        self.create_buttons(buttons)
        
    def create_buttons(self, buttons):
        ok = Button(buttons, text='OK', minwidth=100)
        ok.on_select += lambda *_: self.answer_and_close('ok')
        

class QuestionBox(MessageBox):
    
    @constructor('QuestionBox')
    def __init__(self, parent, title, text, buttons, modal=True):
        MessageBox.__init__(self, parent, title, text, icon=DLG.QUESTION)
        self.buttons = buttons
    
    def create_buttons(self, buttons):
        if 'ok' in self.buttons:
            ok = Button(buttons, text='OK', minwidth=100)
            ok.on_select += lambda *_: self.answer_and_close('ok')
        if 'yes' in self.buttons:
            yes = Button(buttons, text='Yes', halign='fill')
            yes.on_select += lambda *_: self.answer_and_close('yes')
        if 'no' in self.buttons: 
            no = Button(buttons, text='No', halign='fill')
            no.on_select += lambda *_: self.answer_and_close('no')
        if 'cancel' in self.buttons:
            cancel = Button(buttons, text='Cancel', halign='fill')
            cancel.on_select += lambda *_: self.answer_and_close(None)
            
            
def open_progress(parent, title, text, target, autoclose=False):
    dlg = ProgressDialog(parent, title, text, target, modal=0, autoclose=autoclose)
    dlg.dolayout(True)
    dlg.start()
            
class ProgressDialog(MessageBox):
    
    @constructor('ProgressDialog')
    def __init__(self, parent, title, text, target, modal=True, autoclose=False):
        MessageBox.__init__(self, parent, title, text, icon=DLG.INFORMATION, resize=1, modal=modal, btnclose=0)
        self._primary = None
        self._secondary = None
        self._bars = None
        self._max = 100
        if isinstance(target, DetachedSessionThread):
            self._target = target
        else:
            self._target = DetachedSessionThread(target=target, args=(self,))
        self.push = PushService()
        self.autoclose = BoolVar(autoclose)
        
    def setloop(self, show):
        self._bars.selection = self._secondary if show else self._primary
        
    @property
    def max(self):
        self._primary.max
    
    @max.setter
    def max(self, m):
        self._primary.max = m
    
    @property
    def status(self):
        return self.text.text
    
    def inc(self):
        self._primary.value = self._primary.value + 1
    
    @status.setter
    @checkwidget
    def status(self, msg):
        self.text.text = msg 
    
    def start(self):
        self.push.start()
        self._target.start()
        
    def setfinished(self):
        self.push.stop()
        self._btncancel.on_select -= self.terminate_and_close
        self._btncancel.text = 'Close'
        self._btncancel.on_select += lambda *_: self.close()
        if self.autoclose: self.close()
        
        
    def terminate_and_close(self, *_):
        self.setloop(1)
        self.status = 'Terminating...'
        self._target.interrupt()
        self._target.join()
        self.close()
        
    def create_content(self):
        Shell.create_content(self)
        mainarea = Composite(self.content)
        mainarea.layout = ColumnLayout(padding=10, hspace=5)
        if self.icon is not None:
            Label(mainarea, img=self.icon, valign='top', halign='left')
        
        textarea = Composite(mainarea)
        textarea.layout = RowLayout()
        self.text = Label(textarea, self.text, halign='left')
        
        self._bars = StackedComposite(textarea, halign='fill', valign='fill')
        self._primary = ProgressBar(self._bars, horizontal=True, vmax=100, halign='fill', minwidth=500)
        self._secondary = ProgressBar(self._bars, horizontal=True, infinite=True, vmax=100, halign='fill')
        self._bars.selection = 0
        
        buttons = Composite(textarea)
        buttons.layout = ColumnLayout(halign='right', valign='bottom')
        
        cb = Checkbox(buttons, text='close when done')
        cb.bind(self.autoclose) 
        
        self._btncancel = Button(buttons, text='Cancel', halign='fill')
        self._btncancel.on_select += self.terminate_and_close
        
        self.on_resize += self.dolayout
        

def ask_color(parent, modal=True, color=None):
    dlg = ColorDialog(parent, color)
    dlg.dolayout(True)
    dlg.on_close.wait()
    return dlg._color
    

class ColorDialog(Shell):
    PALETTE = Color.names
    
    @constructor('ColorDialog')    
    def __init__(self, parent, color=None, modal=True, resize=False, btnclose=True):
        Shell.__init__(self, parent, title='Choose Color', titlebar=True, border=True, 
                       btnclose=btnclose, resize=resize, modal=modal)
        self._color = parse_value(ifnone(color, 'red'), default=Color)
        
    def setcolor(self, c):
        self.red.selection = c.redi
        self.green.selection = c.greeni
        self.blue.selection = c.bluei
        self.hue.selection = c.huei
        self.saturation.selection = c.saturationi
        self.value.selection = c.valuei
        self.html.text = c.htmla
        self.alpha.selection = c.alphai
        self._redraw(c)
        self._color = c
    
    def _getcolor(self, src):
        if src == 'rgb':
            return Color(rgb=(self.red.asfloat(self.red.selection) / 255,
                         self.green.asfloat(self.green.selection) / 255,
                         self.blue.asfloat(self.blue.selection) / 255),
                         alpha=self.alpha.asfloat(self.alpha.selection) / 255)
        elif src == 'html':
            return Color(html=self.html.text)
        elif src == 'hsv':
            return Color(hsv=(self.hue.asfloat(self.hue.selection) / 255,
                         self.saturation.asfloat(self.saturation.selection) / 255,
                         self.value.asfloat(self.value.selection) / 255), 
                         alpha=self.alpha.asfloat(self.alpha.selection) / 255)
    
    
    def _redraw(self, c):
        with self.selection.gc as gc:
            s = self.selection
            s << gc.begin_path()
            r = (0, 0, 90, 90)
            s << gc.erase(*r)
            s << gc.rect(*r)
            s << gc.fill_style(c)
            s << gc.fill()
        self.selection.draw()
        
    
    def create_content(self):
        Shell.create_content(self)
        
        outer = Composite(self.content)
        outer.layout = RowLayout(padding=10, vspace=5)
        
        main = Composite(outer)
        main.layout = ColumnLayout(padding=10, hspace=20)
        
        left = Composite(main)
        left.layout = RowLayout(valign='fill', flexrows=1)
        
        h = Label(left, 'Preview:', halign='left', padding_left=0)
        h.font = h.font.modify(bf=1)
        
        selection_bg = Composite(left)
        selection_bg.bgimg = Image(os.path.join(pyrap.locations.rc_loc, 'static', 'image', 'bgtransp.png'))
        selection_bg.layout = CellLayout(halign='fill', valign='top')
        self.selection = Canvas(selection_bg, minwidth=90, minheight=90)
        self.selection.bg = 'transp'
        
        right = Composite(main)
        right.layout = RowLayout()

        h = Label(right, 'Color Values:', halign='left')
        h.font = h.font.modify(bf=1)
                
        values = Composite(right)
        values.layout = GridLayout(rows=3)
        
        Label(values, 'Hue:', halign='left')
        self.hue = Spinner(values, vmin=0, vmax=255)
        self.hue.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))
        
        Label(values, 'Red:', halign='left')
        self.red = Spinner(values, vmin=0, vmax=255)
        self.red.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))
        
        Label(values, 'Saturation:', halign='left')
        self.saturation = Spinner(values, vmin=0, vmax=255)
        self.saturation.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))
        
        Label(values, 'Green:', halign='left')
        self.green = Spinner(values, vmin=0, vmax=255)
        self.green.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))
        
        Label(values, 'Value:', halign='left')
        self.value = Spinner(values, vmin=0, vmax=255)
        self.value.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))
        
        Label(values, 'Blue:', halign='left')
        self.blue = Spinner(values, vmin=0, vmax=255)
        self.blue.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))
        
        addvals = Composite(right)
        addvals.layout = GridLayout(cols=2, halign='left')
        
        Label(addvals, 'Hex:', halign='left')
        self.html = Edit(addvals, minwidth=100)
        def html_focusout(focus):
            if focus.lost:
                self.setcolor(self._getcolor('html'))
        self.html.on_focus += html_focusout 
        
        Label(addvals, 'Alpha:', halign='left')
        self.alpha = Spinner(addvals, vmin=0, vmax=255, minwidth=100)
        self.alpha.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))
        
        Separator(right, horizontal=1, halign='fill')
        
        h = Label(right, 'Palette:', halign='left')
        h.font = h.font.modify(bf=1)
        
        palette = Composite(right)
        palette.layout = GridLayout(rows=2, equalwidths=True, equalheights=True)
        
        colors_ = set()
        for name, val in ColorDialog.PALETTE.iteritems():
            if val not in colors_:
                colors_.add(val)
            else: continue
            l = Label(palette, minwidth=30, minheight=20, border=True)
            l.tooltip = '%s (%s)' % (name, val.upper())
            l.bg = Color(val)
            l.cursor = CURSOR.POINTER
            def setcol(event):
                self.setcolor(event.widget.bg)
            l.on_mousedown += setcol
        
        self.setcolor(self._color)
        
        Separator(outer, horizontal=1, halign='fill')
        
        buttons = Composite(outer)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right')
        
        ok = Button(buttons, text='OK', halign='fill')
        ok.on_select += lambda *_: self.close()
        
        
        cancel = Button(buttons, text='Cancel', halign='fill')
        def docancel(*_):
            self._color = None
            self.close()
        cancel.on_select += docancel
        
        