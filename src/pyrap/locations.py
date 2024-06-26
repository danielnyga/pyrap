'''
Created on Oct 2, 2015

@author: nyga
'''
import os
import appdirs

import pyrap

root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
code_base = root

pyrap_path = os.path.join(root, 'pyrap', 'data')

code_base = os.path.normpath(os.path.join(os.path.dirname(pyrap.__file__), '..'))
js_loc = os.path.realpath(os.path.join(pyrap_path, 'js'))
html_loc = os.path.join(pyrap_path, 'html')
css_loc = os.path.join(pyrap_path, 'css')
rc_loc = os.path.join(pyrap_path, 'resource')
pwt_loc = os.path.join(code_base, 'pyrap', 'pwt')
trdparty = os.path.join(pyrap_path, '3rdparty')
