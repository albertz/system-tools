
from .utils import CachedFunc0Deco

class Config:
	def __init__(self, filename):
		self.filename = filename
		self.data = {}
		self.load()

	def load(self):
		try:
			self.data = eval(open(self.filename).read())
			assert isinstance(self.data, dict)
		except Exception:
			self.data = {}

	def write(self):
		f = open(self.filename, "w")
		f.write("dict([\n")
		f.writelines([repr(l) + ",\n" for l in sorted(self.data.items())])
		f.write("])\n")

	def get(self, attr, testFunc):
		if not attr in self.data: self.load() # try to reload
		if not attr in self.data:
			import ui
			res = ui.userInput("Enter %s: " % attr, testFunc=testFunc)
			self.data[attr] = res
			self.write()
			return res
		res = self.data[attr]
		# TODO: maybe run testFunc on it and if it fails, reask or so
		return res

import os
config = Config(filename=os.path.expanduser("~/.system-tools.config"))

@CachedFunc0Deco
def get_private_server():
	from utils import test_server
	return config.get("private_server", testFunc=test_server)

@CachedFunc0Deco
def get_private_remote_projectdir():
	from utils import test_remotedir
	def test(p): return test_remotedir("ssh://%s/%s" % (get_private_server(), p))
	return config.get("private_remote_projectdir", testFunc=test)



