#!/usr/bin/env python3
"""8-minute van-life cooking test video: avatar + B-roll video + stills + voiceover.

Generates all assets via ComfyUI (FLUX stills, Wan 1.3B t2v clips, F5-TTS voice)
then stitches them with ffmpeg.

Usage:
  python3 test_8min_video.py --comfy http://127.0.0.1:8188
"""
import argparse, json, subprocess, time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.comfy import Comfy

OUT = Path("test_8min_output")
OUT.mkdir(exist_ok=True)

FPS = 16
VIDEO_W, VIDEO_H = 832, 480
STILL_W, STILL_H = 1024, 576

REF_AUDIO = "f5_ref.wav"
REF_TEXT = "Today we're going to make something special in our little van kitchen."

REALISTIC_SUFFIX = (
    "photorealistic, natural matte lighting, no glossy reflections, no shiny surfaces, "
    "not airbrushed, not polished, muted desaturated colors, documentary photograph, "
    "natural skin texture, no artificial lighting, no studio look, candid and authentic"
)

AVATAR_PROMPT = (
    "candid photo of a woman in her late 40s with long dark brown hair with grey streaks "
    "in a loose side braid, wearing a rustic earth-tone knit wool sweater, chest and shoulders "
    "framing, looking directly at camera with calm friendly expression, warm natural window "
    "light from the side, cozy camper van interior background with wooden shelves, "
    "matte skin texture, natural imperfections, no makeup, " + REALISTIC_SUFFIX
)

