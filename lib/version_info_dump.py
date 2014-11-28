"""
NOTE: This module has sideeffects on import. This is by intention.

It collects information about the tool (main script file) and dumps it
in the current directory in a file called "versioninfo".

The info is intended to stay mostly fixed, if you keep using the same tool
with the same version.
So, it is intended to keep the file also under local version control
for documentation, so that you can later know what tool version you have used.
This is why we don't include information like the current system time.
For such purpose, use some local history script.
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
	info["file"] = filenameRepr(scriptfile)
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
		info["git-dir"] = filenameRepr(gitdir)
	
	if not gitdir or gitIsDirty:
		info["file-changeDate"] = sysexecOut("ls", "-la", os.path.basename(scriptfile), cwd=scriptdir).strip()

	return info

def myFileRepr():
	filename = os.path.realpath(__file__)
	if filename.endswith(".pyc"):
		filename = filename[:-1]
	return filenameRepr(filename)
	
def dump():
	info = collectInfo()
	cwd = os.getcwd()
	filename = cwd + "/versioninfo"
	t = ""
	try:
		t = open(filename).read()
	except IOError:
		# File does not exist yet or so.
		pass
	if t:
		tools = eval(t)
		test(type(tools) is dict)
	else:
		tools = {}
	tools[info["name"]] = info
	r = "# Version info of tools called from this dir.\n"
	r += "# Ref: " + myFileRepr() + "\n"
	r += betterRepr(tools)
	r += "\n"
	tmpfilename = filename + ".tmp" + tmp_filename()
	f = open(tmpfilename, "w")
	f.write(r)
	f.close()
	os.rename(tmpfilename, filename)
	
try:
	if os.path.exists(os.path.expanduser("~/.version_info_dump.enabled")):
		dump()
except IOError:
	# Permission denied or so.
	# Silently ignore.
	pass
