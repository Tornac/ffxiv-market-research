import json
import pathlib
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import List

import pandas as pandas
import requests


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
    return td.total_seconds() < one_day


def get_unit_price(name: str) -> Item:
    item_id = get_id_by_name(name)
    url = f"https://xivapi.com/market/Lich/item/{item_id}"
    res = requests.get(url)
    res.raise_for_status()
    prices = json.loads(res.text)["History"]
    nqs = sorted(
        price["PricePerUnit"] for price in prices if not price["IsHQ"] and listing_is_recent(price))
    hqs = sorted(
        price["PricePerUnit"] for price in prices if price["IsHQ"] and listing_is_recent(price))
    return Item(
        id=item_id,
        name=name,
        nq=avg(nqs[:10]),
        hq=avg(hqs[:10])
    )


def avg(xs: list):
    if not xs:
        return -1
    return round(sum(xs) / len(xs))


@lru_cache(maxsize=None)
def get_id_by_name(name: str):
    url = "https://xivapi.com/search"
    res = requests.get(url, {
        "string": name,
        "string_algo": "match"
    })
    res.raise_for_status()
    data = json.loads(res.text)["Results"][0]
    assert name == data["Name"]
    return data["ID"]


def check_category(category: Category):
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
            item = get_unit_price(name)
            items.append(item)
        except:
            errors.append(name)
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


def main():
    categories = [Category(f) for f in (pathlib.Path(__file__).parent / "categories").iterdir()]
    for i, c in enumerate(categories):
        print(f"[ {str(i).rjust(3, ' ')} ] - {c.name}")
    print("[ all ] - will go through every category")
    choice = -1
    while choice < 0 or choice >= len(categories):
        choice = input("choose a list to check: ")
        try:
            categories = categories[int(choice)]
        except ValueError:
            if choice == "all":
                break
    for c in categories:
        check_category(c)


if __name__ == '__main__':
    main()