SCRIPT = [
    # --- INTRO (0:00 - 0:30) ---
    {
        "narration": "Welcome back to the van life kitchen. Today we are making a simple one-pot trail chili, perfect for cold nights on the road.",
        "shots": [
            {"type": "avatar", "duration": 4},
            {"type": "still", "duration": 2, "prompt": "exterior of a vintage camper van parked in a desert canyon at sunrise, warm golden light"},
            {"type": "still", "duration": 2, "prompt": "interior of a cozy converted camper van kitchen with wooden shelves and spice jars, warm golden light from window"},
            {"type": "still", "duration": 2, "prompt": "a steaming mug of coffee on a small wooden counter inside a camper van, morning light"},
            {"type": "still", "duration": 3, "prompt": "a cast iron pot and fresh vegetables laid out on a small camper van counter, overhead view, meal prep"},
        ]
    },
    # --- ONE POT INTRO (0:30 - 1:05) ---
    {
        "narration": "The beauty of this recipe is that everything goes into one pot. No fancy equipment needed, just good ingredients and a little patience.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a single cast iron pot on a small camping stove, simple kitchen setup, natural daylight"},
            {"type": "still", "duration": 2, "prompt": "close up of a seasoned cast iron pot surface texture, rustic and well-used, warm tones"},
            {"type": "video", "duration": 4, "prompt": "close up of hands chopping onions on a wooden cutting board, warm kitchen lighting, slow deliberate movements"},
            {"type": "still", "duration": 2, "prompt": "fresh whole vegetables on a rustic wooden surface, onion garlic bell pepper tomatoes, natural light"},
            {"type": "avatar", "duration": 4},
        ]
    },
    # --- PREP VEGETABLES (1:05 - 1:50) ---
    {
        "narration": "Start with your base. One large onion diced, three cloves of garlic minced, and a bell pepper cut into small pieces.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a whole onion on a wooden cutting board with a sharp knife, rustic kitchen, natural light"},
            {"type": "still", "duration": 2, "prompt": "diced onions and minced garlic on a wooden cutting board, overhead view, natural light"},
            {"type": "video", "duration": 4, "prompt": "close up of a bell pepper being sliced with a knife on a cutting board, smooth slow motion"},
            {"type": "still", "duration": 2, "prompt": "three garlic cloves being peeled on a wooden surface, close up, warm light"},
            {"type": "still", "duration": 3, "prompt": "small bowls of chopped vegetables arranged neatly, bell pepper onion garlic, prep station"},
            {"type": "still", "duration": 2, "prompt": "a hand holding a diced bell pepper over a small bowl, close up, natural light"},
        ]
    },
    # --- COOK ONIONS (1:50 - 2:30) ---
    {
        "narration": "Heat some olive oil in your pot until it shimmers. Add the onions first and let them soften for about three minutes.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a bottle of olive oil next to a cast iron pot on a stove, warm kitchen light"},
            {"type": "video", "duration": 5, "prompt": "olive oil being poured into a cast iron pot on a stove, golden liquid flowing, warm lighting"},
            {"type": "still", "duration": 2, "prompt": "shimmering olive oil in the bottom of a hot cast iron pot, close up surface detail"},
            {"type": "still", "duration": 3, "prompt": "diced onions sizzling in a cast iron pot, steam rising, warm kitchen light"},
            {"type": "avatar", "duration": 4},
            {"type": "still", "duration": 2, "prompt": "translucent softened onions in a pot, golden and caramelized edges, close up overhead"},
        ]
    },
    # --- ADD GARLIC & PEPPER (2:30 - 3:05) ---
    {
        "narration": "Now add the garlic and bell pepper. Stir everything together and cook for another two minutes until fragrant.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "minced garlic being added to a pot of onions, close up, warm lighting"},
            {"type": "video", "duration": 4, "prompt": "vegetables being stirred in a pot with a wooden spoon, steam rising, close up cooking shot"},
            {"type": "still", "duration": 2, "prompt": "colorful chopped vegetables in a cast iron pot, garlic and bell peppers, overhead view"},
            {"type": "still", "duration": 2, "prompt": "a wooden spoon resting on the edge of a cast iron pot, steam rising, warm tones"},
            {"type": "still", "duration": 3, "prompt": "aromatic steam rising from a cooking pot, warm ambient lighting, cozy kitchen"},
        ]
    },
    # --- SPICES (3:05 - 4:00) ---
    {
        "narration": "Here is where the magic happens. Add your spices. Two tablespoons of chili powder, one teaspoon of cumin, half a teaspoon of smoked paprika, and a pinch of cayenne if you like heat.",
        "shots": [
            {"type": "avatar", "duration": 5},
            {"type": "still", "duration": 2, "prompt": "small wooden bowls of colorful spices, chili powder cumin paprika, rustic wooden surface"},
            {"type": "still", "duration": 2, "prompt": "a measuring spoon full of dark red chili powder, close up, warm tones"},
            {"type": "still", "duration": 2, "prompt": "ground cumin in a small ceramic bowl, earthy brown color, rustic surface"},
            {"type": "video", "duration": 4, "prompt": "spices being sprinkled into a steaming pot, red and brown powders falling, close up"},
            {"type": "still", "duration": 2, "prompt": "smoked paprika powder on a wooden spoon, deep red color, close up"},
            {"type": "still", "duration": 2, "prompt": "labeled spice jars on a wooden shelf inside a camper van, organized and cozy"},
            {"type": "still", "duration": 2, "prompt": "a pinch of cayenne pepper between fingers over a steaming pot, close up"},
        ]
    },
    # --- TOAST SPICES (4:00 - 4:30) ---
    {
        "narration": "Stir the spices into the vegetables and toast them for about thirty seconds. You will smell them bloom and that is how you know they are ready.",
        "shots": [
            {"type": "video", "duration": 5, "prompt": "wooden spoon stirring spiced vegetables in a pot, rich red and brown colors, steam rising"},
            {"type": "still", "duration": 2, "prompt": "close up of spiced vegetables in a pot, rich earth tones, warm lighting"},
            {"type": "still", "duration": 2, "prompt": "a camper van kitchen with warm light and steam from cooking, atmospheric and cozy"},
            {"type": "avatar", "duration": 3},
        ]
    },
    # --- ADD TOMATOES & BEANS (4:30 - 5:15) ---
    {
        "narration": "Pour in one can of crushed tomatoes and one can of kidney beans, drained. Add about half a cup of water or broth.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a can of crushed tomatoes next to a can of kidney beans on a counter, rustic setting"},
            {"type": "video", "duration": 4, "prompt": "crushed tomatoes being poured from a can into a pot, thick red liquid flowing, cooking"},
            {"type": "still", "duration": 2, "prompt": "kidney beans being drained in a small colander, close up, natural light"},
            {"type": "still", "duration": 2, "prompt": "kidney beans falling into a pot of chili, close up, rich red tones"},
            {"type": "still", "duration": 2, "prompt": "a small measuring cup of broth next to a steaming pot, warm kitchen"},
            {"type": "avatar", "duration": 4},
        ]
    },
    # --- SIMMER (5:15 - 6:00) ---
    {
        "narration": "Give it a good stir, bring it to a gentle simmer, then lower the heat. Let it cook for about twenty minutes, stirring occasionally.",
        "shots": [
            {"type": "video", "duration": 5, "prompt": "a pot of chili simmering gently, small bubbles on the surface, steam rising, warm lighting"},
            {"type": "still", "duration": 2, "prompt": "a bubbling pot of red chili stew, overhead view, rustic kitchen setting"},
            {"type": "still", "duration": 2, "prompt": "the dial of a small camping stove turned to low heat, close up"},
            {"type": "still", "duration": 3, "prompt": "a wooden spoon stirring thick chili in a pot, overhead view, warm tones"},
            {"type": "still", "duration": 2, "prompt": "a small kitchen timer next to a steaming pot on a camping stove inside a van"},
            {"type": "avatar", "duration": 3},
        ]
    },
    # --- SIMMERING TIP (6:00 - 6:40) ---
    {
        "narration": "While the chili simmers, let me share a tip. The longer you let it cook, the better the flavors meld together. If you have the time, forty minutes is even better.",
        "shots": [
            {"type": "avatar", "duration": 5},
            {"type": "still", "duration": 3, "prompt": "view through a camper van window showing a desert sunset landscape, warm golden light"},
            {"type": "still", "duration": 2, "prompt": "a person relaxing in a camp chair outside a camper van, desert landscape, golden hour"},
            {"type": "still", "duration": 2, "prompt": "a pot simmering on a stove with steam curling upward, soft focus background, warm"},
            {"type": "still", "duration": 3, "prompt": "a person reading a book in a camper van with a pot simmering on the stove, cozy interior"},
        ]
    },
    # --- SEASON (6:40 - 7:10) ---
    {
        "narration": "Season with salt and pepper to taste. I like to add a squeeze of lime juice at the end for brightness.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a salt cellar and pepper grinder on a rustic wooden surface, warm light"},
            {"type": "still", "duration": 2, "prompt": "coarse salt being pinched over a pot of chili, close up fingers, warm tones"},
            {"type": "video", "duration": 4, "prompt": "a lime being squeezed over a bowl of chili, juice drops falling, close up slow motion"},
            {"type": "still", "duration": 2, "prompt": "a halved lime next to a steaming bowl of chili, rustic wooden surface, warm light"},
            {"type": "avatar", "duration": 4},
        ]
    },
    # --- SERVE (7:10 - 7:40) ---
    {
        "narration": "Serve it up in a sturdy bowl. Top with some shredded cheese, a dollop of sour cream, and fresh cilantro if you have it.",
        "shots": [
            {"type": "video", "duration": 4, "prompt": "chili being ladled into a ceramic bowl, thick red stew pouring, steam rising"},
            {"type": "still", "duration": 2, "prompt": "shredded cheddar cheese being sprinkled over a bowl of hot chili, close up"},
            {"type": "still", "duration": 2, "prompt": "a dollop of white sour cream on top of a red bowl of chili, contrast colors"},
            {"type": "still", "duration": 2, "prompt": "fresh green cilantro leaves being placed on top of a bowl of chili, garnish close up"},
            {"type": "still", "duration": 3, "prompt": "a finished bowl of chili topped with cheese sour cream and cilantro, rustic presentation, overhead"},
        ]
    },
    # --- OUTRO (7:40 - 8:10) ---
    {
        "narration": "And there you have it. A warm hearty trail chili made right here in the van. Simple ingredients, big flavor, and it feeds you for days. Thanks for watching, and I will see you on the next stop.",
        "shots": [
            {"type": "still", "duration": 2, "prompt": "a person holding a warm bowl of chili while sitting at a fold-out table in a camper van"},
            {"type": "still", "duration": 2, "prompt": "a spoonful of chili being lifted from a bowl, steam rising, close up, warm light"},
            {"type": "still", "duration": 2, "prompt": "an empty clean bowl and spoon on a rustic table, satisfied meal complete"},
            {"type": "video", "duration": 4, "prompt": "a camper van driving slowly down a desert highway at sunset, wide cinematic shot, dust trail"},
            {"type": "still", "duration": 2, "prompt": "a camper van parked under stars in a desert landscape, night sky, peaceful"},
            {"type": "avatar", "duration": 5},
            {"type": "still", "duration": 3, "prompt": "a desert road stretching into the horizon at golden hour, wide landscape, end of journey"},
        ]
    },
]


