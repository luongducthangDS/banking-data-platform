"""Download the PKDD'99 Financial (Berka) dataset into data/raw/."""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/jlacko/berka-dataset/master/"
FILES = ["account", "card", "client", "disp", "district", "loan", "order", "trans"]
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        dest = OUT / f"{f}.asc"
        if not dest.exists():
            urllib.request.urlretrieve(BASE + f"{f}.asc", dest)
        print(f, dest.stat().st_size)
