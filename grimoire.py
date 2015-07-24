import sys
import json
from os import path, walk, makedirs
import re
import fnmatch
import codecs
import bisect

# Global tools :
def getStrippedFilename(filename):
	return path.splitext(path.basename(filename))[0]	

def prepareFileWrite(filename):
	directory = path.dirname(filename)
	if not path.exists(directory):
		makedirs(directory)
	return filename

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

def getItemBefore(lst, x):
	o = 1 if x in lst else 0
	i = bisect.bisect_right(lst, x)
	if i-1-o>=0:
        	return lst[i-1-o]
	else:
		return None

def getItemAfter(lst, x):
	o = 0 if x in lst else 1
	i = bisect.bisect_left(lst, x)
	if i+1-o<len(lst):
		return lst[i+1-o]
	else:
		return None
	
def getItemsList(rootDirname, includeFiles, includeDirectories, recursive=False, fileFilter='*', directoryFilter='*'):
	matches = {}
	# Also include the root directory, if needed :
	if includeDirectories:
		for name in fnmatch.filter([rootDirname], directoryFilter):
			name = name.strip('/')
			matches[name] = {}
			matches[name]['firstFilename'] = None
			matches[name]['firstDirname'] = None
			matches[name]['firstName'] = None
			matches[name]['previousFilename'] = None
			matches[name]['previousDirname'] = None
			matches[name]['previousName'] = None
			matches[name]['nextFilename'] = None
			matches[name]['nextDirname'] = None
			matches[name]['nextName'] = None
			matches[name]['lastFilename'] = None
			matches[name]['lastDirname'] = None
			matches[name]['lastName'] = None
			matches[name]['subFilenames'] = []
			matches[name]['subDirnames'] = []
			matches[name]['subNames'] = []
	for root, dirnames, filenames in walk(rootDirname):
		if not recursive:
			# Remove futures from recursion (in-place) :
			del dirnames[:]
		sRoot = root.strip('/')	
		# Filter and sort :
		selectedFiles = []
		selectedDirectories = []
		if includeFiles:
			for filename in fnmatch.filter(filenames, fileFilter):
				selectedFiles.append(path.join(root, filename))
		if includeDirectories:
			for dirname in fnmatch.filter(dirnames, directoryFilter):
				selectedDirectories.append(path.join(root, dirname).strip('/'))
		selected = selectedFiles + selectedDirectories
		selectedFiles.sort()
		selectedDirectories.sort()
		selected.sort()
		# Save results with extra information :
		for name in selected:
			matches[name] = {}
			matches[name]['firstFilename'] = selectedFiles[0] if selectedFiles else None
			matches[name]['firstDirname'] = selectedDirectories[0] if selectedDirectories else None
			matches[name]['firstName'] = selected[0] if selected else None
			matches[name]['previousFilename'] = getItemBefore(selectedFiles, name)
			matches[name]['previousDirname'] = getItemBefore(selectedDirectories, name)
			matches[name]['previousName'] = getItemBefore(selected, name)
			matches[name]['nextFilename'] = getItemAfter(selectedFiles, name)
			matches[name]['nextDirname'] = getItemAfter(selectedDirectories, name)
			matches[name]['nextName'] = getItemAfter(selected, name)
			matches[name]['lastFilename'] = selectedFiles[-1] if selectedFiles else None
			matches[name]['lastDirname'] = selectedDirectories[-1] if selectedDirectories else None
			matches[name]['lastName'] = selected[-1] if selected else None
			matches[name]['subFilenames'] = []
			matches[name]['subDirnames'] = []
			matches[name]['subNames'] = []
		if matches.get(sRoot):
			matches[sRoot]['subFilenames'] = selectedFiles
			matches[sRoot]['subDirnames'] = selectedDirectories
			matches[sRoot]['subNames'] = selected
	return matches

