'''
Created on Dec 7, 2016

@author: nyga
'''
import pyrap
from pyrap.dialogs import msg_ok
from pyrap.widgets import Shell, Label
from pyrap.layout import CellLayout, GridLayout


class HelloWorld(object):
    '''My pyRAP application'''
    
    def main(self, display, **kwargs):
        self.shell = Shell(display, title='Hello, pyRAP!', resize=True, btnclose=True, btnmin=True, btnmax=True)
        self.shell.content.layout = GridLayout(cols=20, equalheights=True, equalwidths=True, halign='fill', valign='fill')
        for i in range(100):
            Label(self.shell.content, str(i+1), halign='fill', valign='fill')
        # l2 = Label(self.shell.content, 'center', halign='center', valign='top')
        # l3 = Label(self.shell.content, 'right', halign='right', valign='center')
        self.shell.on_resize += self.shell.dolayout
        # msg_ok(display, 'welcome to pyrap', 'this is a pyrap message')
        self.shell.dolayout()

if __name__ == '__main__':
    pyrap.register_app(clazz=HelloWorld, 
                       entrypoints={'hello': HelloWorld.main},
                       path='hello', 
                       name='My First pyRAP app!',
                       default='hello')
    pyrap.run()
