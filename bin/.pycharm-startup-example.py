"""
Move this file to ~/.pycharm-startup.py.

This file is run via system-tools/bin/pycharm.
"""

import os

# https://github.com/fritzw/ld-preload-open
os.environ["LD_PRELOAD"] = "/u/zeyer/code/ld-preload-open/path-mapping-quiet.so"
# os.environ["LD_PRELOAD"] = "/u/zeyer/code/ld-preload-open/path-mapping.so"
os.environ["PATH_MAPPING"] = ":".join(
    f"{p}:/dev/null" for p in [
        "/work/common",
        "/work/asr4",
        "/u/zeyer/setups/combined/2021-05-31/setup-data-dir-symlink",
        "/u/zeyer/setups/combined/2021-05-31/work",
        "/u/zeyer/setups/combined/2021-05-31/alias",
        "/u/zeyer/setups/combined/2021-05-31/output",
    ])
