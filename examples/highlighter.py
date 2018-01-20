from __future__ import print_function

from IPython.core.magic import register_line_magic
from IPython.display import HTML

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


HTML_TEMPLATE = """<style>
{}
</style>
{}
"""


@register_line_magic
def highlight_file(filename):
    lexer = get_lexer_by_name("py3")

    linenos = "inline"

    formatter = HtmlFormatter(style='default',
                              cssclass='pygments',
                              linenos=linenos)

    with open(filename) as f:
        code = f.read()

    html_code = highlight(code, lexer, formatter)
    css = formatter.get_style_defs()

    return HTML(HTML_TEMPLATE.format(css, html_code))
