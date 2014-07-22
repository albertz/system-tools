
import os, sys
from . import ui

# It's bad practice to have an import-sideeffect.
# However, these are anyway only small helper tools and this is useful.
from . import better_exchook
better_exchook.install()


class CachedFunc0Deco(object):
	def __init__(self, func):
		self.func = func
	def __call__(self):
		self.value = self.func()
		self.__call__ = lambda: self.value
		return self.value


def betterRepr(o):
	# the main difference: this one is deterministic
	# the orig dict.__repr__ has the order undefined.
	if isinstance(o, list):
		return "[" + ", ".join(map(betterRepr, o)) + "]"
	if isinstance(o, tuple):
		return "(" + ", ".join(map(betterRepr, o)) + ")"
	if isinstance(o, dict):
		return "{\n" + "".join([betterRepr(k) + ": " + betterRepr(v) + ",\n" for (k,v) in sorted(o.iteritems())]) + "}"
	# fallback
	return repr(o)


class ShellError(Exception): pass

@ui.ConfirmByUserDeco
def shellcmd(cmd):
	import subprocess
	res = subprocess.call(cmd, shell=True)
	if res != 0: raise ShellError

@ui.ConfirmByUserDeco
def pycmd(func, *args, **kwargs):
	return func(*args, **kwargs)

def sysexec(*args):
	import subprocess
	res = subprocess.call(args, shell=False)
	if res != 0: raise ShellError

def sysexecOut(*args):
	from subprocess import Popen, PIPE
	p = Popen(args, shell=False, stdin=PIPE, stdout=PIPE)
	out, _ = p.communicate()
	if p.returncode != 0: raise ShellError
	out = out.decode("utf-8")
	return out

def sysexecRetCode(*args, valid=(0,1)):
	import subprocess
	res = subprocess.call(args, shell=False)
	if valid is not None:
		if res not in valid: raise ShellError
	return res


def git_topLevelDir():
	d = sysexecOut("git", "rev-parse", "--show-toplevel").strip()
	test(os.path.isdir(d))
	test(os.path.isdir(d + "/.git"))
	return d

def git_headCommit():
	return sysexecOut("git", "rev-parse", "--short", "HEAD").strip()

def git_isDirty():
	r = sysexecRetCode("git", "diff", "--no-ext-diff", "--quiet", "--exit-code")
	if r == 0: return False
	if r == 1: return True
	test(False)



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
