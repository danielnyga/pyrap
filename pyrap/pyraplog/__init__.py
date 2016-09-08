import logging
from logging import *
from logformat import RainbowLoggingHandler
import sys

from logging import DEBUG as debug
from logging import INFO as info
from logging import WARNING as warning
from logging import ERROR as error
import os
import traceback
from pyrap.utils import caller

root_logger = getLogger()

class MyLoggerAdapter(object):

    def __init__(self, logger):
        self._logger = logger
        self._logger.findCaller = self._caller
        
    def _caller(self):
        return caller(4)
        
    def critical(self, *args, **kwargs):
        self._logger.critical(' '.join(map(str, args)), extra=kwargs)

    def exception(self, *args, **kwargs):
        self._logger.exception(' '.join(map(str, args)), extra=kwargs)

    def error(self, *args, **kwargs):
        self._logger.error(' '.join(map(str, args)), extra=kwargs)

    def warning(self, *args, **kwargs):
        self._logger.warning(' '.join(map(str, args)), extra=kwargs)

    def info(self, *args, **kwargs):
        self._logger.info(' '.join(map(str, args)), extra=kwargs)

    def debug(self, *args, **kwargs):
        self._logger.debug(' '.join(map(str, args)), extra=kwargs)

    def __getattr__(self, attr):
        return getattr(self._logger, attr)

    @property
    def level(self):
        return self._logger.level
    
    @level.setter
    def level(self, l):
        self._logger.setLevel(l)

def getlogger(name=None, level=None):
    logger = MyLoggerAdapter(getLogger(name))
    if level:
        logger.level = level
    return logger


def level(level):
    getLogger().setLevel(level)


def loglevel(level, logger=None):
    if logger is None:
        getLogger().setLevel(level)
    else:
        getlogger(logger).level = level

handler = RainbowLoggingHandler(sys.stdout)
formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root_logger.addHandler(handler)

