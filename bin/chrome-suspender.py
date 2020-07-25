#!/usr/bin/env python3

import sys
import os
import subprocess
import psutil
import better_exchook


def main():
  chrome_procs = []
  for proc in psutil.process_iter():
    if not proc.name().startswith("Google Chrome"):
      continue
    if proc.name() == "Google Chrome":
      chrome_procs.insert(0, proc)
    else:
      chrome_procs.append(proc)

  if not chrome_procs:
    print("Chrome not running?")
    sys.exit(1)

  status = chrome_procs[0].status()
  if status == psutil.STATUS_STOPPED:
    for proc in chrome_procs:
      print("Resume pid %i (%s) (%s)" % (proc.pid, proc.name(), proc.status()))
      proc.resume()
  else:
    for proc in chrome_procs:
      print("Suspend pid %i (%s) (%s)" % (proc.pid, proc.name(), proc.status()))
      proc.suspend()


if __name__ == '__main__':
  better_exchook.install()
  main()
