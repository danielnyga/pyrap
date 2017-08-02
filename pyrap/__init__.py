import os
import sys

from . import locations
from . import submodules

import mimetypes
mimetypes.init([os.path.join(os.path.dirname(__file__), '..', 'etc', 'mime.types')] + mimetypes.knownfiles)

from .base import register_app
from .base import run
from .base import session