from collections import defaultdict
from email.message import EmailMessage
from typing import Annotated
from urllib.parse import quote_plus, parse_qs
import requests
import typer
import re
import urllib3
from bs4 import BeautifulSoup
import os
import pathlib

urllib3.disable_warnings()

app = typer.Typer()
maxPageOffset = 200

FOTO_REGEX = re.compile(r"(subcollection=\d+&amp;mediafile=\d+)")


@app.command()
def fetch(
    tag: str,
    cookie: Annotated[
        str, typer.Option(prompt="What is the value of your Zebraproduction cookie?")
    ],
):
    client = requests.Session()
    client.headers["Cookie"] = f"Zebraproduction={cookie}"
    client.verify = False

    results = defaultdict(list)

    for offset in range(1, maxPageOffset):
        print(f"Checking page {offset}.")
        response = client.get(
            f"https://dev.uscki.nl/?pagina=Media/TagView&tag={quote_plus(tag)}&mode=grid&offset={offset}"
        )

        response.text
        items = FOTO_REGEX.findall(response.text)

        if not items:
            break

        for item in items:
            data = parse_qs(item.replace("&amp;", "&"))
            results[data["subcollection"][0]].append(data["mediafile"][0])

    titles = {}
    for key in results:
        print(f"Fetching collection title for {key}")
        response = client.get(
            f"https://dev.uscki.nl/?pagina=Media/Archive&subcollection={key}"
        )
        soup = BeautifulSoup(response.text, features="html.parser")
        breadcrumbs = soup.find("nav", class_="breadcrumbs")
        assert breadcrumbs

        crumbs = breadcrumbs.text.strip().split("\n>\n")
        titles[key] = "/".join(crumbs[2:]) or key

    cwd = pathlib.Path(os.curdir)

    image_basedir = cwd / "images" / tag
    for key, pictures in results.items():
        print(f"Fetching pictures for {titles[key]}")
        image_dir: pathlib.Path = image_basedir / titles[key]
        image_dir.mkdir(parents=True, exist_ok=True)

        for picture in pictures:
            response = client.get(
                f"https://dev.uscki.nl/?pagina=Media/FileView&id={picture}&size=large"
            )

            # Determine filename
            msg = EmailMessage()
            msg["Content-Disposition"] = response.headers.get("Content-Disposition")
            filename = msg.get_filename()
            assert filename

            with (image_dir / filename).open("wb") as image_file:
                image_file.write(response.content)


if __name__ == "__main__":
    app()
