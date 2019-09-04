# coding: utf-8
"""
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

import jsonschema
from dateutil import parser

# six.string_types
# Possible types for text data.
# This is basestring() in Python 2 and str in Python 3.
from yoyonel.twitter_scraper.tools.fct_json import DefaultValidatingDraft4Validator

string_types = str


def deunicodify_hook(pairs):
    new_pairs = []
    for key, value in pairs:
        if isinstance(value, str):
            value = value.encode('utf-8')
        if isinstance(key, str):
            key = key.encode('utf-8')
        new_pairs.append((key, value))
    return dict(new_pairs)


def find_env_var(var_name, arg_name_coded_as_json=None):
    """
    Load value for given env var name. Value is expected to be json-serialized
    if its name is in the arg_name_coded_as_json list.
    """
    env_var = os.environ.get(var_name) or os.environ.get(var_name.upper())
    if env_var:
        return (
            json.loads(env_var)
            if arg_name_coded_as_json and var_name in arg_name_coded_as_json
            else env_var
        )


class JsonType(object):

    def __init__(self, schema=None, insert_default_values=True):
        self.schema = schema
        self.insert_default_values = insert_default_values

    def __call__(self, arg):
        if arg is None:
            self.value = None
            return None
        try:
            self.value = json.loads(arg)
        except TypeError:
            self.value = json.load(arg)
        except:  # noqa
            raise argparse.ArgumentTypeError(
                "The argument '{}' is not a proper formatted JSON.\nRemember "
                "that you must use double quotes inside the argument and that"
                " special types are written null, true, false).".format(
                    arg))
        if self.schema is not None:
            self.check_validity()
        return self.value

    def check_validity(self):
        try:
            if self.insert_default_values:
                DefaultValidatingDraft4Validator(
                    self.schema
                ).validate(self.value)
            else:
                jsonschema.validate(self.value, self.schema)
        except jsonschema.ValidationError as e:
            raise argparse.ArgumentTypeError(str(e))


class FileType(object):
    _mapping = {
        'f': os.F_OK,
        'r': os.R_OK,
        'w': os.W_OK,
        # 'ex': os.EX_OK,
    }

    _reverse_mapping = {
        'f': 'Exist',
        'r': 'Read',
        'w': 'Write',
        'ex': 'Executable',
    }

    def __init__(self, mode='r'):
        if mode not in self._mapping:
            raise KeyError(
                "The given mode must be one of these: {}".format(
                    self._mapping.keys()))
        self.mode = mode

    def __call__(self, arg):
        if not os.path.exists(arg):
            raise argparse.ArgumentTypeError(
                "The given path ('{}') does not exist.".format(arg))

        if not os.access(arg, self._mapping[self.mode]):
            raise argparse.ArgumentTypeError(
                "The given path ('{}') does not have the right access "
                "permission (should be '{}').".format(
                    arg, self._reverse_mapping[self.mode]))
        return arg


class FileJsonType(JsonType):

    def __init__(self, schema=None, insert_default_values=True):
        super(FileJsonType, self).__init__(schema, insert_default_values)

    def __call__(self, arg):
        arg = FileType(mode='r')(arg)
        with open(arg) as json_file:
            return super(FileJsonType, self).__call__(json_file)


class DirectoryType(FileType):
    def __init__(self, mode='r'):
        super(DirectoryType, self).__init__(mode)

    def __call__(self, arg):
        arg = os.path.realpath(arg)
        arg = super(DirectoryType, self).__call__(arg)
        if not os.path.isdir(arg):
            raise argparse.ArgumentTypeError(
                "The given path ('{}') is not a directory.".format(arg)
            )
        return arg


class GlobType(object):
    def __init__(self, mode='r'):
        if mode not in FileType._mapping:
            raise KeyError(
                "The given mode must be one of these: {}".format(
                    FileType._mapping.keys()))
        self.mode = mode

    def __call__(self, arg):
        return [
            FileType(mode=self.mode)(file_path)
            for file_path in glob.glob(arg)
        ]


class OutputFileType(object):
    def __init__(self):
        pass

    def __call__(self, arg):
        # test if parent directory (of filepath) is writable
        DirectoryType(mode='w')(os.path.dirname(arg))
        return arg


class DecoderType(object):

    def __call__(self, arg):
        """
        Store arg and return self so as to be able to call decode method later
        """
        self.arg = arg
        return self

    def decode(self):
        """
        Default implementation does not decode anything, returns arg
        """
        return self.arg


class RegexType(DecoderType):
    _pattern = None

    def __init__(self):
        self.re_pattern = re.compile(self._pattern)

    def __call__(self, arg):
        if not self.re_pattern.match(arg):
            raise argparse.ArgumentTypeError(
                "This argument should use the following pattern: {}".format(
                    self.re_pattern.pattern))
        return super(RegexType, self).__call__(arg)


class DateType(object):
    def __call__(self, arg):
        if arg is None or arg == 'None':
            return None
        else:
            self.arg = arg
            return self.decode()

    def decode(self, start_or_end=None):
        # if start_or_end not in ['start', 'end']:
        #     start_or_end = self._start_or_end
        string_date = self.arg
        if isinstance(string_date, datetime.datetime):
            return string_date
        else:
            return parser.parse(string_date) if string_date else None


class StartDateType(DateType):
    _start_or_end = 'start'


class EndDateType(DateType):
    _start_or_end = 'end'


class SchemaType(RegexType):
    _pattern = r'^[\da-fA-F\-]{36}$'


class Parser(argparse.ArgumentParser):
    """
    Class to manage CLI
    """

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if (
                    not arg_string or
                    arg_string[0] not in self.fromfile_prefix_chars
            ):
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    with open(arg_string[1:]) as f:
                        json_args = json.load(
                            f,
                            object_pairs_hook=deunicodify_hook)
                    for i, j in json_args.items():
                        new_arg_strings.append('--' + str(i))
                        if isinstance(j, list) or isinstance(j, dict):
                            new_arg_strings.append(json.dumps(j))
                        else:
                            new_arg_strings.append(str(j))
                except IOError:
                    err = sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def add_date_args(self, required=False):
        self.add_argument(
            '-sd', '--start_date',
            type=StartDateType(), required=required,
            help="The start date of the process.",
        )
        self.add_argument(
            '-ed', '--end_date',
            type=EndDateType(), required=required,
            help="The end date of the process.",
        )

    def add_logger_args(self, required=False, default='debug'):
        self.add_argument(
            '-ll', '--log_level',
            type=str, required=required, default=default,
            choices=['debug', 'warning', 'info', 'error', 'critical'],
            help="The logger filter level.",
        )
        self.add_argument(
            '-lf', '--log_file',
            type=str, required=required,
            help="The path to the file into which the logs will be streamed.",
        )

    def __init__(self, name=None):
        super(Parser, self).__init__(prog=name, fromfile_prefix_chars='@')
        self.name = name

    def parse_args(self, args=None, namespace=None):
        """
        Override the default parse_args() method to add environment variables.
        """
        # Add environment variables in front of other arguments so their
        # priority is lower
        env_args = []
        for i in self._actions:
            env_var = find_env_var(i.dest)
            if env_var is not None:
                env_args.append(i.option_strings[-1])
                env_args.append(env_var)

        # Get args from sys.argv
        if args is None:
            # args default to the system args
            args = sys.argv[1:]
        else:
            # make sure that args are mutable
            args = list(args)

        # Concatenate args
        all_args = env_args + args

        # Call argparse.Parser.parse_args()
        args = super(Parser, self).parse_args(
            args=all_args, namespace=namespace)

        # Decode arguments of type DecoderType
        for key, value in args.__dict__.items():
            if isinstance(value, DecoderType):
                args.__dict__[key] = value.decode()

        return args
