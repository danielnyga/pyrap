'''
Created on Nov 21, 2016

@author: nyga
'''
from collections import OrderedDict

import pyrap
from pyrap.base import session
from pyrap.constants import DLG
from pyrap.engine import PushService
from pyrap.layout import ColumnLayout, RowLayout, CellLayout
from pyrap.ptypes import px, BoolVar, Font
from pyrap.themes import DisplayTheme
from pyrap.threads import DetachedSessionThread
from pyrap.widgets import Shell, constructor, Label, Composite, Button,\
    ProgressBar, StackedComposite, checkwidget, Checkbox, ScrolledComposite, \
    Option


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

def options_list(parent, options):
    msg = OptionsDialog(parent, options)
    msg.dolayout()
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


class OptionsDialog(Shell):
    '''
    Represents a simple dialog box providing a list of options to the user.
    '''


    @constructor('OptionsDialog')
    def __init__(self, parent, options):
        Shell.__init__(self, parent, titlebar=False, border=True, resize=False, modal=True)
        self.icontheme = DisplayTheme(self, pyrap.session.runtime.mngr.theme)
        self.answer = None
        self._options = None
        self._setoptions(options)

    def answer_and_close(self, a):
        self.answer = a
        self.close()

    def _setoptions(self, options):
        if options is None:
            options = []
        if isinstance(options, dict):
            if not all([type(i) is str for i in options]):
                raise TypeError('All keys in an item dictionary must be strings.')
            if type(options) is dict:
                options = OrderedDict(((k, options[k]) for k in sorted(options)))
        elif type(options) in (list, tuple):
            options = OrderedDict(((str(i), i) for i in options))
        else: raise TypeError('Invalid type for List items: %s' % type(options))
        self._options = options

    def create_content(self):
        Shell.create_content(self)

        # calculate and set options field size
        maxitemwidth, _ = session.runtime.textsize_estimate(Font(family='Verdana, "Lucida Sans", Arial, Helvetica, sans-serif', size=14), sorted(self.options.keys(), key=len)[-1])
        itemheight = 41
        w = self.parent.width - px(40)
        h = min(itemheight * len(self.options) + 10, self.parent.height - px(40))
        vscroll = h == self.parent.height - px(40)
        hscroll = maxitemwidth > self.parent.width - px(40)
        self.bounds = self.parent.width / 2 - w / 2, self.parent.height / 2 - h / 2, w, h
        mainarea = ScrolledComposite(self.content, padding=px(40), hscroll=hscroll, vscroll=vscroll)
        mainarea.content.layout = CellLayout(halign='fill', valign='fill')

        optionslist = Composite(mainarea.content)
        optionslist.layout = RowLayout(halign='fill', valign='fill', equalheights=True)

        self.create_options(optionslist)

    def create_options(self, parent):
        for c in parent.children:
            c.dispose()
        for option in self.options:
            tmp = Option(parent, text=option, halign='left', valign='fill')
            tmp.on_checked += lambda x: self.answer_and_close([session.runtime.windows[x.widget].text, self.options[session.runtime.windows[x.widget].text]])

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._setoptions(options)


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
        
        
        