#!/usr/bin/env python3


"""
This will clean up disk space.

So far, we only clean up "safe" things, like caches, etc.
"""

import os



dirs = [
    "~/.config/google-chrome/Default/Service Worker/CacheStorage",
    # also Chrome Extensions, clean up old versions...
    "~/.config/fish/.nfs*",  # old unused files...
    # ~/.linuxbrew/Cellar/... but I use some of the stuff...
    # ~/setups  # not sure how to cleanup... move to archive?
    #   however, many git dirs there, which cloned from each other. merge the git objects?
    # ~/.local/lib/python*  ... I use that stuff... 2.7GB (biggest: Torch + TF)
    # ~/.local/share/JetBrains ... I use that, 1.15GB
    "~/.local/share/Trash/*",
    # py-envs...
    # Documents-archive...
    ]



for d in dirs:
    pass


commands = [
    "brew cleanup",
    "balooctl config set contentIndexing no",
    "balooctl disable", "balooctl purge",
]

raise NotImplementedError  # still wip...

