import os

from . import locations
from . import submodules

from _version import __version__

import mimetypes
mimetypes.init([os.path.join(os.path.dirname(__file__), '..', 'etc', 'mime.types')] + mimetypes.knownfiles)

from .base import register_app, register
from .base import run
from .base import session