#!/usr/bin/env python

from utils import *
import config
import os, sys


def main(argv):
	projname = argv[1]
	pycmd(os.mkdir, projname)
	pycmd(os.chdir, projname)
	shellcmd("git init")
	shellcmd("echo '# %s\n\nInitial Readme.\n' > README.md" % projname)
	shellcmd("git add README.md")
	shellcmd("git commit -m 'initial commit'")

if __name__ == "__main__":
	main(sys.argv)


