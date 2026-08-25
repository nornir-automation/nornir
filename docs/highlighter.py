import pathlib

from IPython.core.display import HTML
from IPython.core.magic import register_line_magic
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename

HTML_TEMPLATE = """<style>
{}
</style>
{}
"""

EXTRA_CSS = """span.lineno {
    color: lightgray;
}
"""


@register_line_magic
def highlight_file(filename: str) -> HTML:
    """Render a file as syntax highlighted HTML.

    Registered as the ``%highlight_file`` line magic so the documentation notebooks can
    show inventory and configuration files with line numbers. The lexer is picked from
    the extension of the file.

    Arguments:
        filename: Path of the file to render

    Returns:
        The highlighted file, ready for IPython to display.

    """
    lexer = get_lexer_for_filename(filename)

    linenos = "inline"

    formatter = HtmlFormatter(style="default", cssclass="pygments", linenos=linenos)

    with pathlib.Path(filename).open() as f:
        code = f.read()

    html_code = highlight(code, lexer, formatter)
    css = formatter.get_style_defs()
    css += EXTRA_CSS

    return HTML(HTML_TEMPLATE.format(css, html_code))
