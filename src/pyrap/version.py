'''
Version information for pyrap.
'''
import logging
import os
import sys


__all__ = [
    'VERSION_MAJOR',
    'VERSION_MINOR',
    'VERSION_PATCH',
    'VERSION_STRING_FULL',
    'VERSION_STRING_SHORT',
    '__version__',
]

_version_fpath = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '.version'
)

try:
    with open(_version_fpath) as f:
        VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH = tuple(f.readline().split('.'))
except FileNotFoundError:
    logging.warning('Version file not found at %s' % _version_fpath)
    VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH = 1, 0, 1


VERSION_STRING_SHORT = '%s.%s' % (VERSION_MAJOR, VERSION_MINOR)
VERSION_STRING_FULL = '%s.%s' % (VERSION_STRING_SHORT, VERSION_PATCH)


__version__ = VERSION_STRING_FULL


if sys.version_info[0] < 3:
    raise Exception('Unsupported Python version: %s' % sys.version_info[0])
