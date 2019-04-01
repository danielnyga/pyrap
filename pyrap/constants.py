'''
Created on Oct 10, 2015

@author: nyga
'''
from pyrap.utils import BitMask

inf = float('inf')

APPSTATE = BitMask('UNINITIALIZED', 'INITIALIZED', 'RUNNING')

RWT = BitMask('NONE', 'VISIBLE', 'ENABLED', 'ACTIVE', 'MAXIMIZED', 'MINIMIZED',
              'BORDER', 'MINIMIZE', 'MAXIMIZE', 'RESTORE', 'CLOSE', 'RESIZE', 
              'TITLE', 'MODAL', 'CENTER', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'FILL',
              'MULTI', 'WRAP', 'HSCROLL', 'VSCROLL', 'VERTICAL', 'HORIZONTAL',
              'BAR', 'CASCADE', 'DROP_DOWN', 'PUSH', 'SEPARATOR', 'MULTI', 'MARKUP',
              'NOSCROLL', 'SINGLE', 'POPUP', 'DRAW_MNEMONIC', 'DRAW_DELIMITER', 'DRAW_TAB',
              'CHECK', 'RADIO', 'INFINITE', 'PASSWORD')

GCBITS = BitMask('DRAW_MNEMONIC', 'DRAW_DELIMITER', 'DRAW_TAB', 'ALIGN_CENTERX',
                 'ALIGN_CENTERY', 'BOLD', 'ITALIC', 'NORMAL')

DLG = BitMask('INFORMATION', 'QUESTION', 'WARNING', 'ERROR')

d3wrapper = '''if (typeof d3 === 'undefined') {{
    {d3content}
}}'''

style = '''
<style type="text/css">
  <![CDATA[
    {}
  ]]>
</style>'''

defs = '''
<defs>{}</defs>'''.format(style)


class CURSOR:
    DEFAULT      = 1 << 0
    POINTER      = 1 << 1

    @staticmethod
    def str(i):
        return {
           CURSOR.DEFAULT : 'default',
           CURSOR.POINTER : 'pointer'
           }[i]

class FONT:
    NONE        = 0
    IT          = 1 << 0
    BF          = 1 << 1
    
    str = {NONE : '',
           IT : 'italic',
           BF : 'bold'}
    

class SHADOW:
    NONE    = 0
    IN      = 1 << 0
    OUT     = 1 << 1
    
    str = {
           IN : 'inset',
           OUT :  'out'}
    
    
class ANIMATION(object):
    EASE_IN      = 1 << 1
    EASE_OUT     = 1 << 2
    LINEAR       = 1 << 3
    
    @staticmethod
    def str(i):
        return {
           ANIMATION.EASE_IN : 'easeIn',
           ANIMATION.EASE_OUT : 'easeOut',
           ANIMATION.LINEAR : 'linear'
           }[i]
    
class BORDER(object):
    NONE         = 1 << 0
    SOLID        = 1 << 1
    DOTTED       = 1 << 2
    
    @staticmethod
    def str(i):
        return {
            BORDER.NONE : 'none',
            BORDER.SOLID : 'solid',
            BORDER.DOTTED : 'dotted'
                  }[i]
    
class GRADIENT:
    VERTICAL     = 1 << 1
    HORIZONTAL   = 1 << 2
