import json
import pathlib
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pandas
import requests

from cache import IdCache


@dataclass
class Item:
    id: int
    name: str
    nq: int
    hq: int


@dataclass
class Category:
    path: pathlib.Path

    @property
    def name(self):
        return self.path.stem


def listing_is_recent(listing: dict):
    td = datetime.now() - datetime.fromtimestamp(listing["PurchaseDate"])
    one_day = 60 * 60 * 24
    return td.total_seconds() < one_day * 1.33


def get_unit_price(name: str, id_cache: IdCache) -> Item:
    item_id = id_cache.get(name)
    url = f"https://xivapi.com/market/Lich/item/{item_id}"
    res = requests.get(url)
    res.raise_for_status()
    history = [entry for entry in json.loads(res.text)["History"] if listing_is_recent(entry)]
    nq_history = sorted(entry["PricePerUnit"] for entry in history if not entry["IsHQ"])
    hq_history = sorted(entry["PricePerUnit"] for entry in history if entry["IsHQ"])
    return Item(
        id=item_id,
        name=name,
        nq=avg(nq_history[:10]),
        hq=avg(hq_history[:10])
    )


def avg(xs: list):
    if not xs:
        return -1
    return round(sum(xs) / len(xs))


def check_category(category: Category, id_cache: IdCache):
    items: List[Item] = []
    names = []
    with category.path.open() as file:
        for name in file.readlines():
            name = name.strip()
            if name:
                names.append(name)

    errors = []
    for i, name in enumerate(names):
        try:
            time.sleep(0.1)
            item = get_unit_price(name, id_cache)
            items.append(item)
        except:
            errors.append(name)
            report_error(name)
        finally:
            print(f"progress: {i + 1} / {len(names)}")
    df = pandas.DataFrame(columns=["Name", "NQ Price", "HQ Price"])
    for item in sorted(items, key=lambda i: i.nq, reverse=True):
        df = df.append({"Name": item.name, "NQ Price": item.nq, "HQ Price": item.hq},
                       ignore_index=True)

    output = f"category: {category.name}\n"
    output += f"last update: {datetime.now()}\n"
    output += "\n" + str(df) + "\n"
    if errors:
        output += "\nerrors for item names:\n"
        for error in errors:
            output += "    " + error + "\n"
    print(output)
    outdir: pathlib.Path = pathlib.Path(__file__).parent / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / category.name).open("w") as f:
        f.write(output)


def report_error(item_name: str, timestamp=str(round(time.time()))):
    directory: pathlib.Path = pathlib.Path(__file__).parent / "errors"
    directory.mkdir(exist_ok=True)
    with (directory / timestamp).open("a") as f:
        f.write(f"item: {item_name}\n\n")
        f.write(traceback.format_exc())
        f.write("\n-----------------\n\n")


def main(id_cache: IdCache):
    categories = [Category(f) for f in (pathlib.Path(__file__).parent / "categories").iterdir()]
    for i, c in enumerate(categories):
        print(f"[ {str(i).rjust(3, ' ')} ] - {c.name}")
    print("[ all ] - will go through every category")
    while True:
        choice = input("choose a list to check: ")
        try:
            categories = [categories[int(choice)]]
            break
        except ValueError:
            if choice == "all":
                break
    for c in categories:
        check_category(c, id_cache)


if __name__ == '__main__':
    with IdCache() as cache:
        main(cache)
