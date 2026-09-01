"""Download b-roll images from Unsplash + Wikimedia Commons.
Run on your PC:

  pip install requests
  python unsplash_download.py --key YOUR_UNSPLASH_ACCESS_KEY

Unsplash: free, 50 req/hr on demo apps. Sign up at https://unsplash.com/developers
Wikimedia: free, no key needed.
"""
import argparse, os, requests, time, re
from pathlib import Path

OUT = Path("broll")
OUT.mkdir(exist_ok=True)

SHOTS = [
    (0,"green lawn"),(1,"calendar september"),(2,"dry brown grass"),(3,"thick green lawn"),
    (4,"neighbor fence yard"),(5,"bare dirt patch"),(6,"weed growing lawn"),(8,"grass seed bag"),
    (9,"fertilizer spreader"),(10,"patchy lawn spring"),(11,"lawn tools shed"),(12,"weekend morning yard"),
    (13,"healthy lawn closeup"),(15,"warm soil ground"),(16,"sunset autumn sky"),(17,"grass roots soil"),
    (18,"lawn growing fast"),(19,"spring lawn cold"),(20,"weeds sprouting ground"),(22,"lawn care professional"),
    (23,"sprinkler lawn water"),(24,"overseeding lawn"),(25,"lawn heat damage"),(26,"foot traffic lawn"),
    (27,"bare lawn spots"),(29,"grass seed closeup"),(30,"august garden calendar"),(31,"seed germination soil"),
    (32,"cool evening lawn"),(33,"young grass growing"),(34,"weed free lawn"),(36,"frost on grass"),
    (37,"clock deadline"),(38,"dead grass winter"),(39,"spring bare patches"),(40,"lawn mower cutting"),
    (41,"grass clippings bag"),(43,"garden rake soil"),(44,"bare dirt raking"),(45,"seed spreader lawn"),
    (46,"grass seed label"),(47,"seedlings crowded"),(48,"watering lawn hose"),(50,"moist soil closeup"),
    (51,"new grass sprouting"),(52,"thick grass result"),(53,"lawn aerator machine"),(54,"compacted dry soil"),
    (55,"lawn mower tracks"),(57,"sun baked yard"),(58,"soil plugs lawn"),(59,"aeration holes grass"),
    (60,"water soaking soil"),(61,"grass roots deep"),(62,"fall leaves lawn"),(64,"lawn recovery green"),
    (65,"aerator running lawn"),(66,"seed in holes"),(67,"aerate overseed lawn"),(68,"screwdriver soil test"),
    (69,"hard packed soil"),(71,"water pooling grass"),(72,"water runoff lawn"),(73,"thin lawn feeding"),
    (74,"core aerator rental"),(75,"lawn fall growth"),(76,"aeration before after"),(78,"fertilizer granules"),
    (79,"lawn fertilizer bag"),(80,"spreader fertilizing lawn"),(81,"lawn feeding results"),(82,"fall lawn care"),
    (83,"grass growing thick"),(85,"spring lawn mistake"),(86,"fertilizer numbers"),(87,"root growth underground"),
    (88,"lawn winter prep"),(89,"granules on grass"),(90,"watering after fertilize"),(92,"weed killer spray"),
    (93,"dandelion lawn weed"),(94,"broadleaf weed lawn"),(95,"spot spray weeds"),(96,"weed dying lawn"),
    (97,"new grass seedlings"),(99,"herbicide bottle"),(100,"calendar timing plan"),(101,"mature grass lawn"),
    (102,"leaf raking lawn"),(103,"mower height adjust"),(104,"tall grass mowing"),(106,"leaves smothering grass"),
    (107,"mulching mower leaves"),(108,"lawn stripe pattern"),(109,"grass blade height"),(110,"snow covered lawn"),
    (111,"spring green lawn"),(113,"checklist notepad"),(114,"lawn tools lineup"),(115,"weekend yard work"),
    (116,"beautiful lawn house"),(117,"neighbor lawn envy"),(118,"lawn care success"),(120,"sunset lawn view"),
    (121,"lawn care tools"),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def try_unsplash(query, dest, api_key):
    r = requests.get("https://api.unsplash.com/search/photos", params={
        "query": query, "per_page": 5, "orientation": "landscape",
    }, headers={"Authorization": f"Client-ID {api_key}"}, timeout=15)
    if r.status_code == 403:
        print("[rate limited]", end=" ")
        return False
    r.raise_for_status()
    results = r.json().get("results", [])
    for photo in results:
        url = photo["urls"]["regular"]  # 1080px wide
        try:
            img = requests.get(url, timeout=15)
            if img.status_code == 200 and len(img.content) > 10_000:
                dest.write_bytes(img.content)
                return True
        except Exception:
            continue
    return False


def try_wikimedia(query, dest):
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "list": "search", "srsearch": f"{query} filetype:bitmap",
        "srnamespace": "6", "srlimit": "10", "format": "json",
    }, headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    results = r.json().get("query", {}).get("search", [])
    for item in results:
        title = item["title"]
        # get the actual file URL
        r2 = requests.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "titles": title, "prop": "imageinfo",
            "iiprop": "url|size", "iiurlwidth": "1920", "format": "json",
        }, headers={"User-Agent": UA}, timeout=15)
        r2.raise_for_status()
        pages = r2.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue
            try:
                img = requests.get(url, timeout=15, headers={"User-Agent": UA})
                if img.status_code == 200 and len(img.content) > 10_000:
                    dest.write_bytes(img.content)
                    return True
            except Exception:
                continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("UNSPLASH_ACCESS_KEY"),
                    help="Unsplash Access Key (or UNSPLASH_ACCESS_KEY env)")
    args = ap.parse_args()

    if not args.key:
        print("No Unsplash key — will use Wikimedia Commons only.")
        print("For better results: sign up at https://unsplash.com/developers")

    for idx, query in SHOTS:
        dest = OUT / f"br_{idx:04d}.png"
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"skip br_{idx:04d} (exists)")
            continue
        print(f"br_{idx:04d} -> {query}...", end=" ", flush=True)

        ok = False
        # Try Unsplash first
        if args.key:
            try:
                ok = try_unsplash(query, dest, args.key)
                if ok:
                    print(f"OK unsplash ({dest.stat().st_size // 1024}KB)")
            except Exception as e:
                print(f"[unsplash error: {e}]", end=" ")

        # Fall back to Wikimedia
        if not ok:
            try:
                ok = try_wikimedia(query, dest)
                if ok:
                    print(f"OK wikimedia ({dest.stat().st_size // 1024}KB)")
            except Exception as e:
                print(f"[wikimedia error: {e}]", end=" ")

        if not ok:
            print("FAILED")

        time.sleep(0.5)

    done = sum(1 for f in OUT.iterdir() if f.stat().st_size > 10_000)
    print(f"\nDone! {done}/105 images in {OUT}")


if __name__ == "__main__":
    main()
