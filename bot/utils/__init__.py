from .logger import logger
from . import launcher
from . import graphql
from . import boosts
from . import scripts


import os

if not os.path.exists(path='sessions'):
    os.mkdir(path='sessions')
