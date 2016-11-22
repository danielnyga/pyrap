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


def ask_yesnocancel(parent, title, text):
    msg = MessageBox(parent, title, text, DLG.QUESTION)
    msg.bounds = (100, 100, 400, 200)
    msg.dolayout()
    current_thread().setsuspended()
    msg.on_close.wait()
    return msg.answer
    

class MessageBox(Shell):
    '''
    Represents a simple message box.
    '''
    
    @constructor('MessageBox')    
    def __init__(self, parent, title, text, icon=None):
        Shell.__init__(self, parent, title=title, titlebar=True, border=True, 
                       btnclose=True, resize=True)
        self.icontheme = DisplayTheme(self, pyrap.session.runtime.mngr.theme)
        self.text = text
        self.icon = {DLG.INFORMATION: self.icontheme.icon_info,
                     DLG.QUESTION: self.icontheme.icon_question,
                     DLG.WARNING: self.icontheme.icon_warning,
                     DLG.ERROR: self.icontheme.icon_error}.get(icon)
        self.answer = None
        
    def create_content(self):
        Shell.create_content(self)
        self.content.layout = ColumnLayout()
        img = None
        if self.icon is not None:
            img = Label(self.content, img=self.icon, valign='top', halign='left')
            
        textarea = Composite(self.content)
        textarea.layout = RowLayout()
        text = Label(textarea, self.text, halign='left')
        
        buttons = Composite(textarea)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right', valign='bottom')
        def answer_and_close(a):
            self.answer = a
            self.close()
            
        yes = Button(buttons, text='Yes', halign='fill')
        yes.on_select += lambda *_: answer_and_close('yes') 
        no = Button(buttons, text='No', halign='fill')
        no.on_select += lambda *_: answer_and_close('no')
        cancel = Button(buttons, text='Cancel', halign='fill')
        cancel.on_select += lambda *_: answer_and_close(None)
        
            
        
        