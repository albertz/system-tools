# -*- coding: utf-8 -*-


import readline
readline.parse_and_bind("tab: complete")
readline.parse_and_bind("set show-all-if-ambiguous on")


class Completer:
	def __init__(self, words):
		self.words = words
		self.prefix = None

	def complete(self, prefix, index):
		if prefix != self.prefix:
			self.matching_words = [w for w in self.words if w.startswith(prefix)]
			self.prefix = prefix
		else:
			pass
		try:
			return self.matching_words[index]
		except IndexError:
			return None


WordsReprMaxLen = 40

def userInputByChoice(words, prompt=""):
	readline.set_completer(Completer(words).complete)
	words_repr = ", ".join(words)
	if len(words_repr) > WordsReprMaxLen:
		words_repr = words_repr[:WordsReprMaxLen] + "..."
	while True:
		s = raw_input(prompt + "Choice of [%s] ? " % words_repr)
		if s in words: return s
		print "Error: '" + s + "' unknown, type again"

def confirm(question):
	while True:
		s = raw_input("%s Press enter to confirm or Ctrl+C otherwise." % question)
		if s == "": return
		print("Error: Don't type anything, just press enter.")

def userInput(prompt, testFunc):
	while True:
		s = raw_input(prompt)
		try:
			assert testFunc(s)
		except Exception as e:
			print("Error: %s" % e)
		else:
			return s

# This is here in `ui` because it returns always some string
# which is only intended for a user and does not mean anything
# otherwise.
def getFuncName(func):
	if hasattr(func, "func_name"):
		return func.func_name
	if hasattr(func, "__name__"):
		return func.__name__
	return str(func)

def userRepr(arg):
	import inspect
	if inspect.isroutine(arg):
		return getFuncName(arg)
	return repr(arg)

class ConfirmByUserDeco(object):
	def __init__(self, func):
		self.func = func
	def __call__(self, *args, **kwargs):
		confirm("%s(%s)?" % (
			getFuncName(self.func),
			", ".join(map(userRepr, args) + ["%s=%r" % item for item in kwargs.items()])
		))
		return self.func(*args, **kwargs)
