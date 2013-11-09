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

	server = config.get_private_server()
	projdir = config.get_private_remote_projectdir()
	shellcmd("ssh %s mkdir %s/%s.git" % (server, projdir, projname))
	shellcmd("rsync -a .git/* %s:%s/%s.git/" % (server, projdir, projname))

if __name__ == "__main__":
	main(sys.argv)


