#!/usr/bin/env python3

# Multithreaded cat.
# http://unix.stackexchange.com/questions/279989/non-blocking-multi-threaded-cat

import os
import sys
from threading import Thread, Condition
from argparse import ArgumentParser


class Pipe:
	def __init__(self):
		self.buffer = []
		self.cond = Condition()
		self.finish = False

	def read(self):
		raise NotImplementedError

	def write(self, v):
		raise NotImplementedError

	def reader_loop(self):
		while True:
			v = self.read()
			with self.cond:
				if v is None:
					self.finish = True
					self.cond.notifyAll()
					return
				self.buffer.append(v)
				self.cond.notifyAll()

	def writer_loop(self):
		while True:
			with self.cond:
				while True:
					if self.buffer:
						break
					if self.finish:
						return
					self.cond.wait(timeout=1)
				v = self.buffer.pop(0)
			self.write(v)


def main():
	parser = ArgumentParser(description='Multithreaded cat. Reads stdin and writes to stdout in parallel.')
	args = parser.parse_args()  # ignored at the moment.

	sin_fd = sys.stdin.fileno()
	sout = open(sys.stdout.fileno(), "wb", buffering=0, closefd=False)
	read_max_size = 1000000

	def read():
		# This has the behavior which we actually want:
		#  - If there are <= read_max_size bytes available, it will return those immediately,
		#    i.e. it will not block to wait until read_max_size bytes are available.
		#  - If there are 0 bytes available, it will block and wait until some bytes are available.
		v = os.read(sin_fd, read_max_size)
		return v or None
	def write(v):
		sout.write(v)
		sout.flush()

	pipe = Pipe()
	pipe.read = read
	pipe.write = write
	reader = Thread(name="reader", daemon=True, target=pipe.reader_loop)
	writer = Thread(name="writer", daemon=True, target=pipe.writer_loop)
	reader.start()
	writer.start()
	try:
		reader.join()
		writer.join()
	except KeyboardInterrupt:
		pass


if __name__ == "__main__":
	main()

