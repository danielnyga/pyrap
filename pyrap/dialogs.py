'''
Created on Nov 21, 2016

@author: nyga
'''
from dnutils import ifnone
from pyrap.widgets import Spinner, Edit,\
    Separator, Canvas
from pyrap.constants import DLG, CURSOR
from pyrap.layout import ColumnLayout, RowLayout, GridLayout, CellLayout
from pyrap.ptypes import parse_value, Color, Image
from collections import OrderedDict

import pyrap
from pyrap.base import session
from pyrap.engine import PushService
import os
from pyrap.ptypes import px, BoolVar, Font
from pyrap.themes import DisplayTheme
from pyrap.threads import DetachedSessionThread
from pyrap.widgets import Shell, constructor, Label, Composite, Button,\
    ProgressBar, StackedComposite, checkwidget, Checkbox, ScrolledComposite, \
    Option


def msg_box(parent, title, text, icon, markup=False):
    msg = MessageBox(parent, title, text, icon, markup=markup)
    msg.show(True)
    msg.on_close.wait()
    return msg.answer


def ask_question(parent, title, text, buttons, markup=False):
    msg = QuestionBox(parent, title, text, buttons, DLG.QUESTION, markup=markup)
    msg.show(True)
    msg.on_close.wait()
    return msg.answer


def ask_input(parent, title, message=False, multiline=False, password=False):
    msg = InputBox(parent, title, message=message, multiline=multiline, password=password)
    msg.show(True)
    msg.on_close.wait()
    return msg.answer


def options_list(parent, options):
    msg = OptionsDialog(parent, options)
    msg.show(pack=True)
    msg.on_close.wait()
    return msg.answer


def ask_yesnocancel(parent, title, text, markup=False):
    return ask_question(parent, title, text, ['yes', 'no', 'cancel'], markup=markup)


def ask_textinput(parent, title, markup=False):
    return ask_input(parent, title, markup=markup)


def ask_passwordinput(parent, title, markup=False):
    return ask_input(parent, title, password=True, markup=markup)


def ask_yesno(parent, title, text, markup=False):
    return ask_question(parent, title, text, ['yes', 'no'], markup=markup)


def ask_okcancel(parent, title, text, markup=False):
    return ask_question(parent, title, text, ['ok', 'cancel'], markup=markup)


def msg_ok(parent, title, text, markup=False):
    '''
    Displays a message dialog with the given title and text.

    The dialog only has one single OK button and an "information" icon.
    The dialog is modal wrt. the parent shell, i.e. the parent shell will be blocked
    until the user confirms the message by hitting OK.

    :param parent: the parent shell
    :param title:  text to be displayed in the title bar
    :param text:   text to be displayed in the message box.

    :return: None
    '''
    return msg_box(parent, title, text, DLG.INFORMATION, markup=markup)


def msg_warn(parent, title, text, markup=False):
    '''
    Displays a warning message with the given title and text.

    The dialog only has one single OK button and an "warning" icon.
    The dialog is modal wrt. the parent shell, i.e. the parent shell will be blocked
    until the user confirms the message by hitting OK.

    :param parent: the parent shell
    :param title:  text to be displayed in the title bar
    :param text:   text to be displayed in the message box.

    :return: ``None``
    '''
    return msg_box(parent, title, text, DLG.WARNING, markup=markup)


def msg_err(parent, title, text, markup=False):
    '''
    Displays a error dialog with the given title and text.

    The dialog only has one single OK button and an "error" icon.
    The dialog is modal wrt. the parent shell, i.e. the parent shell will be blocked
    until the user confirms the message by hitting OK.

    :param parent: the parent shell
    :param title:  text to be displayed in the title bar
    :param text:   text to be displayed in the message box.

    :return: None
    '''
    return msg_box(parent, title, text, DLG.ERROR, markup=markup)
    

class MessageBox(Shell):
    '''
    Represents a simple message box.
    '''

    BTN_MINWIDTH = 120
    MSGBOX_MINWIDTH = 400

    @constructor('MessageBox')    
    def __init__(self, parent, title, text, icon=None, modal=True, resize=False, btnclose=False, markup=False):
        Shell.__init__(self, parent=parent, title=title, titlebar=True, border=True,
                       btnclose=btnclose, resize=resize, modal=modal)
        self.icontheme = DisplayTheme(self, pyrap.session.runtime.mngr.theme)
        self.text = text
        self.icon = {DLG.INFORMATION: self.icontheme.icon_info,
                     DLG.QUESTION: self.icontheme.icon_question,
                     DLG.WARNING: self.icontheme.icon_warning,
                     DLG.ERROR: self.icontheme.icon_error}.get(icon)
        self.answer = None
        self.markup = markup
        
    def answer_and_close(self, a):
        self.answer = a
        self.close()
        
    def create_content(self):
        Shell.create_content(self)
        mainarea = Composite(self.content)
        mainarea.layout = RowLayout(padding=20)
        textarea = Composite(mainarea)
        if self.icon is not None:
            Label(textarea, img=self.icon, valign='top', halign='left')
        textarea.layout = ColumnLayout(hspace=20)
        Label(textarea, self.text, halign='left', valign='top', cell_minwidth=self.MSGBOX_MINWIDTH, markup=self.markup)
        buttons = Composite(mainarea)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right', valign='bottom')
        self.create_buttons(buttons)
        
    def create_buttons(self, buttons):
        ok = Button(buttons, text='OK', minwidth=self.BTN_MINWIDTH, halign='right')
        ok.on_select += lambda *_: self.answer_and_close('ok')


