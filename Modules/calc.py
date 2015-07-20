from __future__ import division

def apply(processor, args, string):
	return str(eval(processor.process(string)))
