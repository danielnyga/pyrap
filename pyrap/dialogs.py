'''
Created on Nov 21, 2016

@author: nyga
'''
from pyrap.widgets import Shell, constructor, Label, Composite, Button
from pyrap.themes import DisplayTheme
import pyrap
from pyrap.constants import DLG
from pyrap.layout import ColumnLayout, RowLayout
from pyrap.utils import out
from threading import current_thread
from pyrap.ptypes import px
from pyrap.threads import sleep


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
    def __init__(self, parent, title, text, icon=None, modal=True):
        Shell.__init__(self, parent, title=title, titlebar=True, border=True, 
                       btnclose=True, resize=False, modal=modal)
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
            
        
        