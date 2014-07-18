#!/usr/bin/env python

import os, sys

if __package__ is None:
	__package__ = "%s.%s" % (os.path.basename(os.path.dirname(os.path.abspath(__file__))), os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0])

from utils import *
import config


def main(argv):
	projname = argv[1]
	pycmd(os.mkdir, projname)
	pycmd(os.chdir, projname)
	shellcmd("git init")
	shellcmd("echo '# %s\n\nInitial Readme.\n' > README.md" % projname)
	shellcmd("git add README.md")
	shellcmd("git commit -m 'initial commit'")

	server = config.get_private_server()
	projdir = config.get_private_remote_projectdir() + "/" + projname + ".git"
	shellcmd("ssh %s 'mkdir %s && cd %s && git init --bare'" % (server, projdir, projdir))
	shellcmd("git remote add origin %s" % get_ssh_fileurl(server, projdir))
	shellcmd("git push -u origin master")

if __name__ == "__main__":
	main(sys.argv)


