
import ui

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
		return "{\n" + "".join(map(lambda (k,v): betterRepr(k) + ": " + betterRepr(v) + ",\n", sorted(o.iteritems()))) + "}"
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
	assert o.path[0] == "/"
	path = o.path[1:]
	args += ["stat", path]
	args += [">/dev/null"]

	import subprocess
	res = subprocess.call(" ".join(args), shell=True)
	assert res == 0
	return True
