import json
from collections import OrderedDict

import pyrap
from pyrap.dialogs import context_menu
from pyrap.layout import ColumnLayout, StackLayout, RowLayout
from pyrap.ptypes import Color, px
from pyrap.pwt.radialtree.radialtree import RadialTree
from pyrap.widgets import Shell, Composite, Label, Sash, ScrolledComposite, Button, Separator


class SashMenu:
    '''My pyRAP application'''

    def __init__(self):
        self.menu_visible = False

    def main(self, **kwargs):
        self._shell = Shell(maximized=True, titlebar=False)
        self._shell.bg = Color('transp')
        self._shell.on_resize += self._shell.dolayout

        comp_mainframe = Composite(self._shell.content)
        comp_mainframe.layout = StackLayout(halign='fill', valign='fill')
        comp_mainframe.bg = Color('green')

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # BODY - this is the 'main' composite that for the content. The visibility of the composites inside changes
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

        container = Composite(comp_mainframe, layout=ColumnLayout(halign='left', valign='fill', flexcols=0))

        menu = ScrolledComposite(container, valign='fill', halign='fill')
        menu.content.layout = RowLayout(halign='fill', valign='fill', flexrows=2)
        menu.content.bg = Color('#F5F5F5')

        Label(menu.content, text='<b>Menu</b>', markup=True, halign='center', valign='fill')
        Separator(menu.content, horizontal=True, halign='fill')

        comp_menu = Composite(menu.content)
        comp_menu.layout = RowLayout(halign='fill', valign='fill', flexrows=-1)
        comp_menu.bg = 'transp'

        btn_clear = Button(comp_menu, text='Clear', minwidth=px(220), halign='left', valign='fill')
        btn_reload = Button(comp_menu, text='Reload', minwidth=px(220), halign='left', valign='fill')

        sash = Sash(container, orientation='v', click=True, valign='fill', halign='right', minwidth=10)
        sash.bg = Color('#5882B5', alpha=0.5)

        content = Composite(comp_mainframe, layout=RowLayout(halign='fill', valign='fill', flexrows=0, padding_left=20))
        radialcontainer = Composite(content, layout=RowLayout(halign='fill', valign='fill', flexrows=0))

        self.status = Label(content, text='', halign='fill', valign='fill')

        data = {}
        with open('resources/charvals_radialtree.json') as f:
            data = json.load(f)

        def clear(*_, **kwargs):
            for c in radialcontainer.children:
                c.dispose()
            self.status.text = 'Cleared Visualization {}'.format('' if not kwargs else '- triggered from node "{}"'.format(kwargs.get('item', '')))

        def reload(*_, **kwargs):
            clear()

            self.rt = RadialTree(radialcontainer, css=['resources/default.css'], halign='fill', valign='fill')
            self.rt.setdata(data)
            self.rt.on_select += context

            self.status.text = 'Reloaded Visualization {}'.format('' if not kwargs else '- triggered from node "{}"'.format(kwargs.get('item', '')))

            self._shell.dolayout()

        def context(args):
            answer, widget = context_menu(self._shell, menuentries, location=[args.x, args.y], **{'item': args.item['name']})

        menuentries = OrderedDict([('Reload', reload),
                                   ('Clear', clear)])

        reload()
        btn_clear.on_select += clear
        btn_reload.on_select += reload

        def togglemenu(*_):
            sash.parent.layout.minwidth = 0 if self.menu_visible else 250
            sash.parent.layout.maxwidth = 0 if self.menu_visible else 250

            self.menu_visible = not self.menu_visible

            self._shell.dolayout()

        sash.on_mousedown += togglemenu

        self._shell.show()


def main():
    pyrap.register(clazz=SashMenu,
                   entrypoints={'start': SashMenu.main},
                   path='sashmenu',
                   theme='resources/default.css',
                   name='Overlay Menu Example')
    pyrap.run()


if __name__ == '__main__':
    main()
