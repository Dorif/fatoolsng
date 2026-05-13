from sys import argv, exit as sys_exit
from importlib import import_module


def greet():
    print('fatoolsng - Python-based DNA fragment-analysis tools')


def usage():
    print('Usage:')
    print(f'\t{argv[0]} command [options]')
    sys_exit(0)


def main():
    greet()
    if len(argv) >= 3:
        command = argv[1]
        opt_args = argv[2:]
        print(f'Running command: {command}')
        try:
            M = import_module('fatoolsng.scripts.' + command)
        except ImportError:
            print(f'Cannot import script name: {command}')
            raise
        parser = M.init_argparser()
        args = parser.parse_args(opt_args)
        M.main(args)
    else:
        print('Insufficient arguments. Please, read fatoolsng manual.')
        sys_exit(1)
