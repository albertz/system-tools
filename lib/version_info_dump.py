"""
NOTE: This module has sideeffects on import. This is by intention.

It collects information about the tool (main script file) and dumps it
in the current directory in "$toolname.versioninfo".

The info is intended to stay mostly fixed, if you keep using the same tool
with the same version.
So, it is intended to keep the "*.versioninfo" also under version control,
so that you can later know what tool version you have used.
"""

from .utils import *
import os

def findMainScript():
	import inspect
	first = inspect.stack()[-1]
	filepath = first[1]
	# Check if filepath is valid.
	# I'm not sure what to do if that fails.
	# Some fallback code would be good.
	test(os.path.exists(filepath))
	return filepath

def gitTopLevelOrNone(d):
	try:
		return git_topLevelDir(gitdir=d)
	except ShellError:
		return None

def collectInfo():
	info = {}
	
	scriptfile = findMainScript()
	scriptname = os.path.basename(scriptfile)
	if scriptname.endswith(".py"): scriptname = scriptname[:-3]
	scriptfile = os.path.realpath(scriptfile)
	scriptfile = os.path.abspath(scriptfile)
	test(os.path.isfile(scriptfile))
	info["file"] = scriptfile
	info["name"] = scriptname
	scriptdir = os.path.dirname(scriptfile)
	
	gitdir = gitTopLevelOrNone(scriptdir)
	gitIsDirty = None
	if gitdir:
		gitCommit = git_headCommit(gitdir=gitdir)
		gitIsDirty = git_isDirty(gitdir=gitdir)
		gitDate = git_commitDate(gitdir=gitdir)
		info["git-commit"] = gitCommit
		info["git-isDirty"] = gitIsDirty
		info["git-date"] = gitDate
		info["git-dir"] = gitdir
	
	if not gitdir or gitIsDirty:
		info["file-changeDate"] = sysexecOut("ls", "-la", scriptfile).strip()

	return info

def dump():
	info = collectInfo()
	cwd = os.getcwd()
	filename = cwd + "/" + info["name"] + ".versioninfo"
	f = open(filename, "w")
	f.write(betterRepr(info))
	f.write("\n")
	f.close()
	
try:
	dump()
except IOError:
	# Permission denied or so.
	# Silently ignore.
	pass
