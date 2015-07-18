import sys
import json
from os import path, walk, makedirs
import re
import fnmatch
import codecs

# Global tools :
def getStrippedFilename(filename):
	return path.splitext(path.basename(filename))[0]	

def parseJSONHeader(string, sourceName):
	parts = re.split(ur'(-){5,}', string)
	if len(parts)==1:
		return ({}, string)
	elif len(parts)==3:
		return (json.loads(parts[0]), parts[2])
	else:
		raise NameError(u'%s is missing the header delimiter.' % sourceName)

def parseJSONFile(filename):
	dataFile = codecs.open(filename, 'r', encoding='utf-8')
	(data, content) = parseJSONHeader(dataFile.read(), filename)
	dataFile.close()
	return (data, content)

def getItemsList(rootDirname, includeFiles, includeDirectories, recursive=False, fileFilter='*', directoryFilter='*'):
	matches = []
	for root, dirnames, filenames in walk(rootDirname):
		if not recursive:
			# Remove futures from recursion (in-place) :
			del dirnames[:]
		if includeFiles:
  			for filename in fnmatch.filter(filenames, fileFilter):
    				matches.append(path.join(root, filename))
		if includeDirectories:
			for dirname in fnmatch.filter(dirnames, directoryFilter):
				matches.append(path.join(root, dirname))
	return matches

def getVarFromPath(rootVar, pathString, silent=False):
	l = re.findall(ur'\w+', pathString)
	currentData = rootVar
	currentName = ''
	for v in l:
		if currentData.get(v)==None:
			if not silent:
				raise NameError('Variable "%s" does not exist in "%s".' % (v, currentName))
			else:
				print u'[WARNING] could not find variable "%s" in "%s".' % (v, currentName)
				return None
		else:
			currentData = currentData[v]
		if not currentName:
			currentName = v
		else:
			currentName = '%s.%s' % (currentName, v)
	return currentData


# Object model :
class ObjectModel(object):
	def __init__(self, name):
		self.name = name
		self.data = {}
	
	def __getitem__(self, member):
		if self.data.get(member)==None:
			raise NameError(u'Object %s does not have a data member named %s.' % (self.name, member))
		else:
			return self.data[member]

	def __setitem__(self, member, value):
		self.data[member] = value

	def get(self, member):
		return self.data.get(member)

	def set(self, member, value):
		self.data.set(member, value)

	def pop(self, member, value):
		self.data.pop(member, value)

	def appendVariables(self, variables):
		for var in variables:
			if self.data.get(var)==None:
				self.data[var] = variables[var]
			else:
				print u'[WARNING] Variable %s dropped in %s' % (var, self.name)

