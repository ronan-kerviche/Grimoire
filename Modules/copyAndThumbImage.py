import math
from os import path, makedirs
from PIL import Image

def apply(processor, args, string):
	if len(args)<4:
		raise NameError(u'Wrong number of arguments. Arguments should be : originalFilename, width, height, saveFilename, thumbWidth, thumbHeight, thumbSaveFilename')
	# Load the image :
	img = Image.open(args[0], 'r')
	# Try to read the EXIF :
	try:
		exif = img._getexif()
		if exif:
			orientationKey = 274 # cf ExifTags
			if orientationKey in exif:
        			orientation = exif[orientationKey]
        		rotateValues = {3: 180, 6: 270, 8: 90}
        		if orientation in rotateValues:
            			img = img.rotate(rotateValues[orientation])
	except:
		pass
	# Parse the arguments :
	sizeImg = [float(args[1]), float(args[2])]
	if sizeImg[0]<=2.0:
		sizeImg[0] = int(math.floor(sizeImg[0]*img.size[0]))
	else:
		sizeImg[0] = int(math.floor(sizeImg[0]))
	if sizeImg[1]<=2.0:
		sizeImg[1] = int(math.floor(sizeImg[1]*img.size[1]))
	else:
		sizeImg[1] = int(math.floor(sizeImg[1]))
	print u'  Loading %s, resizing to %dX%d and saving to %s ...' % (args[0], sizeImg[0], sizeImg[1], args[3])
	if not path.exists(args[3]) or ('force' in args):
		# Prepare destination :
		directory = path.dirname(args[3])
		if not path.exists(directory):
			makedirs(directory)
		# Resize and save :
		imgW = img.resize(sizeImg, Image.ANTIALIAS)
		imgW.save(args[3], 'JPEG', quality=90)
	else:
		print u'  [Omitted]'
	# If needs to generate a thumbnail :
	if len(args)>=5:
		sizeThumb = (int(args[4]), int(args[5]))	
		print u'  Making thumbnail to %dX%d and saving to %s ...' % (sizeThumb[0], sizeThumb[1], args[6])
		if not path.exists(args[6]) or ('force' in args):
			directory = path.dirname(args[6])
			if not path.exists(directory):
				makedirs(directory)
			img.thumbnail(sizeThumb, Image.ANTIALIAS);
			img.save(args[6], 'JPEG', quality=90)
		else:
			print u'  [Omitted]'
	return ''
