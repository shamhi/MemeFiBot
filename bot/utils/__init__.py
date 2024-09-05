from .logger import logger
from . import launcher
from . import graphql
from . import boosts


import os

#There should be no argument attached to the os.path.exists()
if not os.path.exists('sessions'):
    os.makedirs('sessions')