# MiniProcessor : 
class MiniProcessor:
	def __init__(self):
		self.forceVariableReplace = False
		self.matchData = {}
		self.functionStart = '{%'
		self.argumentSeparator = '%%'
		self.functionEnd = '%}'
		self.variableStart = '{{'
		self.variableEnd = '}}'
		def regSafe(s): return s.replace('{', '\{').replace('}', '\}')
		#self.extractIf = re.compile(ur'\{%\s*(if|ifnot)\s+(\w+(?:\.\w+)*)\s*%%')	
		self.extractIf = re.compile(ur'%s\s*(if|ifnot)\s+(\w+(?:\.\w+)*)\s*%s' % (regSafe(self.functionStart), regSafe(self.argumentSeparator)))
		#self.extractFor = re.compile(ur'\{%\s*(?:for)\s+(\w+)\s+(?:in)\s+(\w+(?:\.\w+)*)\s*%%')
		self.extractFor = re.compile(ur'%s\s*(?:for)\s+(\w+)\s+(?:in)\s+(\w+(?:\.\w+)*)\s*%s' % (regSafe(self.functionStart), regSafe(self.argumentSeparator)))
		#self.extractVar = re.compile(ur'\{\{\s*(\w+\.)*\w+\s*\}\}')
		self.extractVar = re.compile(ur'%s\s*(\w+\.)*\w+\s*%s' % (regSafe(self.variableStart), regSafe(self.variableEnd)))
		self.currentDepth = 0
		self.maxDepth = 16

	# Make an object data available to the augmentation :
	def addObject(self, objModel, name=''):
		if not name:
			name = objModel.name
		self.matchData[name] = objModel	

	def findBlock(self,string,start):
		depth = -1
		middle = -1
		blocked = False;
		for start in range(start, len(string), 1):
			if string[start:(start+len(self.functionStart))]==self.functionStart:
				for end in range(start, len(string), 1):
					if blocked:
						blocked = False
						continue
					s = string[end:(end+len(self.functionEnd))]
					if s==self.argumentSeparator and middle<0: # First middle delimiter
						middle = end+len(self.argumentSeparator)
					elif s==self.functionEnd: # Block end
						if depth==0:
							if middle<0:
								middle = end
							return (start, middle, end)
						else:
							depth -= 1
					elif s==self.functionStart: # Block start
						depth += 1
					elif string[end]=='\\':
						blocked = True	
				raise NameError('Missing end delimiter.')
		return (None, None, None)

	def processIf(self, string, start, middle, end, matchObj):
		print u'  (Processing test on %s)' % matchObj.group(2)
		l = getVarFromPath(self.matchData, matchObj.group(2), True)
		if (matchObj.group(1)=='if' and l!=None) or (matchObj.group(1)=='ifnot' and l==None) :	
			return string[:start] + self.process(string[middle:end]) + string[(end+2):]
		else:
			return string[:start] + string[(end+2):]

	def processFor(self, string, start, middle, end, matchObj):
		l = getVarFromPath(self.matchData, matchObj.group(2))
		varname = matchObj.group(1)
		result = string[:start]
		extract = string[middle:end]
		if self.matchData.get(varname)!=None:
			raise NameError(u'A variable with the name "%s" is already in use.' % varname)
		print u'  (Processing for loop over %s)' % matchObj.group(2)
		for var in l:
			self.matchData[varname] = l[var]
			result += self.process(extract)
		self.matchData.pop(varname, None)
		return result + string[(end+2):]
	
	def applyFunction(self, string, start, middle, end):
		matchObj = self.extractIf.match(string, start, middle)
		if matchObj!=None:
			return self.processIf(string, start, middle, end, matchObj)
		matchObj = self.extractFor.search(string, start, middle)
		if matchObj!=None:
			return self.processFor(string, start, middle, end, matchObj)
		raise NameError(u'Unknown function : %s' % string[start:middle])

	# Function parsing the variables request :
	def replaceValueFunction(self, matchobj):
		print u'  (Processing variable %s)' % matchobj.group(0)
		var = getVarFromPath(self.matchData, matchobj.group(0), not self.forceVariableReplace)
		if var==None:
			return matchobj.group(0)
		else:
			return self.process(var)

	# Processing string by : 
	#	- calling functions "{% funcion args %% body %}
	#	- replacing variables "{{ topVar.middleVar.bottomVar }}" and applying code.
	def process(self, string):
		if self.currentDepth>self.maxDepth:
			print u'[WARNING] Maximum recursion depth reached while processing string :\n%s...' % string[1:256]
			return string
		else:
			self.currentDepth += 1
		
		if self.currentDepth==0:
			print string
			print matchData['content']

		# Scan :
		start = 0
		(start, middle, end) = self.findBlock(string, start)
		while start!=None:
			string = self.applyFunction(string, start, middle, end)
			(start, middle, end) = self.findBlock(string, start)

		# Replace remaining variables :
		string = self.extractVar.sub(self.replaceValueFunction, string)
		# Finish :
		self.currentDepth -= 1
		return string

# Layout :
class Layout(ObjectModel):
	def __init__(self, site, filename):
		super(Layout,self).__init__('layout')
		self['filename'] = filename;
		self.processed = False
		self.pages = []
		print u'Loading layout %s ...' % self['filename']
		(data, content) = parseJSONFile(filename)
		self.appendVariables(data)
		self['content'] = content
		
	def process(self, site):
		if self.processed:
			return True
		if self.get('layout')!=None:
			if site['layouts'].get(self['layout'])==None:
				raise NameError(u'From %s, the layout %s was not referenced.' % (self['filename'], self['layout']))
			elif not site['layouts'][self['layout']].processed:
				return False
			# Remove the layout dependency :
			key = self['layout']
			self.pop('layout', None)
			self['content'] = site['layouts'][key].generateContent(site, self['content'])
			# Copy all the variables :
			self.appendVariables(site['layouts'][key].data)
		# Scan, if needed :
		if self.get('foreach')!=None:
			m = re.match(ur'\s*(\w+)\s+in\s+(\w+(?:.\w+)*)', self['foreach'])
			if m==None:
				raise NameError(u'From %s, could not read loop context : %s.' % (self['filename'], self['foreach']))
			varname = m.group(1)
			listname = m.group(2)
			l = getVarFromPath({'site':site, 'layout':self}, listname)
			for var in l:
				self.pages.append( Page(l[var]['url'], l[var]['outputFilename'], self.generateContent(site, None, l[var], varname)) )

		# Done :
		self.processed = True
		return True

	def generateContent(self, site, content=None, obj={}, name=''):
		processor = MiniProcessor();
		processor.addObject(self)
		processor.addObject(site)
		if obj:
			if not name:
				name = obj.name
			processor.addObject(obj, name)
		if content!=None:
			processor.matchData['content'] = content
		return processor.process(self['content'])

