'''
Created on Oct 2, 2015

@author: nyga
'''

import pyrap
from pyrap.widgets import Label, Button, RWT, Shell, Checkbox, Option, Composite,\
    Edit, Combo, TabFolder, TabItem, Group, ScrolledComposite, ScrollBar,\
    Browser, List, Canvas, GC, StackedComposite, Scale
import random
from pyrap import pyraplog, locations
from pyrap.utils import out
from pyrap.ptypes import BoolVar, StringVar, Color, px, Image, pc
from pyrap.layout import GridLayout, RowLayout, CellLayout, ColumnLayout,\
    StackLayout
import os
from pyrap.communication import RWTSetOperation
import math


class ControlsDemo():
    
    @staticmethod
    def setup(application): pass

    def desktop(self, shell, **kwargs):
        self.mainwnd = shell
        
        #=======================================================================
        # main layout
        #=======================================================================
        outer = Composite(self.mainwnd.content)
        outer.layout = RowLayout(halign='fill', valign='fill', flexrows=1)
        
        #=======================================================================
        # header
        #=======================================================================
        header = Composite(outer)
        header.layout = ColumnLayout(halign='fill', minheight='90px', flexcols=1)
#         header.bgimg = Image('images/salvage.gif')
        header.bgimg = Image('images/background_grey.png')
        header.bg = 'marine'
        
        logo = Label(header, img=Image('/home/nyga/beny/beny_logo.png').resize(height='70px'), valign='center', halign='right')
        logo.bg = 'transp'    
        welcome = Label(header, text='pyRAP - Controls Demo', halign='right', valign='top')
        welcome.color = 'white'
        welcome.bg = 'transp'
        welcome.font = welcome.font.modify(size=24, bf=True, it=True)
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
        footer.bg = 'grey'
        Label(footer, halign='left', valign='bottom', text='powered by pyRAP v0.1').bg = 'transp'
        #=======================================================================
        # content area
        #=======================================================================
        self.content = StackedComposite(main, halign='fill', valign='fill')
        self.create_pages()
        
        def switch_page(*args):
            out(self.navigation.selection, self.navigation.selidx, self.navigation.selection)
            for page in (self.pages.values()):
                out(page)
                page.layout.exclude = self.navigation.selection is not page
                out('%s layouting %s' % ({True: 'not', False: ''}[page.layout.exclude], page))
            self.content.selection = self.navigation.selection
        self.navigation.on_select += switch_page


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
        
        self.navigation.items = self.pages
        

    def create_page_template(self, heading):
        # content area
        tab = Composite(self.content)
        tab.layout = RowLayout(halign='fill', valign='fill', flexrows=(1, 2))
        #heading
        header = Label(tab, text=heading, halign='left')
        header.font = header.font.modify(size='16px', bf=1)
        return tab
        

    def create_scale_page(self, parent):
#         upper = Composite(parent)
#         upper.layout = RowLayout(halign='fill', valign='fill', flexrows=1)
        eq = Group(parent, text='Equalizer', halign='fill', valign='fill')
        eq.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=1)
        scales = []
        for _ in range(20):
            s = Scale(eq, valign='fill', orientation=RWT.VERTICAL)
#             s.on_focus += lambda *_: out('focus on ')
            scales.append(s)
        self.mainwnd.tabseq = [self.navigation] + scales
        lower = Composite(parent)
        lower.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=1, padding_right=5)
        
        grpleft = Group(lower, text='Balance')
        grpleft.layout = RowLayout(valign='fill', halign='fill', equalheights=1)
        Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
        grpright = Group(lower, text='Fader', valign='fill', halign='fill')
        grpright.layout = RowLayout(valign='fill', halign='fill', equalheights=1)
#         Label(grpright, text='here will be other controls.')
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
#         Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
    
    def create_button_page(self, parent):
        grp = Group(parent, text='Push Buttons')
        grp.layout = CellLayout(halign='fill', valign='fill')
        Label(grp, text='here come the buttons')

        
    def open_browser(self, data):
        dlg = Shell(self.mainwnd, title='pyRAP Browser', border=True, 
                    btnclose=True, btnmax=True, resize=True, modal=False, titlebar=True)
        dlg.bounds = self.mainwnd.width / 2 - 150, self.mainwnd.height / 2 - 100, 500, 300
        content = Composite(dlg.content)
        content.layout = RowLayout(halign='fill', valign='fill', flexrows=1)
        
        address_bar = Composite(content)
        address_bar.layout = ColumnLayout(halign='fill', valign='fill', flexcols=1)
        Label(address_bar, text='URL:')
        address = Edit(address_bar, text='http://www.tagesschau.de', halign='fill', valign='fill')
        btngo = Button(address_bar, text='Go!')
        browser = Browser(content, message='Type your address here', halign='fill', valign='fill', border=True)
        browser.url = address.text
        def load(*_):
            out(address.text)
            browser.url = address.text
        btngo.on_select += load
        dlg.dolayout()
        
    def onclick(self, *args):
        self.clicks += 1
        self.label.text = 'clicks: %d, from IP: %s' % (self.clicks, pyrap.session.ip)
        b = self.label.bounds
        self.label.bounds = (b[0] + random.randint(-5, 5), b[1] + random.randint(-5, 5), b[2], b[3])
        
    def mobile(self, shell, **kwargs):
        parent = shell.content
        parent.layout.halign = 'fill'   
        parent.layout.valign = 'fill'
        scroll = ScrolledComposite(parent, vscroll=True)
        scroll.layout = CellLayout(valign='fill', halign='fill')
        container = Composite(scroll)
#         container.bg = Color('red')
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
                       setup=ControlsDemo.setup, default=lambda: 'mobile' if pyrap.session.useragent.mobile else 'desktop')
    pyrap.run()

