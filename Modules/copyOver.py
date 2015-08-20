from os import path, makedirs
from shutil import copyfile

def apply(filename, site):
	if site.get('dirname')==None:
		raise NameError(u'Missing dirname in site object.')
	if site.get('outputDirname')==None:
		raise NameError(u'Missing output dirname in site object.') 
	outputFilename = path.join(site['outputDirname'], path.relpath(filename, site['dirname'])); 
	directory = path.dirname(outputFilename)
	if not path.exists(directory):
		makedirs(directory)
	copyfile(filename, outputFilename)
	return (None, None)
