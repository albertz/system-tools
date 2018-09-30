#!/usr/bin/env python3

import unicodedata

def rmdiacritics(char):
    '''
    Return the base character of char, by "removing" any
    diacritics like accents or curls and strokes and the like.
    http://stackoverflow.com/a/15547803/133374
    '''
    desc = unicodedata.name(char)
    cutoff = desc.find(' WITH ')
    if cutoff != -1:
        desc = desc[:cutoff]
    return unicodedata.lookup(desc)

def unicode_norm(s):
	" Łukasz -> Lukasz "
	return "".join(map(rmdiacritics, s))

import sys

if __name__ == "__main__":
	lines = sys.stdin.read().splitlines()
	lines.sort(key=unicode_norm)

	for l in lines:
		print(l)
