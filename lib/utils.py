
import os, sys
from . import ui

# It's bad practice to have an import-sideeffect.
# However, these are anyway only small helper tools and this is useful.

from . import better_exchook

# Special handling of SIGINT
def myExceptHook(etype, value, tb):
    # For SIGINT: Don't print full info, it's legitimate.
    if etype is KeyboardInterrupt:
        print("\n<KeyboardInterrupt>")
        return
    # Fallback
    better_exchook.better_exchook(etype, value, tb)

sys.excepthook = myExceptHook


IsPython2 = sys.version_info[0] <= 2
IsPython3 = sys.version_info[0] >= 3

if IsPython3:
    unicode = str


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
        super(ShellError, self).__init__("exit code %i" % self.exitCode)


@ui.ConfirmByUserDeco
def shellcmd(cmd):
    use_shell = False
    if type(cmd) is str:
        use_shell = True
    import subprocess
    res = subprocess.call(cmd, shell=use_shell)
    if res != 0:
        raise ShellError(res)


@ui.ConfirmByUserDeco
def pycmd(func, *args, **kwargs):
    return func(*args, **kwargs)


def sysexec(*args, **kwargs):
    import subprocess
    res = subprocess.call(args, shell=False, **kwargs)
    if res != 0:
        raise ShellError(res)


def sysexecVerbose(*args, **kwargs):
    print("sysexec: %s" % (args,))
    return sysexec(*args, **kwargs)


def sysexecOut(*args, **kwargs):
    from subprocess import Popen, PIPE
    kwargs.setdefault("shell", False)
    p = Popen(args, stdin=PIPE, stdout=PIPE, **kwargs)
    out, _ = p.communicate()
    if p.returncode != 0:
        raise ShellError(p.returncode)
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
    if commit is None:
        commit = "HEAD"
    return sysexecOut("git", "rev-parse", "--short", commit, cwd=gitdir).strip()


def git_isDirty(gitdir="."):
    r = sysexecRetCode("git", "diff", "--no-ext-diff", "--quiet", "--exit-code", cwd=gitdir)
    if r == 0:
        return False
    if r == 1:
        return True
    raise Exception("unexpected return code %r" % r)


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
    """Some random string which is usable as (part of) a temporary filename."""
    import uuid
    return str(uuid.uuid4())


def homesDir():
    """Returns the base directory of user home directories."""
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


def shorten_str(s, max_len):
    if len(s) > max_len:
        return s[:max_len-3] + "..."
    else:
        return s


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


def human_size(s, postfix="B", limit=0.9, base=1024, str_format=None):
    p = ["", "K", "M", "G", "T"]
    b = 1
    i = 0
    while i < len(p) - 1 and s * limit > b * base:
        b *= base
        i += 1
    if str_format is None:
        if isinstance(s, float) or i > 0:
            str_format = "%.2f"
        else:
            str_format = "%i"
    return str_format % ((s * 1.0) / b) + " %s%s" % (p[i], postfix)


class ObjAsDict:
    Blacklist = ("__dict__", "__weakref__")

    def __init__(self, obj):
        self.__obj = obj

    def __getitem__(self, item):
        if not isinstance(item, (str, unicode)):
            raise KeyError("%r must be a str" % (item,))
        try:
            return getattr(self.__obj, item)
        except AttributeError as e:
            raise KeyError(e)

    def __setitem__(self, item, value):
        if hasattr(self.__obj, item) and getattr(self.__obj, item) is value:
            return
        setattr(self.__obj, item, value)

    def update(self, other):
        items = other.items() if isinstance(other, dict) else other
        for k, v in items:
            self[k] = v

    def keys(self):
        return [k for k in vars(self.__obj).keys() if k not in self.Blacklist]

    def items(self):
        return [(k, v) for (k, v) in vars(self.__obj).items() if k not in self.Blacklist]

    def __iter__(self):
        return iter(self.keys())

    def __repr__(self):
        return "<ObjAsDict %r -> %r>" % (self.__obj, dict(self.items()))


class classproperty(object):
    """
    https://stackoverflow.com/questions/5189699/how-to-make-a-class-property
    """

    def __init__(self, fget, fset=None):
        if not isinstance(fget, (classmethod, staticmethod)):
            fget = classmethod(fget)
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()


def custom_exec(source, source_filename, user_ns, user_global_ns):
    if not source.endswith("\n"):
        source += "\n"
    co = compile(source, source_filename, "exec")
    user_global_ns["__package__"] = __package__  # important so that imports work when CRNN itself is loaded as a package
    eval(co, user_global_ns, user_ns)


def load_config_py(filename, config_dict=None):
    content = open(filename).read()
    if config_dict is None:
        config_dict = {}
    if isinstance(config_dict, dict):
        user_ns = config_dict
    else:
        user_ns = dict(config_dict)
    # Always overwrite:
    user_ns.update({"config": config_dict, "__file__": filename, "__name__": "__crnn_config__"})
    custom_exec(content, filename, user_ns, user_ns)
    if user_ns is not config_dict:
        config_dict.update(user_ns)
    return config_dict
