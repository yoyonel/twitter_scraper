# coding=utf-8
"""
"""
import logging
from typing import Optional

import coloredlogs

from yoyonel.twitter_scraper.tools.tqdm_logger import TqdmLoggingHandler


class IndentedLogger(logging.getLoggerClass()):
    tab_size = 4

    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, name, log_level='info', log_file=None):

        super(IndentedLogger, self).__init__(name)
        # init name, levels, and handlers
        self.setLevel(
            self.levels[log_level]
            if log_level in self.levels else logging.DEBUG
        )

        self.handlers = []
        self.handler = logging.StreamHandler()
        self.addHandler(self.handler)

        if log_file is not None:
            self.file_handler = logging.FileHandler(log_file)
            self.addHandler(self.file_handler)

        # init indent level and format
        self.__indent = 0  # No message indentation by default
        self.__update_format()

    @property
    def indent(self):
        return self.__indent

    @indent.setter
    def indent(self, indent):
        self.__indent = indent
        self.__update_format()

    def increase_indent(self, n=1):
        assert n >= 0
        self.indent += n * self.tab_size

    def decrease_indent(self, n=1):
        assert n >= 0
        self.__indent = max(0, self.__indent - n * self.tab_size)

    def __update_format(self):
        indent_str = ''.join([' '] * self.__indent)
        LOG_FORMAT = (
                '%(asctime)s - %(name)-13s - %(levelname)-8s : '
                + indent_str
                + '%(message)s'
        )
        LOG_DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        for handler in self.handlers:
            handler.setFormatter(formatter)


def create_logger(logger_name: str, log_level: str = 'info',
                  log_file: Optional[str] = None):
    """Creates a new logger handler

    :param logger_name:
    :type logger_name: str
    :param log_level: the logging level. Must be one of
        ["debug", "info", "warning", "error", "critical"]
    :type log_level: str
    :param log_file: contains the path to the file to store logging outputs
    :type log_file: str
    :author: ABE
    """
    return IndentedLogger(logger_name, log_level, log_file)


def init_logger(log_level):
    log_level = IndentedLogger.levels[log_level]

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = coloredlogs.ColoredFormatter(fmt=log_format)
    #
    tqdm_logging_handler = TqdmLoggingHandler(level=log_level)
    tqdm_logging_handler.setFormatter(formatter)

    handlers = [tqdm_logging_handler]

    logging.basicConfig(format=log_format, level=log_level, handlers=handlers)
