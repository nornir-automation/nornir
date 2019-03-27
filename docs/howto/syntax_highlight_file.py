import sys
from typing import Optional, Iterator

from IPython.display import display, Markdown


def get_line_nums(line_nums: str) -> Iterator[int]:
    for line_info in line_nums.split(","):
        if "-" in line_info:
            start_line_str, end_line_str = line_info.split("-")
            start_line, end_line = int(start_line_str), int(end_line_str)
            for line_num in range(start_line, end_line + 1):
                yield line_num
        else:
            yield int(line_info)


def render(path: str, syntax: str = "", lines: Optional[str] = None):
    markdown = ""
    with open(path) as f:
        if lines is None:
            content = f.read()
        else:
            all_lines = f.readlines()
            content = "".join(all_lines[line_num] for line_num in get_line_nums(lines))
        markdown = f"```{syntax}\n{content}\n```"

    return display(Markdown(markdown))


render(*sys.argv[1:])
