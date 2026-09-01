"""Download b-roll images via Google Custom Search API.  Run on your PC:

  pip install requests
  python google_download.py --api-key YOUR_KEY --cx YOUR_CX

Free tier: 100 queries/day.  Paid: $5 per 1000 queries (~$0.53 for 105 images).
"""
import argparse, os, requests, time
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

def search_and_download(api_key: str, cx: str, query: str, dest: Path) -> bool:
    r = requests.get("https://www.googleapis.com/customsearch/v1", params={
        "key": api_key, "cx": cx, "q": query,
        "searchType": "image", "imgSize": "xlarge", "num": 5,
    }, timeout=15)
    r.raise_for_status()
    items = r.json().get("items", [])
    for item in items:
        url = item["link"]
        try:
            img = requests.get(url, timeout=15)
            if img.status_code == 200 and len(img.content) > 10_000:
                dest.write_bytes(img.content)
                return True
        except Exception:
            continue
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("GOOGLE_API_KEY"), help="Google API key (or GOOGLE_API_KEY env)")
    ap.add_argument("--cx", default=os.environ.get("GOOGLE_CSE_ID"), help="Custom Search Engine ID (or GOOGLE_CSE_ID env)")
    args = ap.parse_args()
    if not args.api_key or not args.cx:
        raise SystemExit("need --api-key and --cx (or set GOOGLE_API_KEY + GOOGLE_CSE_ID env vars)")

    for idx, query in SHOTS:
        dest = OUT / f"br_{idx:04d}.png"
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"skip br_{idx:04d} (exists)")
            continue
        print(f"br_{idx:04d} -> {query}...", end=" ", flush=True)
        try:
            ok = search_and_download(args.api_key, args.cx, query, dest)
            print("OK" if ok else "FAILED")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)

    done = sum(1 for f in OUT.iterdir() if f.stat().st_size > 10_000)
    print(f"\nDone! {done}/105 images in {OUT}")

if __name__ == "__main__":
    main()
