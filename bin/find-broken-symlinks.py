#!/usr/bin/env python3

import os

for dirname, dirnames, filenames in os.walk('.'):
	
	if '.git' in dirnames:
		dirnames.remove('.git')

	for f in filenames:
		f = dirname + "/" + f
		if os.path.islink(f) and not os.path.exists(f):
			print(f)
			