def gen_voiceover(comfy: Comfy, out: Path) -> Path:
    full_script = "\n\n".join(seg["narration"] for seg in SCRIPT)
    from director.tts import chunks as split_chunks
    cs = split_chunks(full_script)
    print(f"\n=== VOICEOVER ({len(cs)} chunks) ===")
    parts = []
    for i, c in enumerate(cs):
        part = out / f"vo_{i:04d}.wav"
        if part.exists() and part.stat().st_size > 0:
            parts.append(part)
            print(f"  [{i+1}/{len(cs)}] skip (cached)")
            continue
        print(f"  [{i+1}/{len(cs)}] {len(c)} chars...", end=" ", flush=True)
        t0 = time.time()
        try:
            comfy.tts(c, Path(f"/workspace/runpod-slim/ComfyUI/input/{REF_AUDIO}"),
                      REF_TEXT, part, seed=1, speed=1.0)
            print(f"OK {time.time()-t0:.1f}s")
            parts.append(part)
        except Exception as e:
            print(f"FAILED: {e}")
    if not parts:
        raise RuntimeError("No voiceover parts produced")
    dest = out / "voiceover.wav"
    if len(parts) == 1:
        import shutil
        shutil.copy2(parts[0], dest)
    else:
        listfile = out / "vo_list.txt"
        listfile.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                        "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1", str(dest)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"  -> {dest}")
    return dest


