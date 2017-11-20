import os
import sys

from _version import __version__

import locations
import submodules

import mimetypes
mimetypes.init([os.path.join(locations.pyrap_path, 'etc', 'mime.types')] + mimetypes.knownfiles)

from base import register_app, register
from base import run
from base import session