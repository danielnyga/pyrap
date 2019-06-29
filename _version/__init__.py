"""
_version
Version information for pracmln.
"""
import sys

__all__ = [
    'VERSION_MAJOR',
    'VERSION_MINOR',
    'VERSION_PATCH',
    'VERSION_STRING_FULL',
    'VERSION_STRING_SHORT',
    '__version__'
]

APPNAME = 'pyrap'
APPAUTHOR = 'pyrap.org'

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 1

VERSION_STRING_FULL = '%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
VERSION_STRING_SHORT = '%s.%s' % (VERSION_MAJOR, VERSION_MINOR)

__version__ = VERSION_STRING_FULL
