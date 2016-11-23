'''
Created on Oct 2, 2015

@author: nyga
'''

import pyrap
from pyrap.widgets import Label, Button, RWT, Shell, Checkbox, Option, Composite,\
    Edit, Combo, TabFolder, TabItem, Group, ScrolledComposite, ScrollBar,\
    Browser, List, Canvas, GC, StackedComposite, Scale, Menu, MenuItem
import random
from pyrap import pyraplog, locations
from pyrap.utils import out
from pyrap.ptypes import BoolVar, StringVar, Color, px, Image, pc
from pyrap.layout import GridLayout, RowLayout, CellLayout, ColumnLayout,\
    StackLayout
import os
from pyrap.communication import RWTSetOperation
import math
from collections import OrderedDict
from pyrap import session
from threading import current_thread
from pyrap.constants import DLG
from pyrap.dialogs import ask_yesnocancel, msg_ok, msg_warn, msg_err, ask_yesno, ask_yesnocancel, ask_okcancel

class ControlsDemo():
    
    @staticmethod
    def setup(application): pass

    def desktop(self, display, **kwargs):
        self.shell = Shell(display)#, titlebar=1, btnclose=True, resize=True, btnmax=True, btnmin=True)
        self.shell.maximized = True
        
        
        shell = self.shell
        self.mainwnd = shell
        
        #=======================================================================
        # main layout
        #=======================================================================
        scroll = ScrolledComposite(self.mainwnd.content, vscroll=1, hscroll=1)
        outer = scroll.content
        outer.layout = RowLayout(halign='fill', valign='fill', flexrows=2)
        
        #=======================================================================
        # header
        #=======================================================================
        header = Composite(outer)
        header.layout = ColumnLayout(halign='fill', minheight='90px', flexcols=1)
        header.bgimg = Image('images/background-green.jpg')
        header.css = 'header'
        
        #=======================================================================
        # nav bar
        #=======================================================================
        navbar = Composite(outer, minheight=px(30), halign='fill', valign='fill', padding=0, padding_bottom=15)
        navbar.css = 'navbar'
        
        self.beny_logo = Image('images/beny_logo.png')
        logo = Label(header, img=self.beny_logo, valign='center', halign='fill')
        logo.bg = 'transp'    
        welcome = Label(header, text='pyRAP - Controls Demo', halign='center', valign='center')
#         welcome.color = 'white'
        welcome.css = 'header'
        welcome.bg = 'transp'
