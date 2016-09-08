'''
Created on Oct 2, 2015

@author: nyga
'''

import pyrap
from pyrap.widgets import Label, Button, RWT, Shell, Checkbox, Option, Composite,\
    Edit
import random
from pyrap import pyraplog, locations
from pyrap.utils import out
from pyrap.types import BoolVar, StringVar, Color, px, Image
from pyrap.layout import GridLayout, RowLayout, CellLayout, ColumnLayout
import os


class MyApplication():
    
    def __init__(self):
        self.clicks = 0
    
    @staticmethod
    def setup(application): pass
#         application.resources.registerc('values.csv', 'text/csv', 'x;y;z')
#         application.resources.registerc('values.txt', 'text/plain', 'this is some prosa!')

    def desktop(self, parent, **kwargs):
        self.mainwnd = parent
#         parent.layout.minwidth = parent.layout.maxwidth = 768
        frame = Composite(parent)
        frame.layout = ColumnLayout(flexcols={1: 1}, halign='fill', valign='fill',
                                    padding_left=0, padding_top=0)
        
        logo = Label(frame, img=Image('/home/nyga/beny/beny_logo.png'), valign='top')
        
        container = Composite(frame)
        container.layout = GridLayout(cols=2, valign='fill', halign='left', #flexcols={0:1},
                                      padding_right=0, padding_left=0, padding_bottom=0,
                                      padding_top=0, hspace=0, vspace=5)
        container.layout.flexrows[1] = .1
        container.layout.flexrows[2] = .2
#         container.layout.flexcols[0] = .1
#         container.layout.minwidth = 800
#         containar.laytou_settings.hoffset
        container.layout.maxwidth = px(50)
        
        comp = Composite(container)
        comp.layout = GridLayout(rows=2, squared=1)
        comp.layout.halign = 'center'
        comp.layout.valign = 'center'
#         comp.layout.flexcols[0] = 1
#         comp.layout.flexrows[0] = 1
#         container.bg = Color('blue')
        def click(d):
            if d.button == 1:
                comp.bg = comp.bg.darker()
            elif d.button == 3:
                comp.bg = comp.bg.brighter()
        comp.on_mousedown += click   
        
        self.label = Label(comp, text='PYRAP!', border=False)
        Label(comp, text='2', border=True, halign='fill', valign='center')
        Label(comp, text='bla', border=True, halign='fill', valign='center')
        Label(comp, img=Image(os.path.join(locations.rc_loc, 'widget', 'rap', 'display', 'loading.gif')), border=False, halign='center', valign='center')
        
        self.tick = BoolVar(track=True)
        some_text = StringVar('This is my text!', track=True)
        
        
        self.btn = Button(container, text='Click me, %s, one more time!' % kwargs.get('name', 'Baby'), halign='left', valign='bottom')
        self.btn.on_select += self.show_dlg
        
        cell = Composite(container)
        cell.layout = GridLayout(cols=2)
        cell.layout.valign = 'center'
        cell.layout.halign = 'center'
        cell.layout.padding_right = px(50)
        cell.layout.padding_left = px(50)
#         cell.layout.hspace = px(0)
#         cell.layout.flexcols[0] = 1
#         cell.layout.flexrows[0] = 1
        cell.bg = Color('blue')

        self.check = Checkbox(cell, text='this is a checkbox', checked=True, valign='center', halign='left')
        self.check.on_checked += lambda *_: out('check' if self.check.checked else 'uncheck')
        self.check.bind(self.tick)
        def disable(*_):
            self.check.enabled = not self.check.enabled
        self.tick.on_change += disable 
        
        Label(cell, text='Another label')
        Label(cell, text='yet another label.')
        Label(cell, text='one more')
        
        self.radio = Option(container, text=some_text, valign='bottom', halign='right')
        self.radio.bg = Color('green')
        self.radio.on_mousedown += lambda a: out('mouse down at: %s' % str(a.location)) or self.tick.set(not self.tick)
        yellow = Color('#ffff00')
        Label(container, halign='fill', valign='fill').bg = yellow
        Label(container, halign='fill').bg = yellow.darker().darker()
        
        Label(container, 'First Name:', halign='right', valign='center')
        self.edit_name = Edit(container, halign='right')
        self.edit_name.layout.minwidth = px(100)
        
        Label(container, 'Last Name:', halign='right', valign='center')
        self.edit_name = Edit(container, halign='right')
        self.edit_name.layout.minwidth = px(100)
        
        grid = Composite(container)
        grid.layout = GridLayout(rows=5, halign='center', squared=True, vspace=0, hspace=0)
        green = Color('#32A732')
