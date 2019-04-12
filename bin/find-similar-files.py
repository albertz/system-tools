#!/usr/bin/env python3


import os
import argparse
import better_exchook
import inspect
from glob import glob
import subprocess


def get_source_files(target_file, source_dir, source_pattern):
    """
    :param str target_file:
    :param str|None source_dir:
    :param str|None source_pattern:
    :rtype: list[str]
    """
    if source_dir is None:
        source_dir = os.path.dirname(target_file)
    if source_pattern is None:
        source_pattern = "*"
    if source_dir:
        source_pattern = "%s/%s" % (source_dir, source_pattern)
    source_files = glob(source_pattern)
    source_files.sort()
    if target_file in source_files:
        source_files.remove(target_file)
    return source_files


def get_diff_score(source_fn, target_fn):
    """
    Ways how to compare:

    * Use diff output in some way. But diff is line-based.
      * https://unix.stackexchange.com/questions/81998/understanding-of-diff-output
    * Use some other utility which does char-by-char diffs (but which?).
    * Use Python difflib. However, this is probably much slower than the cmd-line diff.
      We can however still use that for line-by-line comparison.

    :param str source_fn:
    :param str target_fn:
    :rtype: int|float
    """
    # diff returns 0 if same, 1 if different, sth else if other error.
    proc = subprocess.Popen(["diff", source_fn, target_fn], stdout=subprocess.PIPE)
    out, _ = proc.communicate()
    if proc.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(returncode=proc.returncode, cmd=proc.args, output=out)
    assert isinstance(out, bytes)
    return len(out)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("target_file", help="search for other files which are similar to this target file")
    arg_parser.add_argument("--source_dir", help="directory where to search for files")
    arg_parser.add_argument("--source_pattern", help="use glob(pattern) to search for files")
    args = arg_parser.parse_args()
    source_files = get_source_files(**{arg: getattr(args, arg) for arg in inspect.getargspec(get_source_files).args})
    print("Checking %i source files." % len(source_files))
    scores_with_fns = [(get_diff_score(source_fn, args.target_file), source_fn) for source_fn in source_files]
    scores_with_fns.sort()
    best_n = min(len(source_files), 5)
    print("Best %i matches:" % best_n)
    for score, fn in scores_with_fns[:best_n]:
        print("%s (diff score %s)" % (fn, score))
    best_fn = scores_with_fns[0][1]
    print("Diff of best file (%s):" % (os.path.basename(best_fn)))
    subprocess.Popen(["diff", "-u", best_fn, args.target_file]).wait()


if __name__ == '__main__':
    better_exchook.install()
    main()

