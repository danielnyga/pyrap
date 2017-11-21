import os
import sys

from pyrap import locations

trdparty_modules = ['webpy']

for mod in trdparty_modules:
    if mod not in sys.path:
        sys.path.insert(0, os.path.join(locations.trdparty, mod))

sys.path.insert(0, locations.pyrap_path)