#!/usr/bin/env python3
"""5-minute rust removal video recreation in the style of Sal Whitaker.

Uses GenAI Pro for image generation + avatar talking head clips.
All B-roll is still images with Ken Burns zoom/pan effects.
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

# B-roll STILL IMAGES (Ken Burns zoom/pan) — 50 images, all B-roll
BROLL_IMAGES = [
    {"name": "rusty_frame_rail", "prompt": "Close-up photograph of heavy orange flaky rust on a truck frame rail underside, flashlight beam illuminating the rust texture, dark garage background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rusty_rocker_panel", "prompt": "Close-up photograph of rust bubbling through paint on a car rocker panel behind the front tire, peeling flakes, natural daylight, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "repair_invoice_high", "prompt": "Overhead photograph of a printed auto repair invoice on a clipboard showing a circled total of $1500, pen beside it, shop counter background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "repair_invoice_low", "prompt": "Photograph of a small brown chemical bottle next to a $10 bill and loose coins on a workbench, simple clean shot, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "tools_on_tarp", "prompt": "Overhead photograph of rust removal tools laid out on a blue tarp: wire brush, chemical bottle, rubber gloves, old rags, flathead screwdriver, driveway concrete visible, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "flashlight_under_truck", "prompt": "Low angle photograph of a flashlight beam shining on a truck frame rail underside, person lying on their side on a garage floor, warm lighting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "chemical_bottle_pink", "prompt": "Product-style photograph of a small pink gel rust dissolver bottle on a clean workbench, 8 ounce size, hardware store brand, clear label visible, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "water_on_rust", "prompt": "Extreme close-up macro photograph of water droplets sitting on a rusty orange metal surface, shallow depth of field, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "bare_metal_after", "prompt": "Close-up photograph of clean bare gray metal after rust removal, showing the phosphate conversion coating, smooth surface, workshop lighting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "primer_spray_can", "prompt": "Photograph of a can of self-etching primer spray paint next to a wire brush and chemical bottle on a garage workbench, ready to use, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "paint_bubble_rust", "prompt": "Close-up photograph of bubbling paint with rust bleeding through on a car body panel, showing where rust formed underneath the paint, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "four_steps_paper", "prompt": "Top-down photograph of lined paper with handwritten numbers 1 through 4 with brief labels next to each, pen beside paper, clean desk, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "truck_driveway", "prompt": "Wide photograph of a pickup truck parked on a residential driveway, person crouching beside it with a flashlight looking at the frame, afternoon light, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "flash_rust_example", "prompt": "Close-up photograph of bare metal surface showing faint orange flash rust forming overnight, microscopic new rust layer on previously clean steel, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "before_after_split", "prompt": "Side by side comparison photograph, left showing heavy orange rust on metal, right showing clean treated bare gray metal, same lighting, workshop bench, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "brake_lines_rusty", "prompt": "Close-up photograph of thin steel brake lines running along a truck frame rail, showing flaky puffed-up rust on the lines, flashlight illumination, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rust_scale_closeup", "prompt": "Extreme macro photograph of layered rust scale flaking off steel, showing the orange and brown layers of iron oxide, sharp focus, dark background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "wheel_well_rust", "prompt": "Photograph of a car wheel well with rust eating through the inner fender, visible holes and brown staining, natural daylight, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rubber_gloves_table", "prompt": "Photograph of yellow rubber gloves laid next to a wire brush and chemical bottle on a garage workbench, ready for rust treatment work, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rust_converter_label", "prompt": "Close-up photograph of a rust converter product label on a bottle, showing chemical instructions, workbench background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "frame_crossmember", "prompt": "Underneath photograph of a truck frame crossmember showing surface rust and road grime buildup, flashlight illumination, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "masking_tape_prep", "prompt": "Photograph of blue painters tape masking off areas around bare metal before primer application, clean edges, workshop setting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rust_through_hole", "prompt": "Close-up photograph of a quarter-sized perforation hole rusted through a car floor pan, light visible through the hole from below, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "clean_frame_section", "prompt": "Photograph of a section of truck frame that has been fully cleaned and primed, matte gray finish, contrasting with rusty adjacent area, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "shop_receipt_comparison", "prompt": "Overhead photograph of two receipts side by side on a counter, one showing a high repair quote and one showing DIY supply costs under twenty dollars, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "leaf_spring_rust", "prompt": "Photograph of rusty leaf spring suspension under a truck, showing layered rust between the spring leaves, garage floor visible, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "jack_stand_setup", "prompt": "Photograph of a truck raised on jack stands in a driveway, person visible underneath with a flashlight, afternoon sunlight, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "sanding_disc_used", "prompt": "Photograph of a worn sanding disc next to a fresh one on a workbench, the used one covered in orange rust dust, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "spray_can_collection", "prompt": "Photograph of three spray cans lined up on a workbench: self-etching primer, rubberized undercoating, and clear coat, labels visible, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "finished_underside", "prompt": "Wide photograph of a fully treated and undercoated truck undercarriage, clean black rubberized coating, shop lift, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "safety_glasses_bench", "prompt": "Photograph of safety glasses and a dust mask laid on a workbench next to rust removal tools, safety equipment ready, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "thumbs_up_result", "prompt": "Photograph of a hand giving thumbs up next to a section of cleanly treated bare metal on a truck frame, workshop background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    # Former video concepts — now generated as still images
    {"name": "hand_peeling_rust", "prompt": "Close-up photograph of a hand peeling flaky orange rust scale off a steel frame rail, rust crumbling away, workshop lighting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "brushing_chemical", "prompt": "Close-up photograph of a hand applying pink gel chemical with a small brush onto a rusty metal surface, gel visible on rust, workshop bench, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "wire_brush_scrub", "prompt": "Close-up photograph of a wire brush pressed against rusted metal with rust flakes scattered around, revealing bare steel underneath, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "screwdriver_poke_solid", "prompt": "Extreme close-up photograph of a flathead screwdriver tip pressed against surface rust on a solid metal frame rail, firm contact, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "screwdriver_poke_through", "prompt": "Close-up photograph of a screwdriver pushed through severely rusted perforated metal on a car frame, crumbling rust edges around the hole, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "mechanic_under_lift", "prompt": "Low angle photograph of a mechanic in work clothes pointing at the undercarriage of a truck on a two-post shop lift, clipboard in hand, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "holding_invoice", "prompt": "Close-up photograph of hands holding a printed auto repair invoice, finger pointing at a circled line item, shop counter background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "undercoat_spray", "prompt": "Photograph of a mechanic spraying black rubberized undercoating onto a clean truck undercarriage on a shop lift, spray can in hand, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "flashlight_inspect", "prompt": "First person POV photograph of a hand holding a flashlight shining it along a truck frame rail underside, rusty surface illuminated, garage floor, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "baking_soda_wipe", "prompt": "Close-up photograph of a hand wiping bare metal surface with a rag soaked in baking soda solution, clean workshop background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "primer_spray_action", "prompt": "Close-up photograph of a hand spraying self-etching primer from a spray can onto bare gray metal surface, workshop background, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "drill_wire_wheel", "prompt": "Close-up photograph of a cordless drill with wire wheel attachment pressed against a rusty metal surface, rust dust visible, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "tapping_frame", "prompt": "Close-up photograph of a hand holding a small hammer against a truck frame rail, testing for solid metal, garage setting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "sanding_by_hand", "prompt": "Close-up photograph of a hand sanding a rusty metal surface with sandpaper, rust dust accumulating, workshop bench, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "rust_converter_brush", "prompt": "Close-up photograph of a brush applying dark rust converter liquid onto a rusty surface, the rust turning black on contact, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "hosing_off", "prompt": "Photograph of water from a garden hose rinsing chemical residue from a treated metal surface, water running clear, driveway, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "crawling_under", "prompt": "Wide photograph of a person on a creeper underneath a raised truck on jack stands, flashlight in hand, driveway setting, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
    {"name": "comparing_sections", "prompt": "Photograph showing a rusted section next to a treated section of the same truck frame, dramatic before and after difference, shot on smartphone, slightly soft focus, natural ambient lighting, casual framing"},
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

# Timeline: 75 segments, ~5 min — uses all 50 B-roll images + 6 avatars
# type: "avatar" | "image" (still+KenBurns) | "split" (avatar+image)
TIMELINE = [
    # === CHAPTER 1: Hook / Intro (0:00-1:00) ===
    {"type": "avatar", "avatar": "avatar_intro", "start": 0, "dur": 4},
    {"type": "image", "asset": "rusty_frame_rail", "dur": 4},
    {"type": "split", "avatar": "avatar_intro", "asset": "rusty_rocker_panel", "dur": 4},
    {"type": "image", "asset": "hand_peeling_rust", "dur": 4},
    {"type": "image", "asset": "water_on_rust", "dur": 4},
    {"type": "avatar", "avatar": "avatar_explain", "start": 0, "dur": 4},
    {"type": "image", "asset": "repair_invoice_high", "dur": 4},
    {"type": "image", "asset": "holding_invoice", "dur": 4},
    {"type": "split", "avatar": "avatar_explain", "asset": "mechanic_under_lift", "dur": 4},
    {"type": "avatar", "avatar": "avatar_warning", "start": 0, "dur": 4},
    {"type": "image", "asset": "rust_scale_closeup", "dur": 4},
    {"type": "image", "asset": "brushing_chemical", "dur": 4},
    {"type": "image", "asset": "wheel_well_rust", "dur": 4},
    {"type": "split", "avatar": "avatar_warning", "asset": "chemical_bottle_pink", "dur": 4},
    {"type": "image", "asset": "repair_invoice_low", "dur": 4},
    # === CHAPTER 2: The Problem (1:00-1:40) ===
    {"type": "avatar", "avatar": "avatar_friendly", "start": 0, "dur": 4},
    {"type": "image", "asset": "tools_on_tarp", "dur": 4},
    {"type": "image", "asset": "rubber_gloves_table", "dur": 4},
    {"type": "image", "asset": "four_steps_paper", "dur": 4},
    {"type": "avatar", "avatar": "avatar_pointing", "start": 0, "dur": 4},
    {"type": "image", "asset": "safety_glasses_bench", "dur": 4},
    {"type": "image", "asset": "crawling_under", "dur": 4},
    {"type": "image", "asset": "jack_stand_setup", "dur": 4},
    {"type": "split", "avatar": "avatar_pointing", "asset": "truck_driveway", "dur": 4},
    # === CHAPTER 3: Inspection (1:40-2:24) ===
    {"type": "image", "asset": "flashlight_inspect", "dur": 4},
    {"type": "image", "asset": "flashlight_under_truck", "dur": 4},
    {"type": "split", "avatar": "avatar_explain", "asset": "frame_crossmember", "dur": 4},
    {"type": "image", "asset": "tapping_frame", "dur": 4},
    {"type": "image", "asset": "screwdriver_poke_solid", "dur": 4},
    {"type": "avatar", "avatar": "avatar_explain", "start": 2, "dur": 4},
    {"type": "image", "asset": "screwdriver_poke_through", "dur": 4},
    {"type": "avatar", "avatar": "avatar_warning", "start": 2, "dur": 4},
    {"type": "image", "asset": "paint_bubble_rust", "dur": 4},
    {"type": "image", "asset": "rust_through_hole", "dur": 4},
    {"type": "split", "avatar": "avatar_warning", "asset": "brake_lines_rusty", "dur": 4},
    # === CHAPTER 4: The Bottle / Cheap Fix (2:24-3:08) ===
    {"type": "avatar", "avatar": "avatar_friendly", "start": 2, "dur": 4},
    {"type": "image", "asset": "rust_converter_label", "dur": 4},
    {"type": "image", "asset": "rust_converter_brush", "dur": 4},
    {"type": "image", "asset": "chemical_bottle_pink", "dur": 4},
    {"type": "image", "asset": "brushing_chemical", "dur": 4},
    {"type": "image", "asset": "bare_metal_after", "dur": 4},
    {"type": "split", "avatar": "avatar_friendly", "asset": "before_after_split", "dur": 4},
    {"type": "image", "asset": "shop_receipt_comparison", "dur": 4},
    {"type": "avatar", "avatar": "avatar_explain", "start": 3, "dur": 4},
    {"type": "image", "asset": "wire_brush_scrub", "dur": 4},
    {"type": "split", "avatar": "avatar_explain", "asset": "hand_peeling_rust", "dur": 4},
    # === CHAPTER 5: Making it Hold (3:08-3:52) ===
    {"type": "avatar", "avatar": "avatar_warning", "start": 3, "dur": 4},
    {"type": "image", "asset": "flash_rust_example", "dur": 4},
    {"type": "image", "asset": "baking_soda_wipe", "dur": 4},
    {"type": "image", "asset": "hosing_off", "dur": 4},
    {"type": "avatar", "avatar": "avatar_pointing", "start": 2, "dur": 4},
    {"type": "image", "asset": "masking_tape_prep", "dur": 4},
    {"type": "image", "asset": "primer_spray_action", "dur": 4},
    {"type": "image", "asset": "primer_spray_can", "dur": 4},
    {"type": "split", "avatar": "avatar_pointing", "asset": "sanding_by_hand", "dur": 4},
    {"type": "image", "asset": "sanding_disc_used", "dur": 4},
    {"type": "image", "asset": "drill_wire_wheel", "dur": 4},
    # === CHAPTER 6: Sealing & Protecting (3:52-4:24) ===
    {"type": "avatar", "avatar": "avatar_closing", "start": 0, "dur": 4},
    {"type": "image", "asset": "undercoat_spray", "dur": 4},
    {"type": "image", "asset": "spray_can_collection", "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "comparing_sections", "dur": 4},
    {"type": "image", "asset": "clean_frame_section", "dur": 4},
    {"type": "image", "asset": "finished_underside", "dur": 4},
    {"type": "image", "asset": "undercoat_spray", "dur": 4},
    {"type": "image", "asset": "leaf_spring_rust", "dur": 4},
    # === CHAPTER 7: Closing / Recap (4:24-5:00) ===
    {"type": "avatar", "avatar": "avatar_friendly", "start": 0, "dur": 4},
    {"type": "image", "asset": "before_after_split", "dur": 4},
    {"type": "split", "avatar": "avatar_friendly", "asset": "thumbs_up_result", "dur": 4},
    {"type": "image", "asset": "truck_driveway", "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "bare_metal_after", "dur": 4},
    {"type": "image", "asset": "repair_invoice_low", "dur": 4},
    {"type": "image", "asset": "comparing_sections", "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "finished_underside", "dur": 4},
    {"type": "image", "asset": "shop_receipt_comparison", "dur": 4},
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

        elif seg["type"] == "image":
            image_path = OUT / f"{seg['asset']}.png"
            if not image_path.exists():
                print(f"  [seg_{i:04d}] MISSING image {seg['asset']}, using black")
                _black_frame(seg_dest, dur)
            else:
                _ken_burns(image_path, seg_dest, dur)

        elif seg["type"] == "split":
            avatar_clip = OUT / f"{seg['avatar']}.mp4"
            asset_path = OUT / f"{seg['asset']}.png"
            if not avatar_clip.exists() or not asset_path.exists():
                print(f"  [seg_{i:04d}] MISSING assets for split, using black")
                _black_frame(seg_dest, dur)
            else:
                broll_temp = OUT / f"split_broll_{i:04d}.mp4"
                _ken_burns(asset_path, broll_temp, dur)
                avatar_temp = OUT / f"split_avatar_{i:04d}.mp4"
                start = seg.get("start", 0)
                _trim_clip(avatar_clip, avatar_temp, start, dur)
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
