'''
Created on Dec 7, 2016

@author: nyga
'''
import pyrap
from pyrap.widgets import Shell, Label
from pyrap.layout import CellLayout

class HelloWorld(object):
    '''My pyRAP application'''
    
    def main(self, display, **kwargs):
        self.shell = Shell(display, title='Hello, pyRAP!', resize=True, btnclose=True, btnmin=True, btnmax=True)
#         self.shell.content.layout = CellLayout()
        self.label = Label(self.shell.content, 'Hello, world!', halign='center', valign='center')
        self.shell.on_resize += self.shell.dolayout
        self.shell.dolayout(True)

if __name__ == '__main__':
    pyrap.register_app(clazz=HelloWorld, 
                       entrypoints={'hello': HelloWorld.main},
                       path='hello', 
                       name='My First pyRAP app!',
                       default='hello')
    pyrap.run()
