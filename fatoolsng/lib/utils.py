from __future__ import annotations

from sys import stdout, stderr, exit as sys_exit
from base64 import b64encode
from os import urandom
from math import ceil
from typing import Any, NoReturn


def cout(s: str, nl: bool = True, flush: bool = False) -> None:
    stdout.write(s)
    if nl:
        stdout.write('\n')
    if flush:
        stdout.flush()


def cerr(s: str, nl: bool = True, flush: bool = False) -> None:
    stderr.write(s)
    if nl:
        stderr.write('\n')
    if flush:
        stderr.flush()


def cexit(s: str, code: int = 1) -> NoReturn:
    cerr(s)
    sys_exit(code)


_VERBOSITY_ = 0


def set_verbosity(value: int) -> None:
    global _VERBOSITY_
    _VERBOSITY_ = value


def is_verbosity(value: int) -> bool:
    global _VERBOSITY_
    return (_VERBOSITY_ >= value)


def cverr(value: int, txt: str, nl: bool = True, flush: bool = False) -> None:
    global _VERBOSITY_
    if _VERBOSITY_ >= value:
        cerr(txt, nl, flush)


def get_dbhandler(args: Any, initial: bool = False) -> Any:
    """ return suitable handler from args """

    if args.sqldb:
        from fatoolsng.lib.sqlmodels.handler import SQLHandler
        return SQLHandler(args.sqldb, initial)

    elif args.fsdb is not False:
        raise NotImplementedError('filesystem-based database is not supported')

    cerr('ERR: Please specify database system using --sqldb or --fsdb options!')
    sys_exit(1)


def tokenize(options: str, converter: Any = None) -> dict[str, Any]:
    """ return { 'A': '1,2,3', 'B': True } for options 'A=1,2,3;B' """
    opt_dict: dict[str, Any] = {}
    for token in options.split(';'):
        keys = token.split('=', 1)
        if len(keys) == 1:
            opt_dict[keys[0].strip()] = True
        else:
            opt_dict[keys[0].strip()] = keys[1].strip()

    return opt_dict


def random_string(n: int) -> str:
    return b64encode(urandom(int(ceil(0.75*n))), b'-_')[:n].decode('UTF-8')


_R_lock_ = None


def acquire_R():

    global _R_lock_
    if _R_lock_ is None:

        # initialize rpy2 and set thread lock

        from rpy2.robjects import pandas2ri
        import threading

        pandas2ri.activate()
        _R_lock_ = threading.Lock()
    _R_lock_.acquire()


def release_R():

    global _R_lock_

    _R_lock_.release()

# utility to deal with tab or comma delimited text buffer


def detect_buffer(buf):
    """ return (buf, delimiter) """

    # find our new line character, this is for Mac Excel blunder

    n_count = buf.count('\n')
    r_count = buf.count('\r')

    if n_count == 0 and r_count > 0:
        # Mac Excel
        buf = buf.replace('\r', '\n')
        n_count = r_count
    elif r_count > n_count:
        raise RuntimeError('Invalid text content')

    # we detect delimiter
    tab_count = buf.count('\t')
    comma_count = buf.count(',')

    if comma_count > tab_count and comma_count > n_count:
        return (buf, ',')
    return (buf, '\t')
