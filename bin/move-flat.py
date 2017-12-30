#!/usr/bin/env python3


import better_exchook
import os
import shutil
from argparse import ArgumentParser
from lib.ui import ConfirmByUserOptOnce


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("path", default=".", nargs="?")
    arg_parser.add_argument("--target_dir", help="target for files. default is the same as path.")
    arg_parser.add_argument("--join_str", default="__")
    arg_parser.add_argument("--no_dir_deletion", action="store_true")
    arg_parser.add_argument("--dry_run", action="store_true")
    arg_parser.add_argument("--verbose", action="store_true")
    arg_parser.add_argument("--all_confirmed", action="store_true")
    args = arg_parser.parse_args()
    if not args.target_dir:
        args.target_dir = args.path
    assert os.path.sep not in args.join_str
    assert args.path
    assert args.target_dir
    confirm = ConfirmByUserOptOnce(
        dry_run=args.dry_run, verbose=args.verbose, confirmed=args.all_confirmed)
    print("Collecting files in %r." % args.path)
    file_names = []  # type: list[str]
    dir_names = []  # type: list[str]
    for dir_path, sub_dir_names, sub_file_names in os.walk(args.path, topdown=False):
        if os.path.samefile(dir_path, args.path):
            continue
        file_names += [os.path.join(dir_path, fn) for fn in sub_file_names]
        dir_names += [os.path.join(dir_path, fn) for fn in sub_dir_names]
    print("Found %i files and %i directories." % (len(file_names), len(dir_names)))
    for fn in file_names:
        target_fn = fn
        assert target_fn.startswith(args.path + os.path.sep)
        target_fn = target_fn[len(args.path + os.path.sep):]
        target_fn = target_fn.replace(os.path.sep, args.join_str)
        target_fn = os.path.join(args.target_dir, target_fn)
        assert not os.path.exists(target_fn)
        confirm.call_custom(shutil.move, (fn, target_fn))
    for fn in dir_names:
        confirm.call_custom(os.rmdir, (fn,))
    print("Done.")


if __name__ == "__main__":
    better_exchook.install()
    main()
