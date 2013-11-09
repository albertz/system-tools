#!/usr/bin/env python

from utils import *
import config
import os, sys


def main(argv):
	projname = argv[1]
	pycmd(os.mkdir, projname)



if __name__ == "__main__":
	main(sys.argv)


