#!/usr/bin/env python3

"""
Given one source directory, and one destination directory,
find same files (assuming same relative names),
and for all same files,
remove the destination and replace it by a hardlink to the source.
This will save space.
"""

import os
import argparse


class Handler:
    def __init__(self) -> None:
        self.same_byte_count = 0

    def handle_file_same_content(self, src_prefix, dst_prefix, name):
        src_path = os.path.join(src_prefix, name)
        dst_path = os.path.join(dst_prefix, name)
        self.same_byte_count += get_file_size(src_path)
        dst_dir = os.path.dirname(dst_path)
        dst_name = os.path.basename(dst_path)
        dst_tmp_path = dst_dir + "/." + dst_name + ".tmpMergeIdenticalFiles"
        os.link(src=src_path, dst=dst_tmp_path)
        os.unlink(dst_path)
        os.rename(dst_tmp_path, dst_path)


def check_files(src_prefix, dst_prefix, name, *, handler):
    src_path = os.path.join(src_prefix, name)
    dst_path = os.path.join(dst_prefix, name)
    assert os.path.isdir(src_path), f"{src_path} is not a directory"
    assert os.path.isdir(dst_path), f"{dst_path} is not a directory"
    src_files = os.listdir(src_path)
    dst_files = os.listdir(dst_path)
    dst_files_set = set(dst_files)
    common_files = [f for f in src_files if f in dst_files_set]
    for f in common_files:
        sub_name = (name + "/" + f) if name else f
        src_f = os.path.join(src_path, f)
        dst_f = os.path.join(dst_path, f)
        if os.path.isdir(src_f):
            if os.path.isdir(dst_f):
                check_files(src_prefix=src_prefix, dst_prefix=dst_prefix, handler=handler, name=sub_name)
            else:
                print(f"WARNING: src {sub_name} is a dir but {dst_f} is not?")
        elif os.path.isfile(src_f) and not os.path.islink(src_f):
            if os.path.isfile(dst_f):
                if os.path.samefile(src_f, dst_f):
                    pass  # nothing needs to be done
                elif os.path.islink(dst_f):
                    print(f"WARNING: src {sub_name} is a reg file but {dst_f} is a symlink?")
                elif has_same_content(src_f, dst_f):
                    handler.handle_file_same_content(src_prefix=src_prefix, dst_prefix=dst_prefix, name=sub_name)
            else:
                print(f"WARNING: src {sub_name} is a file but {dst_f} is not?")
        # Skip other types


def get_file_size(fn):
    return os.stat(fn).st_size


def has_same_content(src_fn, dst_fn):
    src_stat = os.stat(src_fn)
    dst_stat = os.stat(dst_fn)
    if src_stat.st_size != dst_stat.st_size:
        return False
    N = 1024 * 1024
    with open(src_fn, "rb") as src_f, open(dst_fn, "rb") as dst_f:
        while True:
            src_data = src_f.read(N)
            dst_data = dst_f.read(N)
            if src_data != dst_data:
                return False
            if not src_data:
                break
    return True


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--source", required=True)
    arg_parser.add_argument("--dest", required=True, help="Will be modified!")
    args = arg_parser.parse_args()

    handler = Handler()
    check_files(src_prefix=args.source, dst_prefix=args.dest, name="", handler=handler)

    print(f"Same byte count: {handler.same_byte_count / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    try:
        import better_exchook
        better_exchook.install()
    except ImportError:
        pass
    main()