def getVarFromPath(rootVar, pathString, silent=False):
	l = re.findall(ur'(?:(\w+)|"(\w[\w\s\-\.\\/]*)")', pathString)
	l = [item for tmp in l for item in tmp]
	l = filter(None, l)
	currentData = rootVar
	currentName = ''
	try:
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
	except AttributeError:
		print u'Exception caught while capturing variable "%s"' % currentName
		raise 
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
		self.applyFunctions = True
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
		self.extractForeach = re.compile(ur'%s\s*(?:foreach)\s+(\w+)\s+(?:in)\s+(\w+(?:\.\w+)*)\s*%s' % (regSafe(self.functionStart), regSafe(self.argumentSeparator)))
		self.extractFunc = re.compile(ur'%s\s*(?:call)\s+.+\s*(?:%s|%s)'  % (regSafe(self.functionStart), regSafe(self.argumentSeparator), regSafe(self.functionEnd)))		
		#self.extractVar = re.compile(ur'\{\{\s*(\w+\.)*\w+\s*\}\}')	
		#self.extractVar = re.compile(ur'%s\s*(\w+\.)*\w+\s*%s' % (regSafe(self.variableStart), regSafe(self.variableEnd)))	
		self.extractVar = re.compile(ur'%s\s*\w[\w\s\-\."\\/]*\s*%s' % (regSafe(self.variableStart), regSafe(self.variableEnd)))
		self.currentDepth = 0
		self.maxDepth = 16

	# Make an object data available to the augmentation :
	def addObject(self, objModel, name=None):
		if name=='':
			for var in objModel.data:
				self.matchData[var] = objModel[var]
		else:
			if name==None:
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
								middle = end+len(self.argumentSeparator)
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
		#print u'  (Processing test on %s)' % matchObj.group(2)
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
		#print u'  (Processing for loop over %s)' % matchObj.group(2)
		#for var in l:
		for var in sorted(l.keys()):
			self.matchData[varname] = l[var]
			result += self.process(extract)
		self.matchData.pop(varname, None)
		return result + string[(end+2):]

	def processFunc(self, string, start, middle, end, matchObj):
		call = self.process(string[(start+len(self.functionStart)):(middle-len(self.argumentSeparator))]).split()
		if len(call)<=1:
			raise NameError(u'Missing arguments in function call : %s' % string[start:middle])
		if globals().get(call[1])==None:
			raise NameError(u'Unknown function to call : %s' % call[1])
		else:
			# Call the function and process back :
			fun = globals()[call[1]]
			return  string[:start] + self.process(fun(self, call[2:], string[middle:end])) + string[(end+2):]

	def applyFunction(self, string, start, middle, end):
		matchObj = self.extractIf.match(string, start, middle)
		if matchObj!=None:
			return self.processIf(string, start, middle, end, matchObj)
		matchObj = self.extractForeach.search(string, start, middle)
		if matchObj!=None:
			return self.processFor(string, start, middle, end, matchObj)
		matchObj = self.extractFunc.search(string, start, middle)
		if matchObj!=None:
			return self.processFunc(string, start, middle, end, matchObj)
		raise NameError(u'Unknown operation : %s' % string[start:middle])

	# Function parsing the variables request :
	def replaceValueFunction(self, matchobj):
		#print u'  (Processing variable %s)' % matchobj.group(0)
		var = getVarFromPath(self.matchData, matchobj.group(0), not self.forceVariableReplace)
		if var==None:
			return matchobj.group(0)
		else:
			return self.process(unicode(var))

	# Processing string by : 
	#	- calling functions "{% funcion args %% body %}
	#	- replacing variables "{{ topVar.middleVar.bottomVar }}" and applying code.
	def process(self, string):
		if self.currentDepth>self.maxDepth:
			print u'[WARNING] Maximum recursion depth reached while processing string :\n%s...' % string[1:256]
			return string
		else:
			self.currentDepth += 1	
		# Scan :
		if self.applyFunctions:
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
		print u'Processing %s ...' % self['filename']
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
		if self.get('generate')!=None:
			g = self['generate'].split()
			if g==None:
				raise NameError(u'From %s, missing filename to be generated.' % self['filename'])
			for filename in g:
				 self.pages.append( Page('%s/%s' % (site['rootDirectory'], filename), '%s/site/%s' % (site['dirname'], filename), self.generateContent(site)) )

		# Done :
		self.processed = True
		return True

	def generateContent(self, site, content=None, obj={}, name='', applyFunctions=True):
		processor = MiniProcessor();
		processor.applyFunctions = applyFunctions
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
		dataFile = codecs.open(prepareFileWrite(self.outputFilename), 'w', encoding='utf-8')
		dataFile.write(self.content)
		dataFile.close()

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
		layoutFilenames = getItemsList('%s/layouts/' % self['dirname'], True, False, False)
		for filename in layoutFilenames:
			self['layouts'][getStrippedFilename(filename)] = Layout(self, filename)
		# Load all the categories :
		print u'Loading the categories : '
		categories = self['categories']
		self['categories'] = {}
		for category in categories:
			self['categories'][category['category']] = category
		for category in self['categories']:
			print '  %s ...' % category
			self['categories'][category]['data'] = self.listElementsInCategory(self['categories'][category])	
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
		previousFilename = None
		for filename in filenames :
			elements[filename] = {}
			# Just the name :
			elements[filename]['name'] = getStrippedFilename(filename)
			# File test :
			elements[filename]['isFile'] = True if path.isfile(filename) else None
			# Basic filename data :
			elements[filename]['filename'] = filename
			elements[filename]['basename'] = path.basename(filename)
			elements[filename]['dirname'] = path.dirname(filename).strip('/') if elements[filename]['isFile'] else path.dirname(filename + '/').strip('/')
			# Basic local filename data (stripped from the path to the site :
			elements[filename]['localFilename'] = path.relpath(filename, self['dirname'])
			elements[filename]['localDirname'] = path.relpath(elements[filename]['dirname'], self['dirname']).strip('/')
			elements[filename]['directoryName'] = path.basename(elements[filename]['localDirname'])
			# Basic information about the parent :
			elements[filename]['parentDirname'] = path.dirname(elements[filename]['dirname']).strip('/')
			elements[filename]['localParentDirname'] = path.dirname(elements[filename]['localDirname']).strip('/')
			# Output directory :
			elements[filename]['outputDirname'] = ('%s/site/%s' % (self['dirname'], elements[filename]['localDirname'])).strip('/')
			elements[filename]['urlDirname'] = '%s/%s' % (self['rootDirectory'], elements[filename]['localDirname'])
			if path.isfile(filename):
				elements[filename]['outputFilename'] = '%s/%s.html' % (elements[filename]['outputDirname'], elements[filename]['name'])
				elements[filename]['url'] = '%s/%s.html' % (elements[filename]['urlDirname'], elements[filename]['name'])
				(data, content) = reader(filename)
				for var in data:
					elements[filename][var] = data[var]
				elements[filename]['content'] = content
			else:
				elements[filename]['outputFilename'] = '%s/index.html' % (elements[filename]['outputDirname'])
				elements[filename]['url'] = '%s/index.html' % (elements[filename]['urlDirname'])
			# Copy the other data :
			for var in filenames[filename]:
				elements[filename][var] = filenames[filename][var]
		# Make the chains :
		for filename in elements:
			def chain(name, elName):
				elements[filename][elName] = elements[elements[filename][name]] if elements[filename].get(name)!=None and elements.get(elements[filename][name])!=None else None
			chain('firstFilename', 'firstFile')
			chain('firstDirname', 'firstDirectory')
			chain('firstName', 'first')
			chain('previousFilename', 'previousFile')
			chain('previousDirname', 'previousDirectory')
			chain('previousName', 'previous')
			chain('nextFilename', 'nextFile')
			chain('nextDirname', 'nextDirectory')
			chain('nextName', 'next')
			chain('lastFilename', 'lastFile')
			chain('lastDirname', 'lastDirectory')
			chain('lastName', 'last')
			chain('parentDirname', 'parent')
			def chainList(name, elName):
				elements[filename][elName] = {}
				for v in elements[filename][name]:
					elements[filename][elName][v] = elements[v]
			chainList('subFilenames', 'subFiles')
			chainList('subDirnames', 'subDirectories')
			chainList('subNames', 'sub')
		return elements

def importModules(dirname):
	sys.path.insert(0, dirname)
	lst = getItemsList(dirname, True, False, '*.py')
	for filename in lst:	
		moduleName = path.splitext(path.basename(filename))[0]
		if globals().get(moduleName)==None:
			print u'Importing module %s ...' % moduleName
			module = __import__(moduleName)
			if getattr(module, 'apply', None)!=None:
				globals()[moduleName] = getattr(module, 'apply')
			else:
				print u'[WARNING] Module %s does not have a apply function.' % moduleName

# main() :
if __name__ == "__main__":
	importModules('Modules')
	site = Site(sys.argv[1])	
