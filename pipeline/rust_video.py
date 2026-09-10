#!/usr/bin/env python3
"""5-6 minute rust removal video recreation in the style of Sal Whitaker.

Uses GenAI Pro for image generation + avatar talking head clips.
Voiceover MP3s downloaded separately from vidIQ.
Assembly via ffmpeg with Ken Burns effects, split-screen, and hard cuts.

Usage:
  python rust_video.py --api-key <GENAIPRO_KEY> --gen-images
  python rust_video.py --api-key <GENAIPRO_KEY> --gen-avatar
  python rust_video.py --assemble-only
"""
import argparse, subprocess, random, math
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.veo import Veo

OUT = Path("rust_output")
OUT.mkdir(exist_ok=True)

FPS = 24
VIDEO_W, VIDEO_H = 1280, 720

AVATAR_PROMPT = (
    "Portrait photograph of a weathered American mechanic in his late 50s "
    "with gray hair and reading glasses pushed up on his forehead, "
    "wearing a navy blue work shirt with grease stains, "
    "standing in front of a tool pegboard in a garage workshop, "
    "warm overhead lighting, friendly confident expression, "
    "chest and shoulders framing, facing camera"
)

AVATAR_IMAGE = OUT / "avatar_mechanic.png"

# B-roll images to generate via GenAI Pro create-image
BROLL_IMAGES = [
    {"name": "rusty_frame_rail", "prompt": "Close-up photograph of heavy orange flaky rust on a truck frame rail underside, flashlight beam illuminating the rust texture, dark garage background"},
    {"name": "rusty_rocker_panel", "prompt": "Close-up photograph of rust bubbling through paint on a car rocker panel behind the front tire, peeling flakes, natural daylight"},
    {"name": "hand_peeling_rust", "prompt": "First person POV of a hand peeling flaky rust scale off a steel frame rail, extreme close-up, workshop lighting"},
    {"name": "repair_invoice_high", "prompt": "Overhead photograph of a printed auto repair invoice on a clipboard showing a circled total of $1500, pen beside it, shop counter background"},
    {"name": "repair_invoice_low", "prompt": "Photograph of a small brown chemical bottle next to a $10 bill and loose coins on a workbench, simple clean shot"},
    {"name": "tools_on_tarp", "prompt": "Overhead photograph of rust removal tools laid out on a blue tarp: wire brush, chemical bottle, rubber gloves, old rags, flathead screwdriver, driveway concrete visible"},
    {"name": "flashlight_under_truck", "prompt": "Low angle photograph of a flashlight beam shining on a truck frame rail underside, person lying on their side on a garage floor, warm lighting"},
    {"name": "screwdriver_poke_solid", "prompt": "Extreme close-up of a flathead screwdriver tip pressing against surface rust on solid metal frame, showing the metal is firm underneath"},
    {"name": "screwdriver_poke_through", "prompt": "Close-up photograph of a screwdriver puncturing through severely rusted perforated metal on a car frame, hole visible, dramatic lighting"},
    {"name": "chemical_bottle_pink", "prompt": "Product-style photograph of a small pink gel rust dissolver bottle on a clean workbench, 8 ounce size, hardware store brand, clear label visible"},
    {"name": "brushing_chemical", "prompt": "First person POV close-up of a hand applying pink gel chemical with a small brush onto rusty metal surface, chemical bubbling on contact"},
    {"name": "wire_brush_scrubbing", "prompt": "Close-up photograph of a wire brush scrubbing rust off metal, revealing bare shiny steel underneath, rust flakes scattered around"},
    {"name": "water_on_rust", "prompt": "Extreme close-up macro photograph of water droplets sitting on a rusty orange metal surface, shallow depth of field"},
    {"name": "mechanic_under_lift", "prompt": "Low angle photograph of a mechanic in work clothes pointing at the undercarriage of a truck on a two-post shop lift, clipboard in other hand"},
    {"name": "bare_metal_after", "prompt": "Close-up photograph of clean bare gray metal after rust removal, showing the phosphate conversion coating, smooth surface, workshop lighting"},
    {"name": "primer_spray_can", "prompt": "Photograph of a can of self-etching primer spray paint next to a wire brush and chemical bottle on a garage workbench, ready to use"},
    {"name": "undercoat_spray", "prompt": "Photograph of a mechanic spraying black rubberized undercoating on a clean truck undercarriage on a shop lift, spray mist visible"},
    {"name": "paint_bubble_rust", "prompt": "Close-up photograph of bubbling paint with rust bleeding through on a car body panel, showing where rust formed underneath the paint"},
    {"name": "four_steps_paper", "prompt": "Top-down photograph of lined paper with handwritten numbers 1 through 4 with brief labels next to each, pen beside paper, clean desk"},
    {"name": "truck_driveway", "prompt": "Wide photograph of a pickup truck parked on a residential driveway, person crouching beside it with a flashlight looking at the frame, afternoon light"},
    {"name": "baking_soda_rinse", "prompt": "Photograph of a hand holding a spray bottle of baking soda water solution next to a clean rag on a workbench, simple setup"},
    {"name": "flash_rust_example", "prompt": "Close-up photograph of bare metal surface showing faint orange flash rust forming overnight, microscopic new rust layer on previously clean steel"},
    {"name": "before_after_split", "prompt": "Side by side comparison photograph, left showing heavy orange rust on metal, right showing clean treated bare gray metal, same lighting, workshop bench"},
    {"name": "brake_lines_rusty", "prompt": "Close-up photograph of thin steel brake lines running along a truck frame rail, showing flaky puffed-up rust on the lines, flashlight illumination"},
]

# Avatar talking head clips via frames-to-video
AVATAR_CLIPS = [
    {"name": "avatar_intro", "prompt": "The mechanic in the image talking directly to camera, calm confident expression, slight head nod, workshop background with tools", "duration": 5},
    {"name": "avatar_explain", "prompt": "The mechanic in the image gesturing with one hand while speaking, making a point, engaged expression, workshop background", "duration": 5},
    {"name": "avatar_warning", "prompt": "The mechanic in the image speaking seriously to camera, slight lean forward, concerned expression, emphasizing an important point", "duration": 5},
    {"name": "avatar_friendly", "prompt": "The mechanic in the image smiling warmly at camera, relaxed posture, nodding in agreement, encouraging expression", "duration": 5},
    {"name": "avatar_pointing", "prompt": "The mechanic in the image pointing to the side as if directing attention to something off screen, speaking animatedly", "duration": 5},
    {"name": "avatar_closing", "prompt": "The mechanic in the image giving a confident thumbs up to camera, warm smile, final goodbye energy, workshop background", "duration": 5},
]

# Video timeline: each segment is either solo avatar, solo broll, or split-screen
# type: "avatar" | "broll" | "split" | "graphic"
# For broll/split, "image" references a BROLL_IMAGES name
# For avatar/split, "avatar" references an AVATAR_CLIPS name
TIMELINE = [
    # 0:00-0:04 Avatar intro
    {"type": "avatar", "avatar": "avatar_intro", "start": 0, "dur": 4},
    # 0:04-0:07 B-roll: rusty frame rail
    {"type": "broll", "image": "rusty_frame_rail", "dur": 3},
    # 0:07-0:10 Split: avatar + rusty rocker
    {"type": "split", "avatar": "avatar_intro", "image": "rusty_rocker_panel", "dur": 3},
    # 0:10-0:13 B-roll: hand peeling rust
    {"type": "broll", "image": "hand_peeling_rust", "dur": 3},
    # 0:13-0:16 B-roll: water on rust macro
    {"type": "broll", "image": "water_on_rust", "dur": 3},
    # 0:16-0:19 Avatar speaking
    {"type": "avatar", "avatar": "avatar_explain", "start": 0, "dur": 3},
    # 0:19-0:22 B-roll: repair invoice high
    {"type": "broll", "image": "repair_invoice_high", "dur": 3},
    # 0:22-0:25 B-roll: brushing chemical
    {"type": "broll", "image": "brushing_chemical", "dur": 3},
    # 0:25-0:28 B-roll: wire brush scrubbing
    {"type": "broll", "image": "wire_brush_scrubbing", "dur": 3},
    # 0:28-0:31 Split: avatar + mechanic under lift
    {"type": "split", "avatar": "avatar_explain", "image": "mechanic_under_lift", "dur": 3},
    # 0:31-0:34 B-roll: invoice high circled
    {"type": "broll", "image": "repair_invoice_high", "dur": 3},
    # 0:34-0:37 Avatar warning about upsell
    {"type": "avatar", "avatar": "avatar_warning", "start": 0, "dur": 3},
    # 0:37-0:40 B-roll: undercoat spray
    {"type": "broll", "image": "undercoat_spray", "dur": 3},
    # 0:40-0:43 Split: avatar + chemical bottle
    {"type": "split", "avatar": "avatar_warning", "image": "chemical_bottle_pink", "dur": 3},
    # 0:43-0:46 B-roll: cheap bottle vs cash
    {"type": "broll", "image": "repair_invoice_low", "dur": 3},
    # 0:46-0:49 Avatar - good news
    {"type": "avatar", "avatar": "avatar_friendly", "start": 0, "dur": 3},
    # 0:49-0:52 B-roll: tools on tarp
    {"type": "broll", "image": "tools_on_tarp", "dur": 3},
    # -- AD BREAK ~0:52-1:10 (skip for now, placeholder) --
    # 1:10-1:13 Avatar back
    {"type": "avatar", "avatar": "avatar_friendly", "start": 2, "dur": 3},
    # 1:13-1:16 B-roll: four steps paper
    {"type": "broll", "image": "four_steps_paper", "dur": 3},
    # 1:16-1:19 Avatar pointing
    {"type": "avatar", "avatar": "avatar_pointing", "start": 0, "dur": 3},
    # -- CHAPTER 2: Inspection --
    # 1:19-1:23 B-roll: truck on driveway
    {"type": "broll", "image": "truck_driveway", "dur": 4},
    # 1:23-1:26 B-roll: flashlight under truck
    {"type": "broll", "image": "flashlight_under_truck", "dur": 3},
    # 1:26-1:29 Split: avatar + rusty frame
    {"type": "split", "avatar": "avatar_explain", "image": "rusty_frame_rail", "dur": 3},
    # 1:29-1:33 B-roll: screwdriver poke solid
    {"type": "broll", "image": "screwdriver_poke_solid", "dur": 4},
    # 1:33-1:36 Avatar explain
    {"type": "avatar", "avatar": "avatar_explain", "start": 2, "dur": 3},
    # 1:36-1:40 B-roll: screwdriver poke through
    {"type": "broll", "image": "screwdriver_poke_through", "dur": 4},
    # 1:40-1:43 Avatar warning
    {"type": "avatar", "avatar": "avatar_warning", "start": 2, "dur": 3},
    # 1:43-1:46 B-roll: paint bubble rust
    {"type": "broll", "image": "paint_bubble_rust", "dur": 3},
    # 1:46-1:50 Split: avatar + brake lines
    {"type": "split", "avatar": "avatar_warning", "image": "brake_lines_rusty", "dur": 4},
    # -- CHAPTER 3: The Bottle --
    # 1:50-1:53 Avatar friendly
    {"type": "avatar", "avatar": "avatar_friendly", "start": 2, "dur": 3},
    # 1:53-1:57 B-roll: chemical bottle pink
    {"type": "broll", "image": "chemical_bottle_pink", "dur": 4},
    # 1:57-2:00 B-roll: brushing chemical
    {"type": "broll", "image": "brushing_chemical", "dur": 3},
    # 2:00-2:04 B-roll: bare metal after
    {"type": "broll", "image": "bare_metal_after", "dur": 4},
    # 2:04-2:07 Split: avatar + before/after
    {"type": "split", "avatar": "avatar_friendly", "image": "before_after_split", "dur": 3},
    # 2:07-2:10 B-roll: invoice comparison
    {"type": "broll", "image": "repair_invoice_high", "dur": 3},
    # 2:10-2:13 B-roll: cheap fix
    {"type": "broll", "image": "repair_invoice_low", "dur": 3},
    # 2:13-2:16 Avatar explain
    {"type": "avatar", "avatar": "avatar_explain", "start": 3, "dur": 3},
    # -- CHAPTER 4: Making it hold --
    # 2:16-2:19 Avatar warning - don't skip
    {"type": "avatar", "avatar": "avatar_warning", "start": 3, "dur": 3},
    # 2:19-2:22 B-roll: flash rust
    {"type": "broll", "image": "flash_rust_example", "dur": 3},
    # 2:22-2:26 B-roll: baking soda rinse
    {"type": "broll", "image": "baking_soda_rinse", "dur": 4},
    # 2:26-2:29 B-roll: primer spray can
    {"type": "broll", "image": "primer_spray_can", "dur": 3},
    # 2:29-2:33 Split: avatar + bare metal
    {"type": "split", "avatar": "avatar_pointing", "image": "bare_metal_after", "dur": 4},
    # 2:33-2:36 B-roll: before/after
    {"type": "broll", "image": "before_after_split", "dur": 3},
    # 2:36-2:40 Avatar closing
    {"type": "avatar", "avatar": "avatar_closing", "start": 0, "dur": 4},
    # 2:40-2:44 B-roll: truck driveway final
    {"type": "broll", "image": "truck_driveway", "dur": 4},
    # 2:44-2:48 Avatar final
    {"type": "avatar", "avatar": "avatar_closing", "start": 2, "dur": 4},
]


