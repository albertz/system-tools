#!/usr/bin/env python3

"""
Like `type` but for libs.
"""

from __future__ import print_function
from argparse import ArgumentParser
from glob import glob
import sys
import os


def parse_ld_conf_file(fn):
    paths = []
    for l in open(fn).read().splitlines():
        l = l.strip()
        if not l:
            continue
        if l.startswith("#"):
            continue
        if l.startswith("include "):
            for sub_fn in glob(l[len("include "):]):
                paths.extend(parse_ld_conf_file(sub_fn))
            continue
        paths.append(l)
    return paths


def get_ld_paths():
    # To be very correct, see man-page of ld.so.
    # And here: http://unix.stackexchange.com/questions/354295/what-is-the-default-value-of-ld-library-path/354296
    # Short version, not specific to an executable, in this order:
    # - LD_LIBRARY_PATH
    # - /etc/ld.so.cache (instead we will parse /etc/ld.so.conf)
    # - /lib, /usr/lib (or maybe /lib64, /usr/lib64)
    PREFIX = os.getenv("PREFIX") # Termux & etc.
    LDPATH = os.getenv("LD_LIBRARY_PATH") 
    paths = ["/lib", "/usr/lib", "/lib64", "/usr/lib64"]
    if LDPATH: 
        paths.extend(LDPATH.split(":"))
    if PREFIX:
        paths.extend([PREFIX + "/lib", PREFIX + "/usr/lib", PREFIX + "/lib64", PREFIX + "/usr/lib64"])
        if os.path.exists(PREFIX + "/etc/ld.so.conf"):
            paths.extend(parse_ld_conf_file(PREFIX + "/etc/ld.so.conf"))
        else:
            print("WARNING: file \"" + PREFIX + "/etc/ld.so.conf\" not found.")
    if os.path.exists("/etc/ld.so.conf"):
        paths.extend(parse_ld_conf_file("/etc/ld.so.conf"))
    else:
        print("WARNING: file \"/etc/ld.so.conf\" not found.")
    return paths


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("lib", help="Name of the library (e.g. libncurses.so)")
    args = arg_parser.parse_args()

    paths = get_ld_paths()
    for p in paths:
        fn = "%s/%s" % (p, args.lib)
        if os.path.exists(fn):
            print(fn)
            return

    print("Did not found %r in %r." % (args.lib, paths), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
