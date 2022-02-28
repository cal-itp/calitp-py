from calitp.protobuff import get_random_protobuff
import datetime
import sys
import typer

app = typer.Typer()

@app.command()
def random_protobuff(
        glob=typer.Argument(
            "*",
            help="A glob matching itp_id/url_number/string.",
        ),
        bucket=typer.Option(
            "gtfs-data",
            help="GCS bucket to search.",
        ),
        date=typer.Option(
            f"{datetime.date.today()}*",
            help="Date glob.",
        ),
        format=typer.Option(
            "protobuff",
            help="format to output, json or protobuff.",
        ),
):
    blob, data = get_random_protobuff(
        glob,
        bucket=bucket,
        date=date,
        format=format,
    )
    print(f'downloaded {blob}:')
    print(data)


@app.callback()
def callback():
    """
    Pull a random protobuff file from the rt archiver storage.
    without --date defaults to midnignt this morning
    full --date string is like 2022-01-01T10:42:16
    --date must be at least YYYY-MM-DD and will default to zeros after that
    """

app()