#         welcome.font = welcome.font.modify(size=24, bf=True, it=True)
        #=======================================================================
        # main area
        #=======================================================================
        main = Composite(outer)
        main.layout = ColumnLayout(halign='fill', valign='fill', flexcols=1)
        self.navigation = List(main, border=1, valign='fill', 
                          minwidth=px(250),
                          vscroll=1)
        #=======================================================================
        # footer
        #=======================================================================
        footer = Composite(outer, border=True)
        footer.layout = ColumnLayout(halign='fill', flexcols=0, minheight=50)
        footer.bgimg = Image('images/background_grey.png')
        footer.bg = 'light grey'
        Label(footer, halign='left', valign='bottom', text='powered by pyRAP v0.1').bg = 'transp'
        #=======================================================================
        # content area
        #=======================================================================
        self.content = StackedComposite(main, halign='fill', valign='fill')
        self.create_pages()
        self.navigation.on_select += self.switch_page
        self.navigation.selection = self.pages['Button']
        self.shell.onresize_shell()
        
        
    def switch_page(self, *args):
        for page in (self.pages.values()):
            page.layout.exclude = self.navigation.selection is not page
        self.content.selection = self.navigation.selection


    def create_pages(self):
        self.pages = {}
        #=======================================================================
        # create scale page
        #=======================================================================
        page  = self.create_page_template('Scale Widget Demo')
        self.create_scale_page(page)
        self.pages['Scale'] = page
        
        #=======================================================================
        # create button page
        #=======================================================================
        page = self.create_page_template('Button Widget Demo')
        self.create_button_page(page)
        self.pages['Button'] = page
        
        #=======================================================================
        # create browser page
        #=======================================================================
        page = self.create_page_template('Browser Widget Demo')
        self.create_browser_page(page)
        self.pages['Browser'] = page
        
        #=======================================================================
        # crete menu page
        #=======================================================================
        page = self.create_page_template('Menu Demo')
        self.create_menu_page(page)
        self.pages['Menu'] = page
        
        #=======================================================================
        # crete list page
        #=======================================================================
        page = self.create_page_template('List Demo')
        self.create_list_page(page)
        self.pages['List'] = page
        
        #=======================================================================
        # create scale page
        #=======================================================================
        page  = self.create_page_template('Dialog Demo')
        self.create_dialogs_page(page)
        self.pages['Dialogs'] = page
        
        for page in (self.pages.values()[1:]):
            page.layout.exclude = True
        self.navigation.items = self.pages
        

    def create_page_template(self, heading):
        # content area
        tab = Composite(self.content)
        tab.layout = RowLayout(halign='fill', valign='fill', flexrows=(1, 2))
        #heading
        header = Label(tab, text=heading, halign='left')
        header.css = 'headline'#font = header.font.modify(size='16px', bf=1)
        return tab
        
    
    def create_dialogs_page(self, parent):
        grp_info_dlgs = Group(parent, text='Info Dialogs')
        grp_info_dlgs.layout = ColumnLayout(equalwidths=1)
        
        b = Button(grp_info_dlgs, 'Show Info', halign='fill')
        def showinfo(*_):
            msg_ok(self.shell, 
                   title='pyRAP Message Box', 
                   text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
        b.on_select += showinfo
        
        b = Button(grp_info_dlgs, 'Show Warning', halign='fill')
        def showwarn(*_):
            msg_warn(self.shell, title='pyRAP Warning', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
        b.on_select += showwarn
        
        b = Button(grp_info_dlgs, 'Show Error', halign='fill')
        def showerr(*_):
            msg_err(self.shell, title='Error Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
        b.on_select += showerr
        
        grp_info_dlgs = Group(parent, text='Question Dialogs')
        grp_info_dlgs.layout = ColumnLayout()

        b = Button(grp_info_dlgs, 'Yes-No Question')
        def ask_yesno_(*_):
            resp = ask_yesno(self.shell, title='pyRAP Message Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
            msg_ok(self.shell, 'Info', 'The user clicked %s' % resp)
        b.on_select += ask_yesno_
        
        b = Button(grp_info_dlgs, 'Yes-No-Cancel Question')
        def ask_yesnocancel_(*_):
            resp = ask_yesnocancel(self.shell, title='pyRAP Message Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
            msg_ok(self.shell, 'Info', 'The user clicked %s' % resp)
        b.on_select += ask_yesnocancel_
        
        b = Button(grp_info_dlgs, 'OK-Cancel Question')
        def ask_okcancel_(*_):
            resp = ask_okcancel(self.shell, title='pyRAP Message Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
            msg_ok(self.shell, 'Info', 'The user clicked %s' % resp)
        b.on_select += ask_okcancel_
        
    
    def create_list_page(self, parent):
        grp_ctxmenu = Group(parent, text='Lists')
        grp_ctxmenu.layout = CellLayout(minwidth=200, minheight=200)
        list = List(grp_ctxmenu, halign='fill', valign='fill', minheight=200, minwidth=200)
        list.items = OrderedDict([('str1', 'bla')])
    

    def create_menu_page(self, parent):
        grp_ctxmenu = Group(parent, text='Context Menus')
        grp_ctxmenu.layout = CellLayout()
        label = Label(grp_ctxmenu, text='Right-click in this label\nto open the context menu', halign='fill', valign='fill')
        label.font = label.font.modify(family='Debby', size=48)
        menu = Menu(label, popup=True)
        item1 = MenuItem(menu, index=0, push=True, text='MenuItem 1', img=self.beny_logo)
        
        def ask(*_):
            resp = ask_yesnocancel(self.shell, title='pyRAP Message Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.\n\nAre you OK with that?')
            out('user clicked', resp)
            
        item1.on_select += ask
        
        item2 = MenuItem(menu, index=1, check=True, text='MenuItem 2')
        item3 = MenuItem(menu, index=2, check=True, text='MenuItem 3')
        item4 = MenuItem(menu, index=5, cascade=True, text='MenuItem 4')
        submenu = Menu(item4, dropdown=True)
        item4.menu = submenu
        subitem = MenuItem(submenu, index=0, push=True, text='this is the submenu...')
        item5 = MenuItem(menu, index=4, push=True, text='MenuItem 5')
        
        label.menu = menu
        

    def create_scale_page(self, parent):
        eq = Group(parent, text='Equalizer', halign='fill', valign='fill')
        eq.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=1)
        scales = []
        for _ in range(20):
            s = Scale(eq, valign='fill', orientation=RWT.VERTICAL)
            scales.append(s)
        self.mainwnd.tabseq = [self.navigation] + scales
        lower = Composite(parent)
        lower.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=1, padding_right=5)
        
        grpleft = Group(lower, text='Balance')
        grpleft.layout = RowLayout(valign='fill', halign='fill', equalheights=1)
        Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
        grpright = Group(lower, text='Fader', valign='fill', halign='fill')
        grpright.layout = RowLayout(valign='fill', halign='fill', equalheights=1)
    
    def create_button_page(self, parent):
        grp = Group(parent, text='Push Buttons')
        grp.layout = RowLayout(halign='fill', valign='center')
        for i in range(10):
            b = Checkbox(grp, text='click-%s' % i)
            b.bind(BoolVar())
            b.badge = str(i+1)
#         b.on_select += select
        
    
    def create_browser_page(self, parent):
        grp = Group(parent, text='Browser')
        grp.layout = CellLayout(halign='left', valign='top')
        browser = Button(grp, text='Open Browser')
        browser.on_select += self.open_browser

        
    def open_browser(self, data):
        dlg = Shell(self.mainwnd, title='pyRAP Browser', border=True, 
                    btnclose=True, btnmax=True, resize=True, modal=False, titlebar=True)
        dlg.bounds = self.mainwnd.width / 2 - 150, self.mainwnd.height / 2 - 100, 500, 300
        content = Composite(dlg.content)
        content.layout = RowLayout(halign='fill', valign='fill', flexrows=1)
        
        address_bar = Composite(content)
        address_bar.layout = ColumnLayout(halign='fill', valign='fill', flexcols=1)
        Label(address_bar, text='URL:')
        address = Edit(address_bar, text='http://www.tagesschau.de', message='Type your address here', halign='fill', valign='fill')
        btngo = Button(address_bar, text='Go!')
        browser = Browser(content, halign='fill', valign='fill', border=True)
        browser.url = address.text
        def load(*_):
            browser.url = address.text
        btngo.on_select += load
        dlg.dolayout()
        current_thread().setsuspended()
        dlg.on_close.wait()
        out('browser window closed')
        
        
    def mobile(self, shell, **kwargs):
        parent = shell.content
        parent.layout.halign = 'fill'   
        parent.layout.valign = 'fill'
        scroll = ScrolledComposite(parent, vscroll=True)
        scroll.layout = CellLayout(valign='fill', halign='fill')
        container = Composite(scroll)
        container.layout = RowLayout(halign='fill', valign='top')
        for i in range(200):
            Checkbox(container, text='this is the %d-th item' % (i+1), halign='left', checked=False)
        scroll.content = container



if __name__ == '__main__':
#     pyraplog.level(pyraplog.DEBUG)
    pyrap.register_app(clazz=ControlsDemo, 
                       path='controls', 
                       name='pyRAP Controls Demo', 
                       entrypoints={'desktop': ControlsDemo.desktop,
                                    'mobile': ControlsDemo.mobile},
                       theme='mytheme.css', 
                       setup=ControlsDemo.setup, default=lambda: 'mobile' if pyrap.session.useragent.mobile else 'desktop')
    pyrap.run()

