'''
Created on Dec 7, 2016

@author: nyga
'''
import pyrap
from pyrap.dialogs import msg_ok, ask_yesno
from pyrap.ptypes import Color
from pyrap.widgets import Shell, Label, Button, Composite, StackedComposite
from pyrap.layout import CellLayout, GridLayout


class HelloWorld(object):
    '''My pyRAP application'''
    
    def main(self, display, **kwargs):
        shell = Shell(display, title='Hello, pyRAP!', resize=True, btnclose=True, btnmin=True, btnmax=True)
        shell.content.layout = GridLayout(cols=5, equalheights=False, flexcols=2, flexrows=20, halign='fill', valign='fill')
        btn = Button(shell.content, 'This is a pyRAP Button', valign='fill', halign='fill')
        btn.on_select += lambda *_: ask_yesno(shell, 'Welcome to pyRAP', 'This is a pyRAP message!')
        pack = Button(shell.content, 'Pack this shell!')
        pack.on_select += lambda  *_: shell.dolayout(True)
        color = Color('red')
        for i in range(100):
            l = Label(shell.content, str(i+1), halign='fill', valign='fill')
            color = color.brighter(.01)
            l.bg = color
        comp = Composite(shell.content)
        comp.layout = GridLayout(rows=2, halign='center', valign='center', equalheights=True, flexcols=0)
        b = Button(comp, 'Click me!')
        Label(shell.content)
        comp2 = StackedComposite(shell.content)#, halign='fill', valign='fill')

        def sel0(*_):
            comp2.selidx = 0
        b.on_select += sel0
        b = Button(comp, 'Click me!')

        def sel1(*_):
            comp2.selidx = 1

        b.on_select += sel1
        b = Button(comp, 'Click me!')

        def sel2(*_):
            comp2.selidx = 2

        b.on_select += sel2
        b = Button(comp, 'Click')

        def sel3(*_):
            comp2.selidx = 3

        b.on_select += sel3

        # comp2.layout = GridLayout(cols=1)
        Label(comp2, 'hello')
        Label(comp2, 'world')
        Label(comp2, 'HELLO')
        Label(comp2, 'WORLD')
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
