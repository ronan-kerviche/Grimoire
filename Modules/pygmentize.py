from pygments import highlight
from pygments.lexers import guess_lexer, get_lexer_by_name
from pygments.formatters import HtmlFormatter

def apply(processor, args, string):
	if len(args)<1:
		lexer = guess_lexer(string)
	else:
		lexer = get_lexer_by_name(args[0])
	return highlight(string, lexer, HtmlFormatter(linenos=('linenos' in args)))
