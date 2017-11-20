'''
Created on Oct 2, 2015

@author: nyga
'''
import os
import pyrap

pyrap_path = os.path.normpath(os.path.join(os.path.dirname(pyrap.__file__), '..'))
if os.path.basename(pyrap_path).startswith('python'):
    pyrap_path = os.path.normpath(os.path.join(pyrap_path, '..'))
js_loc = os.path.join(pyrap_path, 'js')
html_loc = os.path.join(pyrap_path, 'html')
css_loc = os.path.join(pyrap_path, 'css')
rc_loc = os.path.join(pyrap_path, 'resource')
pwt_loc = os.path.join(pyrap_path, 'pyrap', 'pwt')
trdparty = os.path.join(pyrap_path, '3rdparty')
