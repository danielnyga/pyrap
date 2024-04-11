'''
"D3 Demo" application in written in pyRAP

This example showcases the simplest web application written in pyRAP.

@author: Mareike Picklum (mareikep@cs.uni-bremen.de)
'''
import json
from collections import OrderedDict

import pyrap
from pyrap import session
from pyrap.dialogs import context_menu
from pyrap.layout import RowLayout
from pyrap.ptypes import Color, px
from pyrap.pwt.tol.tol import ToL
from pyrap.widgets import Shell, SashMenuComposite, Button, FileUpload, Composite, Checkbox


class D3Demo:
    '''My pyRAP application'''

    def main(self, **kwargs):
        self._shell = Shell(maximized=True, titlebar=False)
        self._shell.bg = Color('transp')
        self._shell.on_resize += self._shell.dolayout
        self.menu_width = 260

        comp_mainframe = SashMenuComposite(self._shell.content, self._shell, color='#5882B5', mwidth=self.menu_width)

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # BODY - this is the 'main' composite that for the content. The visibility of the composites inside changes
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        comp_menu = comp_mainframe.menu
        btn_uploadjson = FileUpload(comp_menu, text='Upload',
                                    accepted='.json', multi=False,
                                    halign='left', minwidth=px(self.menu_width - 30))
        btn_clear = Button(comp_menu, text='Clear', minwidth=px(self.menu_width - 30), halign='left', valign='fill')
        btn_load_tol = Button(comp_menu, text='Load Tree of Life', minwidth=px(self.menu_width - 30), halign='left', valign='fill')
        btn_save = Button(comp_menu, text='Save', minwidth=px(self.menu_width - 30), halign='left', valign='fill')

        content = Composite(comp_mainframe.content, layout=RowLayout(halign='fill', valign='fill', flexrows=0, padding_left=20))
        vizcontainer = Composite(content, layout=RowLayout(halign='fill', valign='fill', flexrows=0))
        vizcontainer.bg = Color('white')
        btn_show = Checkbox(content, text='ShowLength', halign='right', valign='fill')

        global toldata
        toldata = {}
        with open('toldata.json', 'r') as f:
            toldata = json.load(f)

        def clear(*_, **kwargs):
            for c in vizcontainer.children:
                c.dispose()

        def showlen(*_, **kwargs):
            self.rt.showlen(btn_show.checked)

        def load_tol(*_, **kwargs):
            clear()

            self.rt = ToL(vizcontainer, halign='fill', valign='fill')
            self.rt.setdata(toldata)
            self.rt.on_select += context

            self._shell.dolayout()

        def context(args):
            answer, widget = context_menu(self._shell, menuentries, location=[args.x, args.y], **{'item': args.item['name']})

        def save(*_):
            if vizcontainer.children:
                vizcontainer.children[-1].download(pdf=False, fname='viz.svg')

        menuentries = OrderedDict([('Reload', load_tol),
                                   ('Clear', clear)])

        load_tol()
        btn_clear.on_select += clear
        btn_load_tol.on_select += load_tol
        btn_save.on_select += save
        btn_show.on_checked += showlen

        self._shell.show()


def main():
    pyrap.register(clazz=D3Demo,
                   entrypoints={'start': D3Demo.main},
                   path='d3demo',
                   name='My First D3 Demo!')
    pyrap.run()


if __name__ == '__main__':
    main()
