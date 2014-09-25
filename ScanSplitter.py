#!/usr/local/bin/python2.7
"""
ScanSplitter.py - A script for splitting pdf-files based on QR-coded separator pages

Usage 1: Split from QR codes
  ScanSplitter [by_separator] <pdf_file>

Usage 2: Split from page numbers
  ScanSplitter by_pageno <pdf_file> <page 1>,<page 2>,...,<page N>

This software requires you to install a lot of helpers:
- GhostView must be installed on path as gs
- zbar library must be installed
- python pillow package must be installed
- python zbar package must be installed 
  See http://stackoverflow.com/questions/21612908/zbar-python-crashes-on-import-osx-10-9-1

janus@insignificancegalore.net, 2014
"""

import zbar
from PIL import Image
import subprocess
import os
import tempfile
import contextlib
import shutil
import itertools
import argparse

@contextlib.contextmanager
def temporary_directory(*args, **kwargs):
    d = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield d
    finally:
        shutil.rmtree(d)

def call_gs(*args):
	allargs = ['gs', '-dNOPAUSE', '-dBATCH', '-dSAFER']+list(args)
	print allargs
	subprocess.call(allargs)

def make_thumbs(file_name, folder):
	call_gs('-sDEVICE=jpeggray', '-r50', '-o'+folder+'/%03d.jpg', file_name)
	return  [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.jpg')]

class QRfilter:
	def __init__(self, match_string = 'halwe.dk'):
		self.scanner = zbar.ImageScanner()
		self.scanner.parse_config('enable')
		self.match_string = match_string

	def scan(self, file_name):
		"""
		If file image has a QR code matching match_string, return corresponding data, otherwise None
		"""
		pil = Image.open(file_name).convert('L')
		width, height = pil.size
		image = zbar.Image(width, height, 'Y800', pil.tobytes())
		self.scanner.scan(image)
		return [symbol.data for symbol in image if symbol.data.endswith(self.match_string)]

	def __call__(self, file_name):
		return self.scan(file_name)

def get_separator_pages(file_name):
	isqr = QRfilter()
	with temporary_directory() as tempfolder:
		thumbs = make_thumbs(file_name, tempfolder)
		separator_pages = [float(os.path.splitext(os.path.basename(f))[0]) for f in thumbs if isqr(f)]
	return separator_pages

def split_pdf(file_name, from_to_pairs, base_name = None):
	if base_name is None:
		base_name = os.path.splitext(file_name)[0]
	for (from_page,to_page) in from_to_pairs:
		out_file_name = '%s_%d.pdf'%(base_name, from_page)
		if to_page is None:
			# write remainder
			call_gs('-sDEVICE=pdfwrite',
				'-dFirstPage=%d'%from_page,
				'-o%s'%out_file_name, file_name)
		else:
			call_gs('-sDEVICE=pdfwrite',
				'-dFirstPage=%d'%from_page,
				'-dLastPage=%d'%to_page,
				'-o%s'%out_file_name, file_name)

def fromto_by_separators(s):
    next_from = 1
    for next_sep in s:
        if next_sep == next_from:
            next_from = next_sep+1
            continue
        yield (next_from, next_sep-1)
        next_from = next_sep+1
    yield (next_from, None)

def main_by_separator(parser, argv):
	parser.add_argument('pdf_file', help = 'PDF file with QR tagged separator pages')
	args = parser.parse_args(argv)

	separator_pages = get_separator_pages(args.pdf_file)
	split_pdf(args.pdf_file, fromto_by_separators(separator_pages))

def main_by_pageno(parser, argv):
	parser.add_argument('pdf_file', help = 'PDF file with QR tagged separator pages')
	parser.add_argument('pages', help = 'Comma-separated list of page numbers to split at')
	args = parser.parse_args(argv)

	pages = [int(s) for s in args.pages.split(',')]
	split_pdf(args.pdf_file, itertools.izip_longest(pages, (s-1 for s in pages[1:])))

def main(argv):
	parser = argparse.ArgumentParser(
		description=__doc__,
		formatter_class=argparse.RawDescriptionHelpFormatter)
	mainmap = {
		'by_separator':  main_by_separator,
		'by_pageno':  main_by_pageno,
		}
	if len(argv)>1 and argv[1] in mainmap:
		mainmap[argv[1]](parser, argv[2:])
	else:
		main_by_separator(parser, argv[1:])

if __name__ == '__main__':
	import sys
	main(sys.argv)
