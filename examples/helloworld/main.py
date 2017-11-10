'''
Created on Dec 7, 2016

@author: nyga
'''
import pyrap
from pyrap.dialogs import msg_ok
from pyrap.ptypes import Color
from pyrap.widgets import Shell, Label, Button, Composite
from pyrap.layout import CellLayout, GridLayout


class HelloWorld(object):
    '''My pyRAP application'''
    
    def main(self, display, **kwargs):
        shell = Shell(display, title='Hello, pyRAP!', resize=True, btnclose=True, btnmin=True, btnmax=True)
        shell.content.layout = GridLayout(cols=10, equalheights=True, flexcols=0, halign='fill', valign='fill')
        btn = Button(shell.content, 'This is a pyRAP Button', valign='fill', halign='fill')
        btn.on_select += lambda *_: msg_ok(display, 'welcome to pyrap', 'this is a pyrap message')
        pack = Button(shell.content, 'Pack this shell!')
        pack.on_select += lambda  *_: shell.dolayout(True)
        color = Color('red')
        for i in range(100):
            l = Label(shell.content, str(i+1), halign='fill', valign='fill')
            color = color.brighter(.01)
            l.bg = color
        comp = Composite(shell.content)
        comp.layout = GridLayout(rows=2, halign='fill', valign='fill', flexrows=0, flexcols=0)
        Button(comp, 'Click me!')
        Button(comp, 'Click me!')
        Button(comp, 'Click me!')
        Button(comp, 'Click me!')
        # l2 = Label(self.shell.content, 'center', halign='center', valign='top')
        # l3 = Label(self.shell.content, 'right', halign='right', valign='center')
        shell.on_resize += shell.dolayout
        # msg_ok(display, 'welcome to pyrap', 'this is a pyrap message')
        shell.dolayout(True)

if __name__ == '__main__':
    pyrap.register_app(clazz=HelloWorld, 
                       entrypoints={'hello': HelloWorld.main},
                       path='hello', 
                       name='My First pyRAP app!',
                       default='hello')
    pyrap.run()
