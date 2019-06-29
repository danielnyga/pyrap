'''
"Hello, World!" application in written in pyRAP

This example showcases the simplest web application written in pyRAP.

@author: Daniel Nyga (nyga@t-online.de)
'''
import pyrap
from pyrap.widgets import Shell, Label


class HelloWorld:
    '''My pyRAP application'''

    def main(self, **kwargs):
        shell = Shell(title='Welcome to pyRAP', minwidth=300, minheight=200)
        Label(shell.content, 'Hello, world!')
        shell.on_resize += shell.dolayout
        shell.show(True)


def main():
    pyrap.register(clazz=HelloWorld,
                   entrypoints={'start': HelloWorld.main},
                   path='helloworld',
                   name='My First pyRAP app!')
    pyrap.run()


if __name__ == '__main__':
    main()