# Page :
class Page:
	def __init__(self, url, outputFilename, content):
		self.url = url
		self.outputFilename = outputFilename
		self.content = content

	def write(self):
		print 'Writing to %s ...' % self.outputFilename
		directory = path.dirname(self.outputFilename)
		if not path.exists(directory):
			makedirs(directory)
		dataFile = codecs.open(self.outputFilename, 'w', encoding='utf-8')
		dataFile.write(self.content)
		dataFile.close()

# Post :
def postReader(filename):
	fileData = codecs.open(filename, 'r', encoding='utf-8')
	content = fileData.read()
	fileData.close()
	return parseJSONHeader(content, 'Post %s' % filename)

def imageReader(filename):
	return ({}, filename)

# Site :
class Site(ObjectModel):
	def __init__(self, dirname):
		super(Site,self).__init__('site')
		self['dirname'] = dirname
		self['outputDirname'] = '%s/site' % dirname
		# Start Loading :
		print 'Loading site description from %s ...' % dirname
		dataFile = codecs.open('%s/site.json' % self['dirname'], 'r', encoding='utf-8')
		self.appendVariables(json.load(dataFile))
		dataFile.close()
		# Check mandatory parameters :
		self.checkParameter('site')
		self.checkParameter('rootDirectory')
		self.checkParameter('categories')
		# Load all the layouts :
		print u'Loading the layouts : '
		self['layouts'] = {}
		layoutFilenames = getItemsList('%s/layouts/' % self['dirname'], True, False, False, '*.html')
		for filename in layoutFilenames:
			self['layouts'][getStrippedFilename(filename)] = Layout(self, filename)
		# Load all the categories :
		print u'Loading the categories : '
		self['categoriesList'] = []
		for category in self['categories']:
			self['categoriesList'].append(category['category'])
			self[category['category']] = self.listElementsInCategory(category)
		# Process them :
		layoutsToProcess = self['layouts'].keys()
		while layoutsToProcess:
			oldProcessedCount = len(layoutsToProcess)
			for layout in layoutsToProcess:
				if self['layouts'][layout].process(self):
					layoutsToProcess.remove(layout)
			if oldProcessedCount==len(layoutsToProcess):
				raise NameError("Cannot process any new Layout.")
		# Save the pages :
		for layout in self['layouts']:
			for page in self['layouts'][layout].pages:
				page.write()

	def checkParameter(self, name):
		# Check if a parameter is present :
		if name in self.data:
			return True
		else:
			raise NameError(u'Missing parameter "%s" in %s/site.json.' % (name, self['dirname']))
		
	def listElementsInCategory(self, category):
		if category.get('category')==None:
			raise NameError(u'Missing category name.')
		if category.get('reader')==None:
			raise NameError(u'Reader module name not declared.')
		if globals().get(category['reader'])==None:
			raise NameError(u'Category %s : unknown reader module %s.' % (category['category'], category['reader']))
		else:
			reader = globals()[category['reader']]
		# Settings :
		if category.get('files')!=None:
			files = (category['files'].lower()==str(u'True').lower())
		else:
			files = True
		if category.get('directories')!=None:
			directories = (category['directories']==str(u'True').lower())
		else:
			directories = True
		# Get the items :
		filenames = getItemsList('%s/%s/' % (self['dirname'], category['category']), files, directories, True)
		if not filenames:
			print '[WARNING] Category %s (loading from %s/%s/) appears to be empty.' % (category['category'], self['dirname'], category['category'])
		elements = {}
		previous = None
		for filename in filenames:
			# Set basic element data (previous and next element, directory, patent, etc.)
			elements[filename] = {}
			elements[filename]['filename'] = filename
			elements[filename]['localFilename'] = path.relpath(filename, self['dirname'])
			elements[filename]['dirname'] = path.dirname(filename)
			elements[filename]['next'] = None
			if previous==None:
				elements[filename]['previous'] = None
			elif previous!=None and elements[filename]['dirname']==elements[previous]['dirname']:
				elements[filename]['previous'] = previous
				elements[previous]['next'] = filename
			elements[filename]['outputFilename'] = '%s/site/%s/%s.html' % (self['dirname'], path.dirname(elements[filename]['localFilename']), getStrippedFilename(filename))
			elements[filename]['url'] = '%s/%s/%s.html' % (self['rootDirectory'], path.dirname(elements[filename]['localFilename']), getStrippedFilename(filename))
			# Also copy some information from the category :
			for var in category:
				elements[filename][var] = category[var]
			# Read the data with the requested module :	
			if path.isfile(filename):
				elements[filename]['isfile'] = True;
				(data, content) = reader(filename)
				for var in data:
					elements[filename][var] = data[var]
				elements[filename]['content'] = content
			else:
				elements[filename]['isfile'] = False;
			previous = filename
		return elements

# Main Function :
def main(argv):
	#print "Hello World!"
	#for arg in sys.argv:
	#	print arg
	site = Site("SampleSite")

# Run main() :
if __name__ == "__main__":
	main(sys.argv)