def _ken_burns(image_path: Path, dest: Path, duration: float):
    """Apply Ken Burns zoom/pan effect to a still image."""
    styles = [
        f"zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='min(zoom+0.001,1.2)':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='min(zoom+0.001,1.2)':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,y+1)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)+sin(on/30)*20':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
    ]
    style = random.choice(styles)
    vf = f"{style},format=yuv420p"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _split_screen(avatar_clip: Path, broll_clip: Path, dest: Path, duration: float):
    """Create split-screen: avatar 40% left, B-roll 60% right."""
    aw = int(VIDEO_W * 0.4)
    bw = VIDEO_W - aw
    vf = (
        f"[0:v]scale={aw}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
        f"pad={aw}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2[left];"
        f"[1:v]scale={bw}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
        f"pad={bw}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2[right];"
        f"[left][right]hstack"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(avatar_clip), "-i", str(broll_clip),
        "-filter_complex", vf, "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _trim_clip(src: Path, dest: Path, start: float, duration: float):
    """Trim a video clip."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(src),
        "-t", str(duration), "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gen_images(veo: Veo):
    """Generate all B-roll images via GenAI Pro."""
    print(f"Generating {len(BROLL_IMAGES)} B-roll images...")
    for img in BROLL_IMAGES:
        dest = OUT / f"{img['name']}.png"
        if dest.exists():
            print(f"  [{img['name']}] skip (cached)")
            continue
        print(f"  [{img['name']}] generating...")
        try:
            veo.create_image(img["prompt"], dest)
            print(f"  [{img['name']}] OK")
        except Exception as e:
            print(f"  [{img['name']}] FAILED: {e}")


def gen_avatar_image(veo: Veo):
    """Generate the avatar mechanic image."""
    if AVATAR_IMAGE.exists():
        print(f"Avatar image exists: {AVATAR_IMAGE}")
        return
    print("Generating avatar image...")
    veo.create_image(AVATAR_PROMPT, AVATAR_IMAGE)
    print(f"Avatar saved: {AVATAR_IMAGE}")


def gen_avatar_clips(veo: Veo):
    """Generate avatar talking head clips via frames-to-video."""
    if not AVATAR_IMAGE.exists():
        print("ERROR: Generate avatar image first (--gen-avatar-image)")
        return
    print(f"Generating {len(AVATAR_CLIPS)} avatar clips...")
    for clip in AVATAR_CLIPS:
        dest = OUT / f"{clip['name']}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [{clip['name']}] skip (cached)")
            continue
        print(f"  [{clip['name']}] generating...")
        try:
            veo.frames_to_video(str(AVATAR_IMAGE), clip["prompt"], dest,
                                duration=clip["duration"])
            print(f"  [{clip['name']}] OK")
        except Exception as e:
            print(f"  [{clip['name']}] FAILED: {e}")


def assemble():
    """Assemble all segments into final video with voiceover."""
    segments = []

    for i, seg in enumerate(TIMELINE):
        seg_dest = OUT / f"seg_{i:04d}.mp4"
        if seg_dest.exists():
            segments.append(seg_dest)
            print(f"  [seg_{i:04d}] skip (cached)")
            continue

        dur = seg["dur"]

        if seg["type"] == "avatar":
            avatar_clip = OUT / f"{seg['avatar']}.mp4"
            if not avatar_clip.exists():
                print(f"  [seg_{i:04d}] MISSING avatar {seg['avatar']}, using black")
                _black_frame(seg_dest, dur)
            else:
                start = seg.get("start", 0)
                _trim_clip(avatar_clip, seg_dest, start, dur)
                # Scale to target resolution
                scaled = OUT / f"seg_{i:04d}_scaled.mp4"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(seg_dest),
                    "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-an", str(scaled)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                scaled.replace(seg_dest)

        elif seg["type"] == "broll":
            image_path = OUT / f"{seg['image']}.png"
            if not image_path.exists():
                print(f"  [seg_{i:04d}] MISSING image {seg['image']}, using black")
                _black_frame(seg_dest, dur)
            else:
                _ken_burns(image_path, seg_dest, dur)

        elif seg["type"] == "split":
            avatar_clip = OUT / f"{seg['avatar']}.mp4"
            image_path = OUT / f"{seg['image']}.png"
            if not avatar_clip.exists() or not image_path.exists():
                print(f"  [seg_{i:04d}] MISSING assets for split, using black")
                _black_frame(seg_dest, dur)
            else:
                # Make ken burns clip for the image side
                broll_temp = OUT / f"split_broll_{i:04d}.mp4"
                _ken_burns(image_path, broll_temp, dur)
                # Trim avatar
                avatar_temp = OUT / f"split_avatar_{i:04d}.mp4"
                start = seg.get("start", 0)
                _trim_clip(avatar_clip, avatar_temp, start, dur)
                # Composite split screen
                _split_screen(avatar_temp, broll_temp, seg_dest, dur)
                broll_temp.unlink(missing_ok=True)
                avatar_temp.unlink(missing_ok=True)

        segments.append(seg_dest)
        print(f"  [seg_{i:04d}] OK ({seg['type']})")

    # Concat all segments
    listfile = OUT / "segments_list.txt"
    listfile.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))

    video_only = OUT / "rust_video_noaudio.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(video_only)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nVideo assembled (no audio): {video_only}")

    # Merge voiceover if available
    vo_parts = sorted(OUT.glob("voiceover_part*.mp3"))
    if vo_parts:
        # Concat voiceover parts
        if len(vo_parts) > 1:
            vo_list = OUT / "vo_list.txt"
            vo_list.write_text("".join(f"file '{p.resolve()}'\n" for p in vo_parts))
            vo_merged = OUT / "voiceover_full.mp3"
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vo_list),
                "-c:a", "copy", str(vo_merged)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            vo_merged = vo_parts[0]

        final = OUT / "rust_video_final.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_only), "-i", str(vo_merged),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Final video with voiceover: {final}")
    else:
        print("No voiceover files found. Place voiceover_part1.mp3 etc in rust_output/")


def _black_frame(dest: Path, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=black:s={VIDEO_W}x{VIDEO_H}:r={FPS}:d={duration}",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18",
        str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--gen-images", action="store_true", help="Generate B-roll images")
    ap.add_argument("--gen-avatar-image", action="store_true", help="Generate avatar image")
    ap.add_argument("--gen-avatar", action="store_true", help="Generate avatar talking head clips")
    ap.add_argument("--assemble-only", action="store_true", help="Skip generation, just assemble")
    args = ap.parse_args()

    if args.assemble_only:
        print("=== ASSEMBLY ===")
        assemble()
        return

    if not args.api_key:
        print("ERROR: --api-key required for generation")
        return

    veo = Veo(args.api_key)
    credits = veo.credits()
    print(f"Credits available: {credits}")

    if args.gen_avatar_image:
        gen_avatar_image(veo)

    if args.gen_images:
        print(f"\n=== GENERATING {len(BROLL_IMAGES)} B-ROLL IMAGES ===")
        gen_images(veo)

    if args.gen_avatar:
        print(f"\n=== GENERATING {len(AVATAR_CLIPS)} AVATAR CLIPS ===")
        gen_avatar_clips(veo)

    if not args.gen_images and not args.gen_avatar and not args.gen_avatar_image:
        print("\nSpecify --gen-images, --gen-avatar-image, --gen-avatar, or --assemble-only")

    total_dur = sum(s["dur"] for s in TIMELINE)
    print(f"\nTimeline: {len(TIMELINE)} segments, ~{total_dur}s ({total_dur/60:.1f} min)")
    print(f"B-roll images needed: {len(BROLL_IMAGES)}")
    print(f"Avatar clips needed: {len(AVATAR_CLIPS)}")


if __name__ == "__main__":
    main()