class OptionsDialog(Shell):
    '''
    Represents a simple dialog box providing a list of options to the user.
    '''

    @constructor('OptionsDialog')
    def __init__(self, parent, options):
        Shell.__init__(self, parent=parent, titlebar=False, border=True, resize=False, modal=True)
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

        self.layout.minheight = self.parent.shell().height * 0.7

        # calculate and set options field size
        mainarea = ScrolledComposite(self.content, padding=px(40), hscroll=True, vscroll=True, halign='fill', valign='fill', minwidth=300, minheight=100)
        mainarea.content.layout = CellLayout(halign='fill', valign='fill')

        optionslist = Composite(mainarea.content)
        optionslist.layout = RowLayout(halign='fill', valign='fill', equalheights=True)

        self.create_options(optionslist)

        self.show(True)

    def create_options(self, parent):
        for c in parent.children:
            c.dispose()
        for option in self.options:
            tmp = Option(parent, text=option, halign='left', valign='fill')
            tmp.on_checked += lambda x: self.answer_and_close([x.widget.text, self.options[x.widget.text]])

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._setoptions(options)


class QuestionBox(MessageBox):
    
    @constructor('QuestionBox')
    def __init__(self, parent, title, text, buttons, modal=True, markup=False):
        MessageBox.__init__(self, parent, title, text, icon=DLG.QUESTION, markup=markup)
        self.buttons = buttons
    
    def create_buttons(self, buttons):
        if 'ok' in self.buttons:
            ok = Button(buttons, text='OK', minwidth=self.BTN_MINWIDTH, halign='right')
            ok.on_select += lambda *_: self.answer_and_close('ok')
        if 'yes' in self.buttons:
            yes = Button(buttons, text='Yes', minwidth=self.BTN_MINWIDTH, halign='right')
            yes.on_select += lambda *_: self.answer_and_close('yes')
        if 'no' in self.buttons: 
            no = Button(buttons, text='No', minwidth=self.BTN_MINWIDTH, halign='right')
            no.on_select += lambda *_: self.answer_and_close('no')
        if 'cancel' in self.buttons:
            cancel = Button(buttons, text='Cancel', minwidth=self.BTN_MINWIDTH, halign='right')
            cancel.on_select += lambda *_: self.answer_and_close(None)


class InputBox(Shell):
    '''
    Represents a simple message box containing an editfield for text input.
    '''


    @constructor('InputBox')
    def __init__(self, parent, title, icon=None, message=False, multiline=False, password=True, modal=True, resize=False,
                 btnclose=True):
        Shell.__init__(self, parent=parent, title=title, titlebar=True, border=True,
                       btnclose=btnclose, resize=resize, modal=modal)
        self.icontheme = DisplayTheme(self, pyrap.session.runtime.mngr.theme)
        self.icon = {DLG.INFORMATION: self.icontheme.icon_info,
                     DLG.QUESTION: self.icontheme.icon_question,
                     DLG.WARNING: self.icontheme.icon_warning,
                     DLG.ERROR: self.icontheme.icon_error}.get(icon)
        self.answer = None
        self.message = message
        self.multiline = multiline
        self.password = password

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
        self.inputfield = Edit(textarea, message=self.message, multiline=self.multiline, password=self.password, valign='fill', halign='fill')

        buttons = Composite(textarea)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right',
                                      valign='bottom')
        self.create_buttons(buttons)


    def create_buttons(self, buttons):
        ok = Button(buttons, text='OK', minwidth=100)
        ok.on_select += lambda *_: self.answer_and_close(self.inputfield.text)
        cancel = Button(buttons, text='Cancel', halign='fill')
        cancel.on_select += lambda *_: self.answer_and_close(None)


def open_progress(parent, title, text, target, autoclose=False):
    dlg = ProgressDialog(parent, title, text, target, modal=0, autoclose=autoclose)
    dlg.show(True)
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

    @property
    def interrupted(self):
        return self._target._interrupt

    @status.setter
    @checkwidget
    def status(self, msg):
        self.text.text = msg
        self.dolayout()
    
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
        

def ask_color(parent, modal=True, color=None):
    dlg = ColorDialog(parent, color)
    dlg.show(True)
    dlg.on_close.wait()
    return dlg._color
    

