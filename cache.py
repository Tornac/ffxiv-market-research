import json
from pathlib import Path

import requests

cache_dir: Path = Path(__file__).parent / ".cache"
if not cache_dir.is_dir():
    cache_dir.mkdir()


class IdCache:
    def __init__(self):
        self.file: Path = cache_dir / "id.json"
        if self.file.is_file():
            with self.file.open() as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def _request_id(self, item_name: str) -> int:
        url = "https://xivapi.com/search"
        res = requests.get(url, {
            "string": item_name,
            "string_algo": "match"
        })
        res.raise_for_status()
        data = json.loads(res.text)["Results"][0]
        assert item_name == data["Name"]
        return int(data["ID"])

    def get(self, item_name) -> int:
        try:
            return self.data[item_name]
        except KeyError:
            val = self._request_id(item_name)
            assert val > 0
            self.data[item_name] = val
            return val

    def __enter__(self) -> "IdCache":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.file.open("w") as f:
            json.dump(self.data, f)
