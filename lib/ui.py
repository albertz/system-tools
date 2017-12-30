# -*- coding: utf-8 -*-

from __future__ import print_function
import sys

try:
    import readline
except ImportError:
    # noinspection SpellCheckingInspection
    readline = None
if readline:
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set show-all-if-ambiguous on")


# Python 3 workaround
try:
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    raw_input
except NameError:
    raw_input = input


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
    if readline:
        readline.set_completer(Completer(words).complete)
    words_repr = ", ".join(words)
    if len(words_repr) > WordsReprMaxLen:
        words_repr = words_repr[:WordsReprMaxLen] + "..."
    while True:
        s = raw_input(prompt + "Choice of [%s] ? " % words_repr)
        if s in words:
            return s
        print("Error: %r unknown, type again" % s)


def confirm(question):
    while True:
        s = raw_input("%s Press enter to confirm or Ctrl+C otherwise." % question)
        if s == "":
            return
        print("Error: Don't type anything, just press enter.")


def seriousConfirm(question):
    while True:
        s = raw_input("%s Type 'yes' to confirm." % question)
        if s == "yes":
            return
        if not s:
            continue
        print("Invalid answer %r. Aborting." % s)
        sys.exit(1)


def userInput(prompt, testFunc):
    while True:
        s = raw_input(prompt)
        try:
            assert testFunc(s)
        except Exception as e:
            print("Error: %s" % e)
        else:
            return s


def userRepr(arg):
    import inspect
    from .utils import get_func_name
    if inspect.isroutine(arg):
        return get_func_name(arg)
    return repr(arg)


class ConfirmByUserDeco(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        from .utils import get_func_name
        confirm("%s(%s)?" % (
            get_func_name(self.func),
            ", ".join(list(map(userRepr, args)) + ["%s=%r" % item for item in kwargs.items()])
        ))
        return self.func(*args, **kwargs)


class ConfirmByUserOptOnce:
    def __init__(self, func=None, prompt=None, dry_run=False, verbose=False, confirmed=False):
        self.func = func
        self.confirmed_always = confirmed
        self.prompt = prompt
        self.dry_run = dry_run
        self.verbose = verbose

    def confirm(self, prompt=None):
        """
        :param str prompt:
        """
        if prompt is None:
            prompt = self.prompt or "Confirm?"
        if prompt and not prompt.endswith(" "):
            prompt += " "
        if self.confirmed_always:
            return
        res = userInputByChoice(words=["", "yes", "always", "no"], prompt=prompt)
        if res == "no":
            raise KeyboardInterrupt
        elif res == "always":
            self.confirmed_always = True
        else:
            assert res in ["", "yes"]

    def __call__(self, *args, **kwargs):
        from .utils import format_func_call
        if self.dry_run:
            if self.prompt:
                print(self.prompt, end=" ")
            print("Dry-run, not executing %s." % format_func_call(self.func, args, kwargs))
            return
        self.confirm()
        if self.verbose:
            print("Call %s." % format_func_call(self.func, args, kwargs))
        return self.func(*args, **kwargs)

    def call_custom(self, func, args=(), kwargs=None, prompt=None):
        from .utils import format_func_call
        if self.dry_run:
            if prompt or self.prompt:
                print(prompt or self.prompt, end=" ")
            print("Dry-run, not executing %s." % format_func_call(func, args, kwargs))
            return
        if not prompt:
            if self.prompt:
                prompt = self.prompt
            else:
                prompt = "Confirm call %s?" % format_func_call(func, args, kwargs)
        self.confirm(prompt=prompt)
        if kwargs is None:
            kwargs = {}
        if self.verbose:
            print("Call %s." % format_func_call(func, args, kwargs))
        return func(*args, **kwargs)
