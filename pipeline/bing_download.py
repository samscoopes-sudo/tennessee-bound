"""Download b-roll images from Bing. Run on your PC:  python bing_download.py"""
import json, os, time, random, re, requests
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUT = Path("broll")
OUT.mkdir(exist_ok=True)

shots = [
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

s = requests.Session()
s.headers["User-Agent"] = UA

for idx, query in shots:
    dest = OUT / f"br_{idx:04d}.png"
    if dest.exists() and dest.stat().st_size > 10000:
        print(f"skip br_{idx:04d} (exists)")
        continue
    print(f"br_{idx:04d} -> {query}...", end=" ", flush=True)
    try:
        r = s.get("https://www.bing.com/images/search",
                  params={"q": query, "form": "HDRSC2", "first": "1", "qft": "+filterui:imagesize-large"},
                  timeout=15)
        urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', r.text)
        if not urls:
            urls = re.findall(r'"murl":"(https?://[^"]+)"', r.text)
        ok = False
        for url in urls[:10]:
            try:
                time.sleep(random.uniform(0.2, 0.5))
                img = s.get(url, timeout=15)
                if img.status_code == 200 and len(img.content) > 10000:
                    dest.write_bytes(img.content)
                    print(f"OK ({len(img.content)//1024}KB)")
                    ok = True
                    break
            except:
                pass
        if not ok:
            print("FAILED")
    except Exception as e:
        print(f"ERROR: {e}")
    time.sleep(random.uniform(0.5, 1.5))

done = sum(1 for f in OUT.iterdir() if f.stat().st_size > 10000)
print(f"\nDone! {done}/105 images in {OUT}")
