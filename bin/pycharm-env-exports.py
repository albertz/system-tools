#!/usr/bin/env python3

from typing import Optional, Set
import os
import sys
import argparse
import importlib


def exec_python_module_from_file(filename: str):
    # https://stackoverflow.com/questions/67631/how-do-i-import-a-module-given-the-full-path
    module_name = filename  # does not matter
    spec = importlib.util.spec_from_file_location(module_name, filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)


def main():
    if not os.path.exists(os.path.expanduser('~/.pycharm-startup.py')):
        return

    old_env = os.environ.copy()
    exec_python_module_from_file(os.path.expanduser('~/.pycharm-startup.py'))

    for key, value in os.environ.items():
        if value != old_env.get(key):
            print(f"export {key}={value}")


if __name__ == "__main__":
    main()
