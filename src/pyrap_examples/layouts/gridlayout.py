'''
"GridLayoutExampple!" application in written in pyRAP

This example showcases the grid layout manager of pyRAP.

@author: Daniel Nyga (daniel.nyga@t-online.de)
'''
from dnutils import ifnone

import pyrap
from pyrap.layout import GridLayout
from pyrap.widgets import Shell, Button


class GridLayoutExample:
    '''Demonstrates some capabilities of GridLyaout'''

    def dimensions(self, **kwargs):
        rows, cols = ifnone(kwargs.get('rows'), None, int), ifnone(kwargs.get('cols'), None, int)
        shell = Shell(title='GridLayout with %s rows and %s columns' % (ifnone(rows, 'variable'), ifnone(cols, 'variable')))
        shell.content.layout = GridLayout(rows=rows, cols=cols)
        for i in range(20):
            Button(shell.content, text='Button %.2d' % (i+1))
        shell.on_resize += shell.dolayout
        shell.show(True)

    def stretch(self, **kwargs):
        equalwidths = {'true': True, 'false': False}[kwargs.get('equalwidths', 'false').lower()]
        flexcols = None
        equalheights = {'true': True, 'false': False}[kwargs.get('equalheights', 'false').lower()]
        flexrows = None
        if not equalwidths:
            flexcols = 0
        if not equalheights:
            flexrows = {1: 1, 2: 2, 3: 3, 4:4}
        shell = Shell(title='GridLayout with flexible rows and columns', maximized=True)
        shell.content.layout = GridLayout(rows=5, halign='fill', valign='fill', equalwidths=equalwidths, equalheights=equalheights, flexcols=flexcols, flexrows=flexrows)
        for i in range(20):
            Button(shell.content, text='Button %.2d' % (i+1), halign='fill', valign='fill')
        shell.on_resize += shell.dolayout
        shell.show(True)


def main():
    pyrap.register(clazz=GridLayoutExample,
                   entrypoints={'dimensions': GridLayoutExample.dimensions,
                                'stretch': GridLayoutExample.stretch},
                   path='grid',
                   name='GridLayout - Examples!')
    pyrap.run()


if __name__ == '__main__':
    main()
