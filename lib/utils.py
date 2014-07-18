
import os, sys
# http://stackoverflow.com/questions/24826005/how-to-make-from-import-utils-work
#if __package__ is None:
	#__package__ = "%s.%s" % (os.path.basename(os.path.dirname(os.path.abspath(__file__))), os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0])
#	__package__ = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
	#sys.modules[__package__] = __import__(".")
	
from . import ui
#import ui

# It's bad practice to have an import-sideeffect.
# However, these are anyway only small helper tools and this is useful.
import better_exchook
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