def gen_stills(comfy: Comfy, out: Path) -> dict:
    stills = {}
    idx = 0
    for seg_i, seg in enumerate(SCRIPT):
        for shot in seg["shots"]:
            if shot["type"] == "still":
                key = f"still_{idx:04d}"
                dest = out / f"{key}.png"
                if dest.exists() and dest.stat().st_size > 0:
                    stills[key] = dest
                    print(f"  [{key}] skip (cached)")
                    idx += 1
                    continue
                print(f"  [{key}] {shot['prompt'][:50]}...", end=" ", flush=True)
                t0 = time.time()
                try:
                    prompt = f"{shot['prompt']}, {REALISTIC_SUFFIX}"
                    comfy.flux_still(prompt, STILL_W, STILL_H, dest,
                                    seed=1000+idx, lora=0.0, guidance=3.5, steps=20)
                    stills[key] = dest
                    print(f"OK {time.time()-t0:.1f}s")
                except Exception as e:
                    print(f"FAILED: {e}")
                idx += 1
    return stills


def gen_videos(comfy: Comfy, out: Path) -> dict:
    videos = {}
    idx = 0
    for seg_i, seg in enumerate(SCRIPT):
        for shot in seg["shots"]:
            if shot["type"] == "video":
                key = f"video_{idx:04d}"
                dest = out / f"{key}.mp4"
                if dest.exists() and dest.stat().st_size > 0:
                    videos[key] = dest
                    print(f"  [{key}] skip (cached)")
                    idx += 1
                    continue
                frames = max(17, int(shot["duration"] * FPS))
                # round to 4n+1 for Wan
                import math
                n = max(1, math.ceil((frames - 1) / 4))
                frames = 4 * n + 1
                print(f"  [{key}] {frames}f {shot['prompt'][:50]}...", end=" ", flush=True)
                t0 = time.time()
                try:
                    prompt = f"{shot['prompt']}, realistic natural lighting, not glossy, not shiny"
                    comfy.wan_t2v(prompt, VIDEO_W, VIDEO_H, frames, dest,
                                 seed=2000+idx)
                    videos[key] = dest
                    print(f"OK {time.time()-t0:.1f}s")
                except Exception as e:
                    print(f"FAILED: {e}")
                idx += 1
    return videos


def gen_avatars(comfy: Comfy, out: Path, avatar_image: Path | None = None) -> dict:
    """Generate avatar clips using i2v (image-to-video) from a consistent source image."""
    if avatar_image is None:
        avatar_image = Path("/workspace/runpod-slim/ComfyUI/input/avatar_presenter.png")
    avatars = {}
    idx = 0
    for seg_i, seg in enumerate(SCRIPT):
        for shot in seg["shots"]:
            if shot["type"] == "avatar":
                key = f"avatar_{idx:04d}"
                dest = out / f"{key}.mp4"
                if dest.exists() and dest.stat().st_size > 0:
                    avatars[key] = dest
                    print(f"  [{key}] skip (cached)")
                    idx += 1
                    continue
                frames = max(17, int(shot["duration"] * FPS))
                import math
                n = max(1, math.ceil((frames - 1) / 4))
                frames = 4 * n + 1
                prompt = (
                    "a woman speaking calmly to camera, subtle natural head movements "
                    "and blinking, warm cozy interior background, "
                    "natural matte lighting, documentary interview style, "
                    "realistic skin texture, muted earthy colors"
                )
                print(f"  [{key}] {frames}f avatar (i2v)...", end=" ", flush=True)
                t0 = time.time()
                try:
                    comfy.wan_i2v(avatar_image, prompt, frames,
                                 VIDEO_W, VIDEO_H, dest)
                    avatars[key] = dest
                    print(f"OK {time.time()-t0:.1f}s")
                except Exception as e:
                    print(f"FAILED: {e}")
                idx += 1
    return avatars


