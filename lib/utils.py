
import os, sys
from . import ui

# It's bad practice to have an import-sideeffect.
# However, these are anyway only small helper tools and this is useful.
from . import better_exchook
better_exchook.install()


IsPython2 = sys.version_info[0] <= 2


class CachedFunc0Deco(object):
	def __init__(self, func):
		self.func = func
	def __call__(self):
		self.value = self.func()
		self.__call__ = lambda: self.value
		return self.value


def betterRepr(o):
	"""
	The main difference: this one is deterministic,
	the orig dict.__repr__ has the order undefined.
	Also, the output is minimally formatted.
	Also, this tries to output such that we can import
	with both Python 2+3.
	"""
	# Recursive structures.
	if isinstance(o, list):
		return "[" + ", ".join(map(betterRepr, o)) + "]"
	if isinstance(o, tuple):
		return "(" + ", ".join(map(betterRepr, o)) + ")"
	# Sort dict. And format.
	if isinstance(o, dict):
		return "{\n" + "".join([betterRepr(k) + ": " + betterRepr(v) + ",\n" for (k,v) in sorted(o.items())]) + "}"
	# Handle Python2 unicode to not print prefix 'u'.
	if IsPython2 and isinstance(o, unicode):
		s = o.encode("utf8")
		s = repr(s)
		if "\\x" in s: # Simple hacky check: Do we need unicode?
			return "%s.decode('utf8')" % s
		return s
	# fallback
	return repr(o)


class ShellError(Exception):
	def __init__(self, res):
		self.exitCode = res
		assert self.exitCode != 0
		super().__init__("exit code %i" % self.exitCode)
		
@ui.ConfirmByUserDeco
def shellcmd(cmd):
	useshell=False
	if type(cmd) is str: useshell=True
	import subprocess
	res = subprocess.call(cmd, shell=useshell)
	if res != 0: raise ShellError(res)

@ui.ConfirmByUserDeco
def pycmd(func, *args, **kwargs):
	return func(*args, **kwargs)

def sysexec(*args, **kwargs):
	import subprocess
	res = subprocess.call(args, shell=False, **kwargs)
	if res != 0: raise ShellError(res)

def sysexecOut(*args, **kwargs):
	from subprocess import Popen, PIPE
	p = Popen(args, shell=False, stdin=PIPE, stdout=PIPE, **kwargs)
	out, _ = p.communicate()
	if p.returncode != 0: raise ShellError(p.returncode)
	out = out.decode("utf-8")
	return out

def sysexecRetCode(*args, **kwargs):
	import subprocess
	res = subprocess.call(args, shell=False, **kwargs)
	valid = kwargs.get("valid", (0,1))
	if valid is not None:
		if res not in valid: raise ShellError(res)
	return res


def git_topLevelDir(gitdir=None):
	d = sysexecOut("git", "rev-parse", "--show-toplevel", cwd=gitdir).strip()
	test(os.path.isdir(d))
	test(os.path.isdir(d + "/.git"))
	return d

def git_headCommit(gitdir=None):
	return sysexecOut("git",  "rev-parse", "--short", "HEAD", cwd=gitdir).strip()

def git_commitRev(commit="HEAD", gitdir="."):
	if commit is None: commit = "HEAD"
	return sysexecOut("git", "rev-parse", "--short", commit, cwd=gitdir).strip()
	
def git_isDirty(gitdir="."):
	r = sysexecRetCode("git", "diff", "--no-ext-diff", "--quiet", "--exit-code", cwd=gitdir)
	if r == 0: return False
	if r == 1: return True
	test(False)

def git_commitDate(commit="HEAD", gitdir="."):
	return sysexecOut("git", "show", "-s", "--format=%ci", commit, cwd=gitdir).strip()[:-6].replace(":", "").replace("-", "").replace(" ", ".")


def utc_datetime_str():
	from datetime import datetime
	return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def utc_datetime_filenamestr():
	from datetime import datetime
	return datetime.utcnow().strftime("%Y%m%d.%H%M%S")


def make_symlink(src, dst):
	test(src)
	abssrc = os.path.join(os.path.dirname(dst), src) if src[:1] != "/" else src
	test(os.path.exists(abssrc), "the link destination %s does not exists" % src)
	if os.path.islink(dst):
		curlink = os.readlink(dst)
		test(curlink == src, "existing missmatching symlink: %s -> %s" % (dst, curlink))
	else:
		os.symlink(src, dst)

def make_dir(dst, recursive=False):
	if not os.path.isdir(dst):
		print("Directory %r does not exist, create..." % dst)
		if recursive:
			os.makedirs(dst)
		else:
			os.mkdir(dst)

def tmp_filename():
	"Some random string which is usable as (part of) a temporary filename."
	import uuid
	return str(uuid.uuid4())

def homesDir():
	"Returns the base directory of user home directories."
	if sys.platform == "darwin":
		return "/Users"
	else:
		# POSIX-like fallback
		return "/home"
	
def loginUsername():
	"""
	Returns the username of the current user.
	Use this as a replacement for os.getlogin().
	"""
	import pwd, os
	return pwd.getpwuid(os.getuid())[0]
	
def filenameRepr(filename, currentUser=False):
	"Some os.path.expanduser filename representation."
	homesdir = os.path.realpath(homesDir()) + "/"
	if filename.startswith(homesdir):
		username = filename[len(homesdir):].split("/")[0]
		prefix = "~%s" % username
		homedir = os.path.realpath(os.path.expanduser(prefix))
		prefix += "/"
		homedir += "/"
		if filename.startswith(homedir):
			if currentUser and username == loginUsername():
				return "~/" + filename[len(homedir):]
			return prefix + filename[len(homedir):]
	# Fallback.
	return filename
	

def test_server(servername):
	import subprocess
	res = subprocess.call("ping -c 1 %s >/dev/null" % servername, shell=True)
	assert res == 0
	return True

def test_remotedir(remotedir):
	import urlparse
	o = urlparse.urlparse(remotedir)
	assert o.scheme == "ssh"
	assert test_server(o.hostname)
	args = ["ssh", o.hostname]
	if o.port:
		args += ["-p", str(o.port)]
	assert o.path != ""
	path = o.path
	args += ["stat", path]
	args += [">/dev/null"]

	import subprocess
	res = subprocess.call(" ".join(args), shell=True)
	assert res == 0
	return True

# This is just like `assert`, except that it will not be optimized away.
def test(value, msg=None):
	if not value:
		raise AssertionError(*((msg,) if msg else ()))
	
def get_homeremotedir(server):
	import subprocess
	return subprocess.check_output(["ssh", server, "pwd"]).strip("\n")

def get_ssh_fileurl(server, remotedir, homeremotedir=None):
	assert remotedir != ""
	if remotedir[0] != "/":
		if not homeremotedir:
			homeremotedir = get_homeremotedir(server)
			assert homeremotedir[0:1] == "/"
		remotedir = homeremotedir + "/" + remotedir
	return "ssh://%s%s" % (server, remotedir)
