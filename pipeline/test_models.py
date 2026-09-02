#!/usr/bin/env python3
"""Side-by-side quality + speed test for image and video models on ComfyUI.

Tests:
  IMAGE:  FLUX.1-dev+Boreal  vs  SD3.5 Large
  VIDEO:  Wan 2.1 14B  vs  CogVideoX-5B

Each model renders the SAME 5 prompts (including text-heavy ones).
Output: test_output/ folder with all results + a timing summary.

Usage:
  python3 test_models.py --comfy http://127.0.0.1:8188
"""
import argparse, json, time, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.comfy import Comfy

OUT = Path("test_output")
OUT.mkdir(exist_ok=True)

# --- Test prompts: mix of normal scenes + text-heavy (the pain point) ---
IMAGE_PROMPTS = [
    ("lawn_green", "photo of a lush green lawn in morning sunlight, suburban backyard, photorealistic"),
    ("text_sign", "photo of a wooden garden sign that reads KEEP OFF THE GRASS, close up, sharp text, photorealistic"),
    ("text_bag", "photo of a bag of Scott's grass seed with product label visible, store shelf, photorealistic"),
    ("detail_roots", "photo of grass roots in cross-section of soil, detailed macro shot, photorealistic"),
    ("person_mowing", "photo of a man mowing a lawn with a push mower, wide shot, suburban neighborhood, photorealistic"),
]

VIDEO_PROMPTS = [
    ("sprinkler", "water sprinkler spinning on green lawn, water droplets catching sunlight"),
    ("leaves_fall", "autumn leaves gently falling onto grass, slow calm movement"),
    ("mower_push", "push lawn mower moving forward cutting grass, steady smooth motion"),
]


def test_flux(comfy, prompts):
    """Test FLUX.1-dev + Boreal (fp8 checkpoint, no GGUF needed)."""
    print("\n=== FLUX.1-dev + Boreal (fp8) ===")
    wf_path = Path(__file__).resolve().parent / "workflows" / "flux_still_fp8.json"
    if not wf_path.exists():
        print("  ERROR: flux_still_fp8.json workflow not found — skip")
        return []
    template = json.loads(wf_path.read_text())
    times = []
    for name, prompt in prompts:
        dest = OUT / f"flux_{name}.png"
        print(f"  {name}...", end=" ", flush=True)
        wf = json.loads(json.dumps(template))
        for nid, node in wf.items():
            if node.get("_meta", {}).get("title") == "Positive":
                node["inputs"]["text"] = prompt
        t0 = time.time()
        try:
            pid = comfy.queue(wf)
            hist = comfy.wait(pid)
            outs = comfy.outputs(hist)
            if outs:
                comfy.download(outs[-1], dest)
                dt = time.time() - t0
                times.append(dt)
                print(f"OK {dt:.1f}s ({dest.stat().st_size // 1024}KB)")
            else:
                print("FAILED: no output")
        except Exception as e:
            print(f"FAILED: {e}")
    return times


def test_sd35(comfy, prompts):
    """Test SD3.5 Large."""
    print("\n=== SD3.5 Large ===")
    wf_path = Path(__file__).resolve().parent / "workflows" / "sd35_test.json"
    if not wf_path.exists():
        print("  ERROR: sd35_test.json workflow not found — skip")
        return []
    template = json.loads(wf_path.read_text())
    times = []
    for name, prompt in prompts:
        dest = OUT / f"sd35_{name}.png"
        print(f"  {name}...", end=" ", flush=True)
        wf = json.loads(json.dumps(template))
        # Set prompt in the positive CLIP node
        for nid, node in wf.items():
            if node.get("_meta", {}).get("title") == "Positive":
                node["inputs"]["text"] = prompt
        t0 = time.time()
        try:
            pid = comfy.queue(wf)
            hist = comfy.wait(pid)
            outs = comfy.outputs(hist)
            if outs:
                comfy.download(outs[-1], dest)
                dt = time.time() - t0
                times.append(dt)
                print(f"OK {dt:.1f}s ({dest.stat().st_size // 1024}KB)")
            else:
                print("FAILED: no output")
        except Exception as e:
            print(f"FAILED: {e}")
    return times


def test_wan(comfy, image_path, prompts):
    """Test Wan 2.1 14B (current video model)."""
    print("\n=== Wan 2.1 14B (video) ===")
    times = []
    for name, prompt in prompts:
        dest = OUT / f"wan_{name}.mp4"
        print(f"  {name}...", end=" ", flush=True)
        t0 = time.time()
        try:
            # Use a test still as input
            still = OUT / f"flux_{IMAGE_PROMPTS[0][0]}.png"
            if not still.exists():
                still = image_path
            comfy.wan_i2v(still, prompt, 49, 832, 480, dest)  # 49 frames ~3s
            dt = time.time() - t0
            times.append(dt)
            print(f"OK {dt:.1f}s")
        except Exception as e:
            print(f"FAILED: {e}")
    return times


def test_cogvideo(comfy, prompts):
    """Test CogVideoX-5B."""
    print("\n=== CogVideoX-5B (video) ===")
    wf_path = Path(__file__).resolve().parent / "workflows" / "cogvideo_test.json"
    if not wf_path.exists():
        print("  ERROR: cogvideo_test.json workflow not found — skip")
        return []
    template = json.loads(wf_path.read_text())
    times = []
    for name, prompt in prompts:
        dest = OUT / f"cogvideo_{name}.mp4"
        print(f"  {name}...", end=" ", flush=True)
        wf = json.loads(json.dumps(template))
        for nid, node in wf.items():
            if node.get("_meta", {}).get("title") == "Positive":
                node["inputs"]["text"] = prompt
        t0 = time.time()
        try:
            pid = comfy.queue(wf)
            hist = comfy.wait(pid)
            outs = comfy.outputs(hist)
            if outs:
                comfy.download(outs[-1], dest)
                dt = time.time() - t0
                times.append(dt)
                print(f"OK {dt:.1f}s")
            else:
                print("FAILED: no output")
        except Exception as e:
            print(f"FAILED: {e}")
    return times


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy", required=True, help="ComfyUI URL")
    ap.add_argument("--skip-video", action="store_true", help="Only test image models")
    ap.add_argument("--skip-image", action="store_true", help="Only test video models")
    args = ap.parse_args()

    comfy = Comfy(args.comfy)
    results = {}

    if not args.skip_image:
        results["flux"] = test_flux(comfy, IMAGE_PROMPTS)
        results["sd35"] = test_sd35(comfy, IMAGE_PROMPTS)

    if not args.skip_video:
        # Need a source still for Wan i2v
        still = OUT / f"flux_{IMAGE_PROMPTS[0][0]}.png"
        if not still.exists():
            print("\nGenerating a source still for video tests...")
            comfy.flux_still(IMAGE_PROMPTS[0][1], 1280, 720, still, seed=42)
        results["wan"] = test_wan(comfy, still, VIDEO_PROMPTS)
        results["cogvideo"] = test_cogvideo(comfy, VIDEO_PROMPTS)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for model, times in results.items():
        if times:
            avg = sum(times) / len(times)
            print(f"  {model:<12}  avg {avg:6.1f}s  ({len(times)} samples)")
        else:
            print(f"  {model:<12}  no results")
    print(f"\nOutputs in: {OUT.resolve()}")
    print("Compare the images/videos side by side to judge quality!")


if __name__ == "__main__":
    main()
