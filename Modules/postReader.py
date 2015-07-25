import codecs
import json
import re

def apply(filename):
	delimiter = u'-----'
	fileData = codecs.open(filename, 'r', encoding='utf-8')
	content = fileData.read()
	fileData.close()
	parts = re.split(ur'%s' % delimiter, content)
	if len(parts)==0:
		return ({}, {})
	elif len(parts)==1:
		return ({}, content)
	else:
		return (json.loads(parts[0]), delimiter.join(parts[1:]))
