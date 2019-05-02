'''
Created on Oct 2, 2015

@author: nyga
'''
import base64
import json
import os
from collections import OrderedDict

import sys

from dnutils import out
from dnutils.threads import sleep, ThreadInterrupt
from dnutils.tools import ifnone

from pyrap.pwt.barchart.barchart import BarChart

import pyrap
from pyrap import session, locations
from pyrap.dialogs import msg_ok, msg_warn, msg_err, ask_yesno, ask_yesnocancel, \
    ask_okcancel, open_progress, ask_color
from pyrap.layout import GridLayout, RowLayout, CellLayout, ColumnLayout
from pyrap.ptypes import BoolVar, Color, px, Image, Font, NumVar, SVG
from pyrap.pwt.bubblyclusters.bubblyclusters import BubblyClusters
from pyrap.pwt.radar_smoothed.radar_smoothed import RadarSmoothed
from pyrap.pwt.radialdendrogramm.radialdendrogramm import RadialDendrogramm
from pyrap.pwt.graph.graph import Graph
from pyrap.pwt.plot.plot import Scatterplot
from pyrap.pwt.radar.radar import RadarChart
from pyrap.pwt.tree.tree import Tree
from pyrap.pwt.video.video import Video
from pyrap.widgets import Label, Button, RWT, Shell, Checkbox, Composite, Edit, \
    Group, ScrolledComposite, Browser, List, Canvas, StackedComposite, Scale, \
    Menu, MenuItem, Spinner, info, FileUpload, TabFolder, Table, Sash, Toggle, \
    DropDown, Combo, Option, error
import pyrap.web

class Images:
    IMG_UP = Image('images/icons/up.gif')
    IMG_DOWN = Image('images/icons/down.gif')
    IMG_CHECK = Image('images/icons/tick.png')
    IMG_RED = Image('images/icons/bullet_red.png')
    IMG_GREEN = Image('images/icons/bullet_green.png')
    IMG_WHITE = Image('images/icons/bullet_white.png')