def assemble(vo: Path, stills: dict, videos: dict, avatars: dict, out: Path) -> Path:
    """Stitch all shots into a single video with voiceover."""
    clips = []
    still_idx = video_idx = avatar_idx = 0
    for seg in SCRIPT:
        for shot in seg["shots"]:
            if shot["type"] == "still":
                key = f"still_{still_idx:04d}"
                if key in stills:
                    # convert still to video clip
                    clip = out / f"clip_{key}.mp4"
                    if not clip.exists():
                        subprocess.run([
                            "ffmpeg", "-y", "-loop", "1", "-i", str(stills[key]),
                            "-t", str(shot["duration"]),
                            "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2",
                            "-r", str(FPS), "-pix_fmt", "yuv420p",
                            "-c:v", "libx264", "-crf", "18", str(clip)
                        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    clips.append(clip)
                still_idx += 1
            elif shot["type"] == "video":
                key = f"video_{video_idx:04d}"
                if key in videos:
                    clips.append(videos[key])
                video_idx += 1
            elif shot["type"] == "avatar":
                key = f"avatar_{avatar_idx:04d}"
                if key in avatars:
                    clips.append(avatars[key])
                avatar_idx += 1

    if not clips:
        raise RuntimeError("No clips to assemble")

    # concat all clips
    listfile = out / "clips_list.txt"
    # normalize all clips to same format first
    norm_clips = []
    for i, c in enumerate(clips):
        nc = out / f"norm_{i:04d}.mp4"
        if not nc.exists():
            subprocess.run([
                "ffmpeg", "-y", "-i", str(c),
                "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-an", str(nc)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        norm_clips.append(nc)

    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in norm_clips))
    video_only = out / "video_only.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(video_only)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # merge with voiceover
    final = out / "final_8min.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_only), "-i", str(vo),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(final)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"\n=== FINAL VIDEO: {final} ===")
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy", required=True, help="ComfyUI URL")
    ap.add_argument("--skip-vo", action="store_true", help="Skip voiceover generation")
    ap.add_argument("--skip-stills", action="store_true", help="Skip still generation")
    ap.add_argument("--skip-videos", action="store_true", help="Skip video generation")
    ap.add_argument("--skip-avatars", action="store_true", help="Skip avatar generation")
    ap.add_argument("--assemble-only", action="store_true", help="Only assemble from cached assets")
    args = ap.parse_args()

    comfy = Comfy(args.comfy)

    # Count shots
    n_stills = sum(1 for s in SCRIPT for sh in s["shots"] if sh["type"] == "still")
    n_videos = sum(1 for s in SCRIPT for sh in s["shots"] if sh["type"] == "video")
    n_avatars = sum(1 for s in SCRIPT for sh in s["shots"] if sh["type"] == "avatar")
    total_dur = sum(sh["duration"] for s in SCRIPT for sh in s["shots"])
    print(f"Plan: {n_stills} stills, {n_videos} video clips, {n_avatars} avatar shots")
    print(f"Total duration: ~{total_dur}s ({total_dur/60:.1f} min)")

    vo = OUT / "voiceover.wav"
    if not args.skip_vo and not args.assemble_only:
        print("\n=== VOICEOVER ===")
        vo = gen_voiceover(comfy, OUT)

    stills = {}
    if not args.skip_stills and not args.assemble_only:
        print(f"\n=== STILLS ({n_stills}) ===")
        stills = gen_stills(comfy, OUT)
    else:
        # load cached
        for i in range(n_stills):
            p = OUT / f"still_{i:04d}.png"
            if p.exists():
                stills[f"still_{i:04d}"] = p

    videos = {}
    if not args.skip_videos and not args.assemble_only:
        print(f"\n=== VIDEO CLIPS ({n_videos}) ===")
        videos = gen_videos(comfy, OUT)
    else:
        for i in range(n_videos):
            p = OUT / f"video_{i:04d}.mp4"
            if p.exists():
                videos[f"video_{i:04d}"] = p

    avatars = {}
    if not args.skip_avatars and not args.assemble_only:
        print(f"\n=== AVATAR SHOTS ({n_avatars}) ===")
        avatars = gen_avatars(comfy, OUT, Path("/workspace/runpod-slim/ComfyUI/input/avatar_presenter.png"))
    else:
        for i in range(n_avatars):
            p = OUT / f"avatar_{i:04d}.mp4"
            if p.exists():
                avatars[f"avatar_{i:04d}"] = p

    print(f"\nAssets: {len(stills)} stills, {len(videos)} videos, {len(avatars)} avatars")

    if vo.exists():
        print("\n=== ASSEMBLY ===")
        final = assemble(vo, stills, videos, avatars, OUT)
        print(f"Done! Final video: {final}")
    else:
        print("\nSkipping assembly (no voiceover)")


if __name__ == "__main__":
    main()
