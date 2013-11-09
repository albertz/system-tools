
import ui

class CachedFunc0Deco(object):
	def __init__(self, func):
		self.func = func
	def __call__(self):
		self.value = self.func()
		self.__call__ = lambda: self.value
		return self.value


class ShellError(Exception): pass

@ui.ConfirmByUserDeco
def shellcmd(cmd):
	import subprocess
	res = subprocess.call(cmd, shell=True)
	if res != 0: raise ShellError

@ui.ConfirmByUserDeco
def pycmd(func, *args, **kwargs):
	return func(*args, **kwargs)