class ColorDialog(Shell):
    PALETTE = Color.names
    
    @constructor('ColorDialog')    
    def __init__(self, parent, color=None, modal=True, resize=False, btnclose=True):
        Shell.__init__(self, parent=parent, title='Choose Color', titlebar=True, border=True,
                       btnclose=btnclose, resize=resize, modal=modal)
        self._color = parse_value(ifnone(color, 'red'), default=Color)
        
    def setcolor(self, c):
        self.red.selection = c.redi
        self.green.selection = c.greeni
        self.blue.selection = c.bluei
        self.hue.selection = c.huei
        self.saturation.selection = c.saturationi
        self.value.selection = c.valuei
        self.html.text = c.htmla
        self.alpha.selection = c.alphai
        self._redraw(c)
        self._color = c
    
    def _getcolor(self, src):
        if src == 'rgb':
            return Color(rgb=(self.red.asfloat(self.red.selection) / 255,
                         self.green.asfloat(self.green.selection) / 255,
                         self.blue.asfloat(self.blue.selection) / 255),
                         alpha=self.alpha.asfloat(self.alpha.selection) / 255)
        elif src == 'html':
            return Color(html=self.html.text)
        elif src == 'hsv':
            return Color(hsv=(self.hue.asfloat(self.hue.selection) / 255,
                         self.saturation.asfloat(self.saturation.selection) / 255,
                         self.value.asfloat(self.value.selection) / 255), 
                         alpha=self.alpha.asfloat(self.alpha.selection) / 255)
    
    
    def _redraw(self, c):
        with self.selection.gc as gc:
            s = self.selection
            s << gc.begin_path()
            r = (0, 0, 90, 90)
            s << gc.erase(*r)
            s << gc.rect(*r)
            s << gc.fill_style(c)
            s << gc.fill()
        self.selection.draw()
        
    
    def create_content(self):
        Shell.create_content(self)
        
        outer = Composite(self.content)
        outer.layout = RowLayout(padding=10, vspace=5)
        
        main = Composite(outer)
        main.layout = ColumnLayout(padding=10, hspace=20)
        
        left = Composite(main)
        left.layout = RowLayout(valign='fill', flexrows=1)
        
        h = Label(left, 'Preview:', halign='left', padding_left=0)
        h.font = h.font.modify(bf=1)
        
        selection_bg = Composite(left)
        selection_bg.bgimg = Image(os.path.join(pyrap.locations.rc_loc, 'static', 'image', 'bgtransp.png'))
        selection_bg.layout = CellLayout(halign='fill', valign='top')
        self.selection = Canvas(selection_bg, minwidth=90, minheight=90)
        self.selection.bg = 'transp'
        
        right = Composite(main)
        right.layout = RowLayout()

        h = Label(right, 'Color Values:', halign='left')
        h.font = h.font.modify(bf=1)
                
        values = Composite(right)
        values.layout = GridLayout(rows=3)

        Label(values, 'Hue:', halign='left')
        Label(values, 'Saturation:', halign='left')
        Label(values, 'Value:', halign='left')

        self.hue = Spinner(values, vmin=0, vmax=255)
        self.hue.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))

        self.saturation = Spinner(values, vmin=0, vmax=255)
        self.saturation.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))

        self.value = Spinner(values, vmin=0, vmax=255)
        self.value.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))

        Label(values, 'Red:', halign='left')
        Label(values, 'Green:', halign='left')
        Label(values, 'Blue:', halign='left')

        self.red = Spinner(values, vmin=0, vmax=255)
        self.red.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))

        self.green = Spinner(values, vmin=0, vmax=255)
        self.green.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))

        self.blue = Spinner(values, vmin=0, vmax=255)
        self.blue.on_modify += lambda *_: self.setcolor(self._getcolor('rgb'))
        
        addvals = Composite(right)
        addvals.layout = GridLayout(cols=2, halign='left')
        
        Label(addvals, 'Hex:', halign='left')
        self.html = Edit(addvals, minwidth=100)
        def html_focusout(focus):
            if focus.lost:
                self.setcolor(self._getcolor('html'))
        self.html.on_focus += html_focusout 
        
        Label(addvals, 'Alpha:', halign='left')
        self.alpha = Spinner(addvals, vmin=0, vmax=255, minwidth=100)
        self.alpha.on_modify += lambda *_: self.setcolor(self._getcolor('hsv'))
        
        Separator(right, horizontal=1, halign='fill')
        
        h = Label(right, 'Palette:', halign='left')
        h.font = h.font.modify(bf=1)
        
        palette = Composite(right)
        palette.layout = GridLayout(rows=2, equalwidths=True, equalheights=True)
        
        colors_ = set()
        for name, val in ColorDialog.PALETTE.items():
            if val not in colors_:
                colors_.add(val)
            else: continue
            l = Label(palette, minwidth=30, minheight=20, border=True)
            l.tooltip = '%s (%s)' % (name, val.upper())
            l.bg = Color(val)
            l.cursor = CURSOR.POINTER
            def setcol(event):
                self.setcolor(event.widget.bg)
            l.on_mousedown += setcol
        
        self.setcolor(self._color)
        
        Separator(outer, horizontal=1, halign='fill')
        
        buttons = Composite(outer)
        buttons.layout = ColumnLayout(equalwidths=True, halign='right')
        
        ok = Button(buttons, text='OK', halign='fill')
        ok.on_select += lambda *_: self.close()
        
        
        cancel = Button(buttons, text='Cancel', halign='fill')
        def docancel(*_):
            self._color = None
            self.close()
        cancel.on_select += docancel
        
        