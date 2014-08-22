#!/usr/local/bin/python2.7
"""
splitByQR.py - A script for splitting pdf-files based on QR-coded separator pages

Has a bunch of anoying prerequisites:
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

def split_pdf_byseparators(file_name, separator_pages, base_name = None):
	if base_name is None:
		base_name = os.path.splitext(file_name)[0]
	first_page = 1
	for sp in separator_pages:
		if sp == first_page:
			first_page = sp+1
			continue
		out_file_name = '%s_%d.pdf'%(base_name, first_page)
		call_gs('-sDEVICE=pdfwrite',
			'-dFirstPage=%d'%first_page,
			'-dLastPage=%d'%(sp-1),
			'-o%s'%out_file_name, file_name)
		first_page = sp+1
	# write remainder
	call_gs('-sDEVICE=pdfwrite',
		'-dFirstPage=%d'%first_page,
		'-o%s'%out_file_name, file_name)

def main(pdfname):
	separator_pages = get_separator_pages(pdfname)
	split_pdf_byseparators(pdfname, separator_pages)


if __name__ == '__main__':
	import sys
	main(*sys.argv[1:])