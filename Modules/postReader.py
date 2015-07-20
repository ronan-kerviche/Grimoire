import codecs
import json
import re

def apply(filename):
	fileData = codecs.open(filename, 'r', encoding='utf-8')
	content = fileData.read()
	fileData.close()
	parts = re.split(ur'(-){5,}', content)
	if len(parts)==1:
		return ({}, content)
	elif len(parts)==3:
		return (json.loads(parts[0]), parts[2])
	else:
		raise NameError(u'Post %s is missing the header delimiter.' % filename)