class ControlsDemo():
    
    @staticmethod
    def setup(application): pass

    def desktop(self, **kwargs):
        page = kwargs.get('page', 'Radar')
        self.shell = Shell(maximized=True, titlebar=False)
        self.shell.on_resize += self.shell.dolayout
        shell = self.shell
        self.mainwnd = shell
        
        #=======================================================================
        # main layout
        #=======================================================================
        scroll = ScrolledComposite(shell.content, vscroll=1, hscroll=0, halign='fill', valign='fill', minwidth=100, minheight=100)
        outer = scroll.content
        outer.layout = RowLayout(halign='fill', valign='fill', flexrows=2)
        
        #=======================================================================
        # header
        #=======================================================================
        header = Composite(outer)
        header.layout = ColumnLayout(halign='fill', minheight='90px', flexcols=1)
        header.bgimg = Image('images/background-blue.jpg')
        header.css = 'header'
        
        #=======================================================================
        # nav bar
        #=======================================================================
        navbar = Composite(outer, minheight=px(30), halign='fill', valign='fill', padding=0, padding_bottom=15)
        navbar.css = 'navbar'
        
        self.beny_logo = Image('images/pyrap-logo.png').resize(height='75px')
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
        main.layout = ColumnLayout(halign='fill', valign='fill', flexcols=2, minheight=500)
        self.navigation = List(main, border=1, valign='fill', 
                          minwidth=px(250),
                          vscroll=1)
        # =======================================================================
        # footer
        # =======================================================================
        sash = Sash(main, orientation='v', valign='fill')

        def apply_sash(event):
            x, _, _, _ = sash.bounds
            delta_x = event.x - x
            i = sash.parent.children.index(sash)
            prev = sash.parent.children[i-1]
            prev.layout.minwidth = prev.width + delta_x #+ 2 * sash.parent.layout.hspace
            try:
                del sash.parent.layout.flexcols[0]
            except (IndexError, KeyError): pass
            self.shell.dolayout()

        sash.on_select += apply_sash

        #=======================================================================
        # footer
        #=======================================================================
        footer = Composite(outer, border=True)
        footer.layout = ColumnLayout(halign='fill', flexcols=0, minheight=50)
        footer.bgimg = Image('images/background_grey.png')
        footer.bg = 'light grey'
        pyversion = '.'.join(map(str, sys.version_info[:3]))
        Label(footer, halign='left', valign='bottom', text='Session ID: %s\nPowered by pyRAP v%s on Python %s' % (session.id, pyrap.__version__, pyversion)).bg = 'transp'

        #=======================================================================
        # content area
        #=======================================================================
        self.content = StackedComposite(main, halign='fill', valign='fill')
        self.create_pages()
        self.navigation.on_select += self.switch_page
        self.navigation.selection = self.pages[page]
        self.switch_page()

        self.shell.show(True)

    def switch_page(self, *args):
        for page in (self.pages.values()):
            page.layout.exclude = self.navigation.selection is not page
        self.content.selection = self.navigation.selection
        self.shell.onresize_shell()

    def create_pages(self):
        self.pages = OrderedDict()
        #=======================================================================
        # create scale page
        #=======================================================================
        page  = self.create_page_template('Scale Widget Demo')
        self.create_scale_page(page)
        self.pages['Scale'] = page
        
        # =======================================================================
        # crete canvas page
        # =======================================================================
        page = self.create_page_template('Canvas Demo')
        self.create_canvas_page(page)
        self.pages['Canvas'] = page
        
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
        # create dialogs page
        #=======================================================================
        page  = self.create_page_template('Dialog Demo')
        self.create_dialogs_page(page)
        self.pages['Dialogs'] = page
        
        #=======================================================================
        # create spinner page
        #=======================================================================
        page  = self.create_page_template('Spinner Demo')
        self.create_spinner_page(page)
        self.pages['Spinner'] = page
        
        #=======================================================================
        # create fileupload
        #=======================================================================
        page  = self.create_page_template('File Upload Demo')
        self.create_upload_page(page)
        self.pages['FileUpload'] = page

        # =======================================================================
        # create tab folders
        # =======================================================================
        page = self.create_page_template('Tab Folders')
        self.create_tabfolder_page(page)
        self.pages['TabFolders'] = page

        # =======================================================================
        # create scrolled composite
        # =======================================================================
        page = self.create_page_template('Scrolled Composite')
        self.create_scrolled_page(page)
        self.pages['Scrolled'] = page

        # =======================================================================
        # create table demo
        # =======================================================================
        page = self.create_page_template('Table Demo')
        self.create_table_page(page)
        self.pages['Tables'] = page

        # =======================================================================
        # create sash demo
        # =======================================================================
        page = self.create_page_template('Sash Demo')
        self.create_sash_page(page)
        self.pages['Sash'] = page

        # =======================================================================
        # create cookies demo
        # =======================================================================
        page = self.create_page_template('Cookies Demo')
        self.create_cookies_page(page)
        self.pages['Cookies'] = page

        #=======================================================================
        # create radar chart
        #=======================================================================
        page  = self.create_page_template('Radar Chart Demo')
        self.create_radar_page(page)
        self.pages['Radar'] = page

        # =======================================================================
        # create radar chart -- redesigned
        # =======================================================================
        page = self.create_page_template('Radar Chart Demo -- Smoothed')
        self.create_radarsmoothed_page(page)
        self.pages['Radar Smooth'] = page

        #=======================================================================
        # create D3 radial dendrogramm
        #=======================================================================
        page = self.create_page_template('D3 Radial Dendrogramm')
        self.create_cluster_page(page)
        self.pages['Radial Dendrogramm'] = page

        #=======================================================================
        # create D3 bubbly clusters chart
        #=======================================================================
        page = self.create_page_template('D3 Bubbly Clusters')
        self.create_bubblycluster_page(page)
        self.pages['Bubbly Clusters'] = page

        #=======================================================================
        # create D3 tree
        #=======================================================================
        page = self.create_page_template('D3 Tree')
        self.create_tree_page(page)
        self.pages['Tree'] = page

        #=======================================================================
        # create D3 scatterplot
        #=======================================================================
        page = self.create_page_template('D3 Scatterplot')
        self.create_scatterplot_page(page)
        self.pages['Scatterplot'] = page

        #=======================================================================
        # create D3 graph
        #=======================================================================
        page = self.create_page_template('D3 Graph')
        self.create_graph_page(page)
        self.pages['Directed Graph'] = page

        #=======================================================================
        # create D3 bar chart
        #=======================================================================
        page = self.create_page_template('D3 Bar Chart')
        self.create_barchart_page(page)
        self.pages['Bar Chart'] = page

        # =======================================================================
        # create video
        # =======================================================================
        page = self.create_page_template('Video')
        self.create_video_page(page)
        self.pages['Video'] = page

        for page in [self.pages[k] for k in sorted(self.pages.keys())][1:]:
            page.layout.exclude = True
        self.navigation.items = self.pages

    def create_page_template(self, heading):
        # content area
        tab = Composite(self.content)
        tab.layout = RowLayout(halign='fill', valign='fill', flexrows={1: 2, 2: 1, 3: .5})
        #heading
        header = Label(tab, text=heading, halign='left')
        header.css = 'headline'#font = header.font.modify(size='16px', bf=1)
        return tab

    def create_cookies_page(self, parent):

        def check_cookies(_):
            if self.navigation.selection is parent:
                if not session.client.data.get('allow_cookies', False):
                    if ask_yesno(self.shell, 'Cookies', 'This page will save cookies on your local machine.\n\nDo you agree?') == 'yes':
                        session.client.data.allow_cookies = True
                update_client_data()

        self.navigation.on_select += check_cookies

        parent.layout.flexrows = {2: 1}
        top = Composite(parent, layout=ColumnLayout(halign='left'))
        Label(top, ('Use <tt>session.client.data</tt> to permanently store data on the client ' +
                   'machine.<br>Right-click to add new data and check that they persist also over <a target="_blank" href="%s?page=Cookies">different sessions</a>.' % session.location), markup=True, halign='left')

        clear = Button(top, 'Clear')
        clear.tooltip = 'Delete all client data'

        def cleardata(_):
            session.client.data = web.Storage()
            update_client_data()

        table = Table(parent, valign='fill', halign='fill')

        table.addcol('Key', width=200)
        table.addcol('Value', width=200)
        table.addcol('Type', width=100)

        clear.on_select += cleardata

        def update_client_data():
            for item in table.items:
                table.rmitem(item)
            for key, value in session.client.data.items():
                i = table.additem(texts=[str(key), str(value), type(value).__name__], data=(key, value))
            if not session.client.data.get('allow_cookies', False):
                clear.decorator = error('You must accept cookies to use this feature')
                clear.enabled = False
            else:
                clear.decorator = None
                clear.enabled = True

        update_client_data()

        def additem(_):
            dlg = Shell(parent=self.shell, title='Add new user data')
            dlg.content.layout = GridLayout(cols=2, padding=20)
            Label(dlg.content, 'Key:')
            editKey = Edit(dlg.content, minwidth=200, halign='fill')
            Label(dlg.content, 'Value:')
            editValue = Edit(dlg.content, minwidth=200, halign='fill')

            Label(dlg.content, 'Type:')

            type_comp = Composite(dlg.content, layout=ColumnLayout())

            opt_str = Option(type_comp, 'String')
            opt_str.checked = True
            opt_num = Option(type_comp, 'Number')
            opt_bool = Option(type_comp, 'Bool')

            Label(dlg.content)

            ok = Button(dlg.content, 'OK', halign='right')

            def doadd(_):
                if not session.client.data.get('allow_cookies', False):
                    msg_err(self.shell, 'Unable to add client data', 'You must agree to accept cookies on you machine first.')
                    return
                type_ = str
                value = editValue.text
                if opt_num.checked:
                    type_ = float
                if opt_bool.checked:
                    type_ = bool
                    value = {'true': True, 'false': False}[value.lower()]
                session.client.data[editKey.text] = type_(value)
                update_client_data()
                dlg.close()

            ok.on_select += doadd
            dlg.show(pack=True)

        m = Menu(table, popup=True)
        insert = MenuItem(m, 'Insert...')
        insert.on_select += additem
        table.menu = m

        remove = MenuItem(m, 'Remove')

        def rmitem(_):
            sel = table.selection
            if sel:
                try:
                    del session.client.data[sel.data[0]]
                except KeyError: pass
            update_client_data()

        remove.on_select += rmitem

    def create_sash_page(self, parent):
        container = Composite(parent, layout=ColumnLayout(halign='fill', valign='fill', flexcols=[0,2]))

        left = Label(container, 'LEFT', halign='fill', valign='fill', border=True)
        sash = Sash(container, orientation='v', valign='fill')
        right = Label(container, 'RIGHT', halign='fill', valign='fill', border=True)

        def apply_sash(event):
            x, _, _, _ = sash.bounds
            delta_x = event.x - x
            i = sash.parent.children.index(sash)
            prev = sash.parent.children[i-1]
            prev.layout.minwidth = prev.width + delta_x #+ 2 * sash.parent.layout.hspace
            try:
                del sash.parent.layout.flexcols[0]
            except (IndexError, KeyError): pass
            self.shell.dolayout()

        sash.on_select += apply_sash


    def create_table_page(self, parent):
        table = Table(parent, halign='fill', valign='fill', headervisible=True, colsmoveable=True, check=True)

        def sort_by_firstname(_):
            table.items = sorted(table.items, key=lambda item: item.texts[0], reverse=table.sortedby[1] == 'down')

        def sort_by_lastname(_):
            table.items = sorted(table.items, key=lambda item: item.texts[1], reverse=table.sortedby[1] == 'down')

        def sort_by_title(_):
            table.items = sorted(table.items, key=lambda item: item.texts[2], reverse=table.sortedby[1] == 'down')

        firstname = table.addcol('Last Name', img=Images.IMG_RED, sortable=True)
        firstname.on_select += sort_by_firstname

        lastname = table.addcol('First Name', sortable=True)
        lastname.on_select += sort_by_lastname

        title = table.addcol('Title', sortable=True)
        title.on_select += sort_by_title

        table.additem(['Nyga', 'Daniel', 'Dr.'], images=[Images.IMG_CHECK, None, Images.IMG_GREEN, None])
        table.additem(['Picklum', 'Mareike', 'M.Sc.'], images=[Images.IMG_CHECK, None, Images.IMG_GREEN, None])
        table.additem(['Beetz', 'Michael', 'Prof. PhD.'], images=[Images.IMG_DOWN, None, Images.IMG_WHITE, None])
        table.additem(['Balint-Benczedi', 'Ferenc', 'M.Sc.'], images=[Images.IMG_DOWN, None, Images.IMG_RED, None])

        m = Menu(table, popup=True)
        insert = MenuItem(m, 'Insert...')
        delete = MenuItem(m, 'Delete...')

        def insertitem(event):
            dlg = Shell(parent=self.shell, title='Create new entry')
            dlg.content.layout = GridLayout(valign='fill', equalheights=True, cols=2, padding=20)
            Label(dlg.content, 'First Name:', halign='right')
            fname = Edit(dlg.content, minwidth=200)
            Label(dlg.content, 'Last Name:', halign='right')
            lname = Edit(dlg.content, minwidth=200)
            Label(dlg.content, 'Title', halign='right')
            title = Combo(dlg.content, halign='fill')
            title.items = ['M. Sc.', 'Dr.', 'Prof.']
            Composite(dlg.content)
            buttons = Composite(dlg.content, layout=ColumnLayout(equalwidths=True))
            ok = Button(buttons, 'OK')
            cancel = Button(buttons, 'Cancel')
            dlg.tabseq = (fname, lname, title, ok, cancel)

            def insert(event):
                table.additem([lname.text, fname.text, title.text])
                dlg.close()

            ok.on_select += insert
            cancel.on_select += lambda _: dlg.close()
            dlg.show(True)

        insert.on_select += insertitem

        def rmitem(*_):
            if table.selection:
                doit = ask_yesno(self.shell, 'Please confirm', 'Are you sure you want to delete %s %s %s?' % (table.selection.texts[2],
                                                                                                              table.selection.texts[1],
                                                                                                              table.selection.texts[0])) == 'yes'
                if doit:
                    table.rmitem(table.selection)
            if not table.items:
                delete.enabled = False

        delete.on_select += rmitem
        table.menu = m

    def create_scrolled_page(self, parent):
        page = Composite(parent, layout=CellLayout(halign='fill', valign='fill'))
        container = Composite(page, layout=RowLayout())
        Label(container, 'This frame is scrollable:', halign='left')
        scrolled = ScrolledComposite(container, vscroll=True, hscroll=True, minwidth=300, minheight=300, border=True)
        scrolled.content.layout = CellLayout(minwidth=700, minheight=700)  #RowLayout(halign='fill', valign='fill')
        Label(scrolled.content, halign='fill', valign='fill', padding=20).css = 'bgrepeat'

    def create_tabfolder_page(self, parent):
        page = Composite(parent, layout=RowLayout(halign='fill', valign='fill', equalheights=True))
        tabs = TabFolder(page, halign='center', valign='center', tabpos='bottom', minheight=200)
        page1 = tabs.addtab('First Page')
        Label(page1.content, 'Hello', halign='fill', valign='fill').bg = 'red'
        page2 = tabs.addtab('Second Page')
        Label(page2.content, 'pyRAP!', halign='center', valign='center').bg = 'yellow'
        tabs.selected = 0

    def create_upload_page(self, parent):
        body = Composite(parent)
        body.layout = RowLayout(halign='fill', valign='fill', flexrows=3)
        upload = FileUpload(body, text='Browse...', multi=True, halign='left', valign='top')
        cont = Composite(body)
        cont.layout = GridLayout(cols=2, halign='fill', flexcols=1)
        Label(cont, 'Filename:')
        filename = Label(cont, halign='fill')
        Label(cont, 'File size:')
        filesize = Label(cont, halign='fill')
        Label(cont, 'File Type:')
        filetype = Label(cont, halign='fill')
        Label(body, text='Content:', halign='fill')
        content = Edit(body, halign='fill', valign='fill', multiline=True, wrap=True)
        content.font = Font(family='monospace', size='11px')
        def uploaded():
            files = session.runtime.servicehandlers.fileuploadhandler.files[upload.token]
            filename.text = ', '.join([f['filename'] for f in files])
            fullcnt = ''
            for f in files:
                try:
                    if filetype.text.startswith('application'): raise UnicodeDecodeError()
                    fullcnt += f['filecontent'].decode('utf8')
                except UnicodeDecodeError:
                    fullcnt += base64.b64encode(f['filecontent']).decode()
                fullcnt += '\n\n'
            filesize.text = '%d Byte' % (len(fullcnt)-2)
            filetype.text = ', '.join([f['filetype'] for f in files])
            content.text = fullcnt
        upload.on_finished += uploaded
    
    def create_spinner_page(self, parent):
        body = Composite(parent, layout=ColumnLayout(valign='fill', halign='fill', equalwidths=True))
        # spinners
        grp = Group(body, 'Spinners')
        grp.layout = GridLayout(cols=2, equalheights=True)
        Label(grp, text='Simple Spinner:', halign='left')
        s1 = Spinner(grp)
        Label(grp, text='Spinner:', halign='left')
        s2 = Spinner(grp)        
        Label(grp, 'Current value:', halign='left')
        l = Label(grp, halign='fill')
        
        def onchange(*_):
            l.text = str(s2.asfloat(s2.selection))
        
        s2.on_modify += onchange
        
        # settings
        settings = Group(body, 'Settings')
        settings.layout = GridLayout(cols=2, equalheights=True)
        
        Label(settings, 'Minimum:', halign='right')
        min_ = Edit(settings, text=str(s1.min), halign='fill')

        Label(settings, 'Maximum:', halign='right')
        max_ = Edit(settings, text=str(s1.max), halign='fill')
        
        Label(settings, 'Digits:', halign='right')
        digs = Spinner(settings, vmin=0, vmax=10, digits=0, sel=s1.digits)
        
        Label(settings, 'Selection', halign='right')
        sel = Edit(settings, text=ifnone(s2.selection, '', str), halign='fill')
        
        Label(settings)
        apply = Button(settings, halign='right', text='Apply')
        
        def apply_settings(*_):
            s1.min = int(min_.text)
            s2.min = int(min_.text)
            s1.max = int(max_.text)
            s2.max = int(max_.text)
            s1.digits = digs.selection
            s2.digits = digs.selection
            s2.selection = s1.selection = None if sel.text == '' else int(sel.text)
            
        apply.on_select += apply_settings
        self.shell.tabseq = (s1, s2, min_, max_, digs, sel, apply)
            
    def create_dialogs_page(self, parent):
        grp_info_dlgs = Composite(parent)#, text='Info Dialogs')
        grp_info_dlgs.layout = ColumnLayout(valign='fill', minheight=100)
        grp_info_dlgs.bg = Color('blue')

        b = Button(grp_info_dlgs, 'Show Info', halign='fill')
        b.decorator = info('this is a decorator description.')

        def showinfo(*_):
            ret = msg_ok(self.shell,
                   title='pyRAP Message Box', 
                   text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.')
            out('message box returned', ret)
        b.on_select += showinfo
        
        b = Button(grp_info_dlgs, 'Show Warning', halign='fill')
        def showwarn(*_):
            msg_warn(self.shell, title='pyRAP Warning', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.')
        b.on_select += showwarn
        
        b = Button(grp_info_dlgs, 'Show Error', halign='fill')
        def showerr(*_):
            msg_err(self.shell, title='Error Box', text='This is my first message. It can also span multiple lines. You just have to put\nnewline in the message box text.')
        b.on_select += showerr
        
        grp_progress_dlgs = Composite(parent)#, text='Other Dialogs')
        grp_progress_dlgs.layout = ColumnLayout(valign='fill')
        grp_progress_dlgs.bg = Color('yellow')

        def process(dlg):
            try:
                dlg.status = 'Preparing a time-consuming task...'
                dlg.setloop(1)
                sleep(2.5)
                dlg.setloop(0)
                dlg.max = 100
                for i in range(100):
                    dlg.status = 'Step %d completed' % (i+1)
                    dlg.inc()
                    if dlg.interrupted: return
                    dlg.push.flush()
                    sleep(.1)
                dlg.status = 'Done. All tasks completed.'
                dlg.setfinished()
                dlg.push.flush()
            except ThreadInterrupt:
                out('process was interrupted.')

        b = Button(grp_progress_dlgs, 'Open Progress...', halign='fill')
        def showprog(*_):
            open_progress(self.shell, 'Progress Report', 'Running a long procedure...', target=process)
        b.on_select += showprog
        
        b = Button(grp_progress_dlgs, 'Change color...', valign='center')
        def showcolor(*_):
            color = ask_color(self.shell)
            out('user picked', color)
            grp_progress_dlgs.bg = color
        b.on_select += showcolor
        
        grp_info_dlgs = Composite(parent)#, text='Question Dialogs')
        grp_info_dlgs.layout = ColumnLayout(valign='fill')
        grp_info_dlgs.bg = Color('red')

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
        item1 = MenuItem(menu, index=0, push=True, text='MenuItem 1', img=Image('images/pyrap-logo.png').resize(height='32px'))
        
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
            c = Composite(eq, layout=RowLayout(valign='fill', flexrows=1))
            Label(c, '+')
            s = Scale(c, valign='fill', orientation=RWT.VERTICAL)
            Label(c, '-')
            scales.append(s)
        self.mainwnd.tabseq = [self.navigation] + scales
        lower = Composite(parent)
        lower.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=1, padding_right=5, hspace=10)
        
        grpleft = Group(lower, text='Balance')
        grpleft.layout = ColumnLayout(valign='fill', halign='fill', flexcols=1)
        Label(grpleft, '-')
        Scale(grpleft, halign='fill', orientation=RWT.HORIZONTAL)
        Label(grpleft, '+')
        grpright = Group(lower, text='Fader', valign='fill', halign='fill')
        grpright.layout = ColumnLayout(valign='fill', halign='fill', flexcols=1)
        Label(grpright, '-')
        Scale(grpright, halign='fill', orientation=RWT.HORIZONTAL)
        Label(grpright, '+')
        
    
    def create_canvas_page(self, parent):
        grp_ctxmenu = Group(parent, text='Canvas')
        grp_ctxmenu.layout = CellLayout(halign='fill', valign='fill')
        canvas = Canvas(grp_ctxmenu, halign='fill', valign='fill')
        context = canvas.gc
        canvas << context.draw_grid(10, 10, 'lightgrey')

        canvas << context.begin_path()
        canvas << context.rect(50, 50, 300, 100)
        canvas << context.fill_style(Color('white'))
        canvas << context.fill()
        canvas << context.linewidth(1)
        canvas << context.stroke_style(Color('black'))
        canvas << context.stroke()

        canvas << context.fill_style(Color('red'))
        canvas << context.font('Arial', 30)
        canvas << context.stroke_text("Hello World!\nThis is Awesome!", 200, 100, aligncenterx=True, aligncentery=True)

        canvas << context.begin_path()
        canvas << context.rect(50, 150, 300, 100)
        canvas << context.fill_style(Color('light grey'))
        canvas << context.fill()
        canvas << context.linewidth(1)
        canvas << context.stroke_style(Color('black'))
        canvas << context.stroke()

        canvas << context.fill_style(Color('green'))
        canvas << context.font('Arial', 30)
        canvas << context.fill_text("Hello World!\nThis is Awesome!", 60, 200, aligncenterx=False, aligncentery=True)
        canvas.draw()    
       
    
    def create_button_page(self, parent):
        grp = Group(parent, text='Push Buttons')
        grp.layout = RowLayout(halign='fill', valign='center')
        for i in range(10):
            b = Checkbox(grp, text='click-%s' % i)
            b.bind(BoolVar())
            b.badge = str(i+1)

        pushbuttons = Group(parent, layout=ColumnLayout(halign='fill', equalwidths=True))
        button = Button(pushbuttons, 'Pushbutton')
        toggle = Toggle(pushbuttons, 'Togglebutton')

    def create_browser_page(self, parent):
        grp = Group(parent, text='Browser')
        # grp.layout = GridLayout(cols=1, minheight=200, minwidth=200, flexcols=0)
        # container = Composite(grp)
        grp.layout = ColumnLayout(minheight=200, minwidth=200, flexcols=0)
        # grp.bg = 'yellow'
        # grp.bg = 'green'
        Label(grp, 'Click:', halign='center')
        browser = Button(grp, text='Open Browser', halign='center')
        browser.on_select += self.open_browser

    def create_radar_page(self, parent):
        grp = Group(parent, text='Radar Chart')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = {}
        with open('resources/radar.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            radar = RadarChart(comp_body, legendtext=data.get('legendtext', ''), halign='fill', valign='fill')

            for i, axis in enumerate(data.get('axes', [])):
                radar.addaxis(name=axis.get("name", "Axis {}".format(i)),
                              minval=axis.get("limits", [0, 1])[0],
                              maxval=axis.get("limits", [0, 1])[1],
                              unit=axis.get("unit", '%'),
                              intervalmin=axis.get("interval", [.4, .6])[0],
                              intervalmax=axis.get("interval", [.4, .6])[1],
                              )

            radar.setdata(data.get('data', {}))

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_radarsmoothed_page(self, parent):
        grp = Group(parent, text='Radar Chart -- Smoothed')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = {}
        with open('resources/radar.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            radar = RadarSmoothed(comp_body, legendtext=data.get('legendtext', ''), halign='fill', valign='fill')

            for i, axis in enumerate(data.get('axes', [])):
                radar.addaxis(name=axis.get("name", "Axis {}".format(i)),
                              minval=axis.get("limits", [0, 1])[0],
                              maxval=axis.get("limits", [0, 1])[1],
                              unit=axis.get("unit", '%'),
                              intervalmin=axis.get("interval", [.4, .6])[0],
                              intervalmax=axis.get("interval", [.4, .6])[1],
                              )

            radar.setdata(data.get('data', {}))

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_cluster_page(self, parent):
        grp = Group(parent, text='Radial Dendrogramm')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        txt = Edit(comp_btn, text='28Mn6', halign='fill', valign='fill')
        btn = Button(comp_btn, text='Highlight', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = []
        with open('resources/materials.json') as f:
            data = json.load(f)

        def highlight(*_):
            comp_body.children[-1].highlight(txt.text)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            cluster = RadialDendrogramm(comp_body, halign='fill', valign='fill')
            cluster.setdata(data)

            self.shell.dolayout()

        reload()
        btn.on_select += highlight
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_bubblycluster_page(self, parent):
        grp = Group(parent, text='Bubbly Cluster')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download SVG', halign='fill', valign='fill')
        btn_play = Button(comp_btn, text='Download PDF', halign='fill', valign='fill')

        audio = os.path.join(locations.rc_loc, 'static', 'audio', 'blob.mp3')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = []
        with open('resources/bubbly.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def play(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=True)

        def reload(*_):
            if comp_body.children:
                clear()

            cluster = BubblyClusters(comp_body, halign='fill', valign='fill')
            # cluster.setaudio(audio)
            cluster.setdata(data)

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download
        btn_play.on_select += play

    def create_tree_page(self, parent):
        grp = Group(parent, text='Tree')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = CellLayout(halign='fill', valign='fill')

        data = []
        with open('resources/treedata.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            clear()

            t = Tree(comp_body, halign='fill', valign='fill')
            t.setdata(data)

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_scatterplot_page(self, parent):
        grp = Group(parent, text='Scatterplot')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Reload', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = []
        with open('resources/scatter.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            plot = Scatterplot(comp_body, halign='fill', valign='fill')
            plot.axeslabels('X-Axis', 'Y-Axis')
            plot.formats(xformat=['', ".2%", ''], yformat=['', ".2%", ''])
            plot.setdata(data)

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_graph_page(self, parent):
        grp = Group(parent, text='Graph')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Load', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = []
        with open('resources/graph.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            graph = Graph(comp_body, halign='fill', valign='fill')
            graph.updatedata(data)

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_barchart_page(self, parent):
        grp = Group(parent, text='Bar Chart')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_clear = Button(comp_btn, text='Clear', halign='fill', valign='fill')
        btn_reload = Button(comp_btn, text='Load', halign='fill', valign='fill')
        btn_download = Button(comp_btn, text='Download', halign='fill', valign='fill')

        def download(*_):
            if comp_body.children:
                v = comp_body.children[-1]
                v.download(pdf=False)

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        data = []
        with open('resources/barchart.json') as f:
            data = json.load(f)

        def clear(*_):
            for c in comp_body.children:
                c.dispose()

        def reload(*_):
            if comp_body.children:
                clear()

            bc = BarChart(comp_body, halign='fill', valign='fill')
            bc.data(data)

            self.shell.dolayout()

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload
        btn_download.on_select += download

    def create_video_page(self, parent):
        grp = Group(parent, text='Video')
        grp.layout = RowLayout(halign='fill', valign='fill', flexrows=1)

        comp_btn = Composite(grp)
        comp_btn.layout = ColumnLayout(halign='fill', valign='fill', equalwidths=True)
        btn_play = Button(comp_btn, text='Play', halign='fill', valign='fill')
        btn_pause = Button(comp_btn, text='Pause', halign='fill', valign='fill')

        comp_body = Composite(grp)
        comp_body.layout = RowLayout(halign='fill', valign='fill', flexrows=0)

        v = Video(comp_body, halign='fill', valign='fill')
        v.addsrc({'source': 'resources/test.mp4', 'type': 'video/mp4'})

        def play(*_):
            v.play()

        def pause(*_):
            v.pause()

        btn_play.on_select += play
        btn_pause.on_select += pause

    def open_browser(self, data):
        dlg = Shell(title='pyRAP Browser', minwidth=500, minheight=400)
        dlg.on_resize += dlg.dolayout
        content = Composite(dlg.content, layout=RowLayout(halign='fill', valign='fill', flexrows=1))
        address_bar = Composite(content, layout=ColumnLayout(halign='fill', valign='fill', flexcols=1))

        Label(address_bar, text='URL:')
        address = Edit(address_bar, text='http://www.tagesschau.de', message='Type your address here', halign='fill', valign='fill')
        btngo = Button(address_bar, text='Go!')
        browser = Browser(content, halign='fill', valign='fill', border=True)
        browser.url = address.text
        def load(*_):
            browser.url = address.text
        btngo.on_select += load
        dlg.show(True)
        dlg.on_close.wait()

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


def main():
    pyrap.register_app(clazz=ControlsDemo,
                       path='controls',
                       name='pyRAP Controls Demo',
                       entrypoints={'desktop': ControlsDemo.desktop},
                                    # 'mobile': ControlsDemo.mobile},
                       theme='mytheme.css',
                       setup=ControlsDemo.setup)#, default=lambda: 'mobile' if 'mobile' in pyrap.session.client.useragent else 'desktop')
    pyrap.run(admintool=True)


if __name__ == '__main__':
    main()
