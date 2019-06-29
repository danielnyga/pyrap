'''
Created on Oct 2, 2015

@author: nyga
'''
from pyrap.web.webapi import HTTPError

class RWTError(Exception): pass

class WidgetDisposedError(RWTError): pass

class ResourceError(Exception): pass

class LayoutError(Exception): pass

class Forbidden(HTTPError):
    """`403 Forbidden` error."""
    def __init__(self, message):
        status = "403 Forbidden"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message)

forbidden = Forbidden