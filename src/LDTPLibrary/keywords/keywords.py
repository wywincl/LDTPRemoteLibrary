#  Copyright 2008-2014 Nokia Solutions and Networks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import re
import sys
import inspect
import traceback
from StringIO import StringIO
from xmlrpclib import Binary

import ldtp

try:
    import signal
except ImportError:
    signal = None
try:
    from collections import Mapping
except ImportError:
    Mapping = dict

__version__ = 'devel'

BINARY = re.compile('[\x00-\x08\x0B\x0C\x0E-\x1F]')
NON_ASCII = re.compile('[\x80-\xff]')


class LDTPDynamicKeywords(object):
    allow_reuse_address = True
    _generic_exceptions = (AssertionError, RuntimeError, Exception)
    _fatal_exceptions = (SystemExit, KeyboardInterrupt)

    def __init__(self):
        self._ldtp = ldtp

    def get_keyword_names(self):
        names = [attr for attr in dir(self._ldtp) if attr[0] != '_']
        # print names
        return names

    def _is_function_or_method(self, item):
        # Cannot use inspect.isroutine because it returns True for
        # object().__init__ with Jython and IronPython
        return inspect.isfunction(item) or inspect.ismethod(item)

    def run_keyword(self, name, args, kwargs=None):
        args, kwargs = self._handle_binary_args(args, kwargs or {})
        result = {'status': 'FAIL'}
        # print name, args, kwargs
        self._intercept_std_streams()
        try:
            return_value = self._get_keyword(name)(*args, **kwargs)
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self._add_to_result(result, 'error',
                                self._get_error_message(exc_type, exc_value))
            self._add_to_result(result, 'traceback',
                                self._get_error_traceback(exc_tb))
            self._add_to_result(result, 'continuable',
                                self._get_error_attribute(exc_value, 'CONTINUE'),
                                )
            self._add_to_result(result, 'fatal',
                                self._get_error_attribute(exc_value, 'EXIT'),
                                )
        else:
            try:
                self._add_to_result(result, 'return',
                                    self._handle_return_value(return_value))
            except:
                exc_type, exc_value, _ = sys.exc_info()
                self._add_to_result(result, 'error',
                                    self._get_error_message(exc_type, exc_value))
            else:
                result['status'] = 'PASS'
        self._add_to_result(result, 'output', self._restore_std_streams())
        return result

    def _handle_binary_args(self, args, kwargs):
        args = [self._handle_binary_arg(a) for a in args]
        kwargs = dict([(k, self._handle_binary_arg(v)) for k, v in kwargs.items()])
        return args, kwargs

    def _handle_binary_arg(self, arg):
        if isinstance(arg, Binary):
            return arg.data
        return arg

    def _add_to_result(self, result, key, value, default=''):
        if value != default:
            result[key] = value

    def get_keyword_arguments(self, name):
        kw = self._get_keyword(name)
        if not kw:
            return []
        return self._arguments_from_kw(kw)

    def _arguments_from_kw(self, kw):
        args, varargs, kwargs, defaults = inspect.getargspec(kw)
        if inspect.ismethod(kw):
            args = args[1:]  # drop 'self'
        if defaults:
            args, names = args[:-len(defaults)], args[-len(defaults):]
            args += ['%s=%s' % (n, d) for n, d in zip(names, defaults)]
        if varargs:
            args.append('*%s' % varargs)
        if kwargs:
            args.append('**%s' % kwargs)
        return args

    def get_keyword_documentation(self, name):
        if name == '__intro__':
            return inspect.getdoc(self._ldtp) or ''
        if name == '__init__' and inspect.ismodule(self._ldtp):
            return ''
        return inspect.getdoc(self._get_keyword(name)) or ''

    def _get_keyword(self, name):
        kw = getattr(self._ldtp, name, None)
        if not self._is_function_or_method(kw):
            return None
        return kw

    def _get_error_message(self, exc_type, exc_value):
        if exc_type in self._fatal_exceptions:
            self._restore_std_streams()
            raise
        name = exc_type.__name__
        message = self._get_message_from_exception(exc_value)
        if not message:
            return name
        if exc_type in self._generic_exceptions \
                or getattr(exc_value, 'ROBOT_SUPPRESS_NAME', False):
            return message
        return '%s: %s' % (name, message)

    def _get_message_from_exception(self, value):
        # UnicodeError occurs below 2.6 and if message contains non-ASCII bytes
        try:
            msg = unicode(value)
        except UnicodeError:
            msg = ' '.join([self._str(a, handle_binary=False) for a in value.args])
        return self._handle_binary_result(msg)

    def _get_error_traceback(self, exc_tb):
        # Latest entry originates from this class so it can be removed
        entries = traceback.extract_tb(exc_tb)[1:]
        trace = ''.join(traceback.format_list(entries))
        return 'Traceback (most recent call last):\n' + trace

    def _get_error_attribute(self, exc_value, name):
        return bool(getattr(exc_value, 'ROBOT_%s_ON_FAILURE' % name, False))

    def _handle_return_value(self, ret):
        if isinstance(ret, basestring):
            return self._handle_binary_result(ret)
        if isinstance(ret, (int, long, float)):
            return ret
        if isinstance(ret, Mapping):
            return dict([(self._str(key), self._handle_return_value(value))
                         for key, value in ret.items()])
        try:
            return [self._handle_return_value(item) for item in ret]
        except TypeError:
            return self._str(ret)

    def _handle_binary_result(self, result):
        if not self._contains_binary(result):
            return result
        try:
            result = str(result)
        except UnicodeError:
            raise ValueError("Cannot represent %r as binary." % result)
        return Binary(result)

    def _contains_binary(self, result):
        return (BINARY.search(result) or isinstance(result, str) and
                sys.platform != 'cli' and NON_ASCII.search(result))

    def _str(self, item, handle_binary=True):
        if item is None:
            return ''
        if not isinstance(item, basestring):
            item = unicode(item)
        if handle_binary:
            return self._handle_binary_result(item)
        return item

    def _intercept_std_streams(self):
        sys.stdout = StringIO()
        sys.stderr = StringIO()

    def _restore_std_streams(self):
        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
        close = [sys.stdout, sys.stderr]
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        for stream in close:
            stream.close()
        if stdout and stderr:
            if not stderr.startswith(('*TRACE*', '*DEBUG*', '*INFO*', '*HTML*',
                                      '*WARN*')):
                stderr = '*INFO* %s' % stderr
            if not stdout.endswith('\n'):
                stdout += '\n'
        return self._handle_binary_result(stdout + stderr)

    def _log(self, msg, level=None):
        if level:
            msg = '*%s* %s' % (level.upper(), msg)
        self._write_to_stream(msg, sys.stdout)
        if sys.__stdout__ is not sys.stdout:
            self._write_to_stream(msg, sys.__stdout__)

    def _write_to_stream(self, msg, stream):
        stream.write(msg + '\n')
        stream.flush()