#         Label(grid, halign='center', valign='center', minwidth=20, minheight=20).bg = green = green.darker()
        for _ in range(25):
            Label(grid, halign='fill', valign='fill').bg = green = green.darker()
        
        cols = Composite(container, border=1)
        cols.layout = RowLayout(halign='center', valign='top')
        cols.layout.flexcols[1] = 1
        Label(cols, 'Hi, there!')
        Label(cols, 'We are in a column!')
        Label(cols, 'We are in a column!')
        Label(cols, 'We are in a column!')
        Label(cols, 'We are in a column!')
        
        Composite(container, halign='fill', valign='fill').bg = '#1E90FF'
        
        rows = Composite(container)
        rows.layout = ColumnLayout(halign='left', equalwidths=1)
        Label(rows, 'We are in a row, man!')
        Label(rows, 'man!')
        Label(rows, 'We are in a row, man!')
        Label(rows, 'We are in a row, man!')
        Label(rows, 'We are in a row, man!')
        
        self.prev = Button(container, '<', enabled=self.tick.canundo)
        
        def undo(*_):
            self.tick.canundo and self.tick.undo()
        def enable_undo(*_): self.prev.enabled = self.tick.canundo
        self.prev.on_select += undo 
        self.tick.on_change += enable_undo
        
        self.next = Button(container, '>', enabled=self.tick.canredo )
        def redo(*_): self.tick.canredo and self.tick.redo()
        self.next.on_select += redo
        def enable_redo(*_): self.next.enabled = self.tick.canredo
        self.tick.on_change += enable_redo
        self.check.on_focus += lambda f: out('i got the focus :-)' if f.gained else 'now i lost it :-(')
        self.check.focus()
        
    def show_dlg(self, data):
        dlg = Shell(self.mainwnd, title='This is a pyrap dialog window', border=True, 
                    titlebar=True, btnclose=True, resize=True, modal=True, btnmax=True)
        dlg.on_resize += lambda *_: out('dialog resized')
        dlg.bounds = self.mainwnd.width / 2 - 150, self.mainwnd.height / 2 - 100, 300, 200
        l = Label(dlg, 'checked: %s, ticked: %s' % (self.check.checked, self.tick))
        l.on_dblclick += lambda d: d.ctrl and out('dbl click at %s' % str(l.cursor_loc))
        l.bounds = 0, 50, 200, 20
        
    def onclick(self, *args):
        self.clicks += 1
        self.label.text = 'clicks: %d, from IP: %s' % (self.clicks, pyrap.session.ip)
        b = self.label.bounds
        self.label.bounds = (b[0] + random.randint(-5, 5), b[1] + random.randint(-5, 5), b[2], b[3])
        
    def mobile(self, parent, **kwargs):
        checkboxes = Composite(parent)
        self.label = Label(checkboxes, text='Hello, PYRAP! You are using the Mobile App.', valign='top', halign='left')
        checkboxes.layout = RowLayout(padding_left=px(50), vspace=20)
        Checkbox(checkboxes, 'my first option', checked=0, halign='left')
        Checkbox(checkboxes, 'my second option', checked=0,halign='left')
        Checkbox(checkboxes, 'my third option', checked=0,halign='left')
        
        Button(checkboxes, 'Submit')
#         self.label.layout.halign = 'center'
#         self.label.layout.valign = 'fill'
#         self.visible = True
#         parent.on_mousedown += self.onclick



if __name__ == '__main__':
    pyraplog.level(pyraplog.DEBUG)
    pyrap.register_app(clazz=MyApplication, path='myapp', name='PyRAP Demo Application', entrypoints={'desktop': MyApplication.desktop,
                                                                                          'mobile': MyApplication.mobile}, 
                       setup=MyApplication.setup, default=lambda: 'mobile' if pyrap.session.useragent.mobile else 'desktop')
    pyrap.run()
