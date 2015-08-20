import exifread

def apply(filename, site):
	apply.printExif += 1
	if apply.printExif==1:
		print '    EXIF for %s :' % filename
	# Read the EXIF data :
	f = open(filename, 'rb')
	tags = exifread.process_file(f)
	data = {}
	for tag in tags.keys():
		if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename'):
			if (tags[tag].field_type!=7 or not all(v==0 for v in tags[tag].values)):
				c = tag.split()
				current = data
				for k in range(0, len(c)-1):
					if current.get(c[k])==None:
						current[c[k]] = {}
					current = current[c[k]]
				current[c[-1]] = str(tags[tag])
				if apply.printExif==1:
					print u'      TAG <%s> VALUE <%s>' % (tag, tags[tag])
			else:
				if apply.printExif==1:
					print u'      OMITTED TAG <%s> VALUE <%s>' % (tag, tags[tag])
	f.close()
	return (data, '')

apply.printExif = 0
