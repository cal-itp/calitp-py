from IPython.core.magic import register_cell_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import Markdown, display
from IPython import get_ipython
from calitp.sql import query_sql


@magic_arguments()
@argument(
    "-m",
    "--markdown",
    action="store_true",
    help="Print the code to markdown, in addition to running",
)
@argument("-o", "--output", type=str, help="A variable name to save the result as")
@argument(
    "-q", "--quiet", action="store_true", help="Whether to hide the result printout"
)
@register_cell_magic
def sql(line, cell):
    # %%sql -m
    # %%sql -o tbl_result
    args = parse_argstring(sql, line)

    if args.markdown:
        # print out a markdown object
        display(Markdown(f"""```SQL\n{cell}\n```"""))

    res = query_sql(cell)

    if args.output:
        # if output variable specified, set it as the result in IPython
        shell = get_ipython()
        shell.user_ns[args.output] = res

    if not args.quiet:
        return res
