'''
"Say Hello!" application in written in pyRAP

This example shows how HTTP query keyword arguments can also be used
within pyRAP to parameterize entrypoints.

@author: Daniel Nyga (nyga@t-online.de)
'''
import pyrap
from pyrap.widgets import Shell, Label


class SayHello:
    '''My pyRAP application'''

    def main(self, **kwargs):
        shell = Shell(title='Welcome to pyRAP', minwidth=300, minheight=200)
        Label(shell.content, 'Hello, %s!' % kwargs.get('name', 'world'))
        shell.on_resize += shell.dolayout
        shell.show(True)


def main():
    pyrap.register(clazz=SayHello,
                   entrypoints={'sayhello': SayHello.main},
                   path='helloworld',
                   name='My First pyRAP app!')
    pyrap.run(admintool=True)


if __name__ == '__main__':
    main()
