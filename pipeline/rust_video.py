#!/usr/bin/env python3
"""5-6 minute rust removal video recreation in the style of Sal Whitaker.

Uses GenAI Pro for image generation + avatar talking head clips.
Voiceover MP3s downloaded separately from vidIQ.
Assembly via ffmpeg with Ken Burns effects, split-screen, and hard cuts.

Usage:
  python rust_video.py --api-key <GENAIPRO_KEY> --gen-images
  python rust_video.py --api-key <GENAIPRO_KEY> --gen-videos
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

# B-roll STILL IMAGES (Ken Burns zoom/pan) — static subjects
BROLL_IMAGES = [
    {"name": "rusty_frame_rail", "prompt": "Close-up photograph of heavy orange flaky rust on a truck frame rail underside, flashlight beam illuminating the rust texture, dark garage background"},
    {"name": "rusty_rocker_panel", "prompt": "Close-up photograph of rust bubbling through paint on a car rocker panel behind the front tire, peeling flakes, natural daylight"},
    {"name": "repair_invoice_high", "prompt": "Overhead photograph of a printed auto repair invoice on a clipboard showing a circled total of $1500, pen beside it, shop counter background"},
    {"name": "repair_invoice_low", "prompt": "Photograph of a small brown chemical bottle next to a $10 bill and loose coins on a workbench, simple clean shot"},
    {"name": "tools_on_tarp", "prompt": "Overhead photograph of rust removal tools laid out on a blue tarp: wire brush, chemical bottle, rubber gloves, old rags, flathead screwdriver, driveway concrete visible"},
    {"name": "flashlight_under_truck", "prompt": "Low angle photograph of a flashlight beam shining on a truck frame rail underside, person lying on their side on a garage floor, warm lighting"},
    {"name": "chemical_bottle_pink", "prompt": "Product-style photograph of a small pink gel rust dissolver bottle on a clean workbench, 8 ounce size, hardware store brand, clear label visible"},
    {"name": "water_on_rust", "prompt": "Extreme close-up macro photograph of water droplets sitting on a rusty orange metal surface, shallow depth of field"},
    {"name": "bare_metal_after", "prompt": "Close-up photograph of clean bare gray metal after rust removal, showing the phosphate conversion coating, smooth surface, workshop lighting"},
    {"name": "primer_spray_can", "prompt": "Photograph of a can of self-etching primer spray paint next to a wire brush and chemical bottle on a garage workbench, ready to use"},
    {"name": "paint_bubble_rust", "prompt": "Close-up photograph of bubbling paint with rust bleeding through on a car body panel, showing where rust formed underneath the paint"},
    {"name": "four_steps_paper", "prompt": "Top-down photograph of lined paper with handwritten numbers 1 through 4 with brief labels next to each, pen beside paper, clean desk"},
    {"name": "truck_driveway", "prompt": "Wide photograph of a pickup truck parked on a residential driveway, person crouching beside it with a flashlight looking at the frame, afternoon light"},
    {"name": "flash_rust_example", "prompt": "Close-up photograph of bare metal surface showing faint orange flash rust forming overnight, microscopic new rust layer on previously clean steel"},
    {"name": "before_after_split", "prompt": "Side by side comparison photograph, left showing heavy orange rust on metal, right showing clean treated bare gray metal, same lighting, workshop bench"},
    {"name": "brake_lines_rusty", "prompt": "Close-up photograph of thin steel brake lines running along a truck frame rail, showing flaky puffed-up rust on the lines, flashlight illumination"},
    {"name": "rust_scale_closeup", "prompt": "Extreme macro photograph of layered rust scale flaking off steel, showing the orange and brown layers of iron oxide, sharp focus, dark background"},
    {"name": "wheel_well_rust", "prompt": "Photograph of a car wheel well with rust eating through the inner fender, visible holes and brown staining, natural daylight"},
    {"name": "rubber_gloves_table", "prompt": "Photograph of yellow rubber gloves laid next to a wire brush and chemical bottle on a garage workbench, ready for rust treatment work"},
    {"name": "rust_converter_label", "prompt": "Close-up photograph of a rust converter product label on a bottle, showing chemical instructions, workbench background"},
    {"name": "vinegar_soak_bolt", "prompt": "Photograph of rusty bolts soaking in a glass jar of white vinegar on a workbench, bubbles forming on the rust surface"},
    {"name": "sanding_disc_used", "prompt": "Photograph of a worn sanding disc next to a fresh one on a workbench, the used one covered in orange rust dust"},
    {"name": "frame_crossmember", "prompt": "Underneath photograph of a truck frame crossmember showing surface rust and road grime buildup, flashlight illumination"},
    {"name": "rust_stain_concrete", "prompt": "Photograph of orange rust stain drips on a concrete garage floor beneath a parked vehicle, overhead view"},
    {"name": "masking_tape_prep", "prompt": "Photograph of blue painters tape masking off areas around bare metal before primer application, clean edges, workshop setting"},
    {"name": "safety_glasses_bench", "prompt": "Photograph of safety glasses and a dust mask laid on a workbench next to rust removal tools, safety equipment ready"},
    {"name": "rust_through_hole", "prompt": "Close-up photograph of a quarter-sized perforation hole rusted through a car floor pan, light visible through the hole from below"},
    {"name": "naval_jelly_applied", "prompt": "Close-up photograph of pink naval jelly chemical paste sitting on a rusty metal surface, partially dissolving the rust, workshop lighting"},
    {"name": "clean_frame_section", "prompt": "Photograph of a section of truck frame that has been fully cleaned and primed, matte gray finish, contrasting with rusty adjacent area"},
    {"name": "shop_receipt_comparison", "prompt": "Overhead photograph of two receipts side by side on a counter, one showing a high repair quote and one showing DIY supply costs under twenty dollars"},
    {"name": "drain_plug_rusty", "prompt": "Close-up photograph of a rusty drain plug on a truck frame, rust buildup around the threads, flashlight beam on it"},
    {"name": "leaf_spring_rust", "prompt": "Photograph of rusty leaf spring suspension under a truck, showing layered rust between the spring leaves, garage floor visible"},
    {"name": "wire_wheel_drill", "prompt": "Photograph of a wire wheel attachment on a cordless drill laying on a workbench, rust dust on the wire bristles"},
    {"name": "exhaust_rust_flakes", "prompt": "Photograph of rusty exhaust pipe with flaking rust falling onto garage floor, heavy corrosion near the muffler connection"},
    {"name": "phosphoric_acid_reaction", "prompt": "Extreme close-up of phosphoric acid rust converter reacting on metal surface, showing the dark gray conversion coating forming"},
    {"name": "truck_bed_rust_spot", "prompt": "Photograph of a small rust spot on a pickup truck bed floor, paint chipping around the edges, overhead view"},
    {"name": "spray_can_collection", "prompt": "Photograph of three spray cans lined up on a workbench: self-etching primer, rubberized undercoating, and clear coat, labels visible"},
    {"name": "jack_stand_setup", "prompt": "Photograph of a truck raised on jack stands in a driveway, person visible underneath with a flashlight, afternoon sunlight"},
    {"name": "rust_dust_pile", "prompt": "Close-up photograph of a small pile of orange rust dust and flakes on a blue tarp after wire brushing, detailed texture"},
    {"name": "caliper_measuring", "prompt": "Photograph of a caliper measuring the thickness of a rusty metal panel, showing how thin the rust has made the steel"},
    {"name": "newspaper_protect", "prompt": "Photograph of newspaper spread on a driveway under a truck to catch rust flakes and chemical drips during treatment"},
    {"name": "finished_underside", "prompt": "Wide photograph of a fully treated and undercoated truck undercarriage, clean black rubberized coating, shop lift"},
    {"name": "thumbs_up_result", "prompt": "Photograph of a hand giving thumbs up next to a section of cleanly treated bare metal on a truck frame, workshop background"},
    {"name": "sunrise_truck_drive", "prompt": "Wide photograph of a pickup truck driving down a rural road at sunrise, golden light, the truck looking clean and well-maintained"},
]

# B-roll VIDEO CLIPS (real motion) — action/hands-on shots
BROLL_VIDEOS = [
    {"name": "vid_hand_peeling_rust", "prompt": "First person POV close-up of a hand slowly peeling flaky orange rust scale off a steel frame rail, rust crumbling away, workshop lighting", "duration": 5},
    {"name": "vid_brushing_chemical", "prompt": "Close-up of a hand applying pink gel chemical with a small brush onto a rusty metal surface, gel bubbling on contact with rust, workshop bench", "duration": 5},
    {"name": "vid_wire_brush_scrub", "prompt": "Close-up of a wire brush scrubbing back and forth on rusted metal, rust flakes flying off revealing shiny bare steel underneath", "duration": 5},
    {"name": "vid_screwdriver_poke_solid", "prompt": "Extreme close-up of a flathead screwdriver tip pressing firmly against surface rust on a solid metal frame rail, metal does not give way, firm tap", "duration": 5},
    {"name": "vid_screwdriver_poke_through", "prompt": "Close-up of a screwdriver pushing through severely rusted perforated metal on a car frame, metal crumbling and breaking apart, dramatic", "duration": 5},
    {"name": "vid_mechanic_under_lift", "prompt": "Low angle shot of a mechanic in work clothes pointing at the undercarriage of a truck on a two-post shop lift, gesturing with clipboard in hand", "duration": 5},
    {"name": "vid_holding_invoice", "prompt": "Close-up of hands holding and reviewing a printed auto repair invoice, finger pointing at a circled line item, shop counter background", "duration": 5},
    {"name": "vid_undercoat_spray", "prompt": "Mechanic spraying black rubberized undercoating onto a clean truck undercarriage on a shop lift, spray mist visible, steady sweeping motion", "duration": 5},
    {"name": "vid_flashlight_inspect", "prompt": "First person POV of a hand holding a flashlight shining it along a truck frame rail underside, slowly panning across rusty surface, garage floor", "duration": 5},
    {"name": "vid_baking_soda_wipe", "prompt": "Close-up of a hand wiping bare metal surface with a rag soaked in baking soda solution, neutralizing chemical residue, clean workshop", "duration": 5},
    {"name": "vid_primer_spray", "prompt": "Close-up of a hand spraying self-etching primer from a spray can onto bare gray metal surface, even sweeping coat, workshop background", "duration": 5},
    {"name": "vid_drill_wire_wheel", "prompt": "Close-up of a cordless drill with wire wheel attachment spinning and removing rust from a metal surface, sparks and rust dust flying", "duration": 5},
    {"name": "vid_pouring_vinegar", "prompt": "Close-up of hands pouring white vinegar from a bottle into a glass jar containing rusty bolts, liquid splashing over rusted metal", "duration": 5},
    {"name": "vid_tapping_frame", "prompt": "Close-up of a hand tapping along a truck frame rail with a small hammer, listening for solid vs hollow sounds, garage setting", "duration": 5},
    {"name": "vid_peeling_masking", "prompt": "Close-up of hands peeling blue painters tape off a freshly primed metal surface, revealing clean sharp edges, satisfying peel", "duration": 5},
    {"name": "vid_sanding_by_hand", "prompt": "Close-up of a hand sanding a rusty metal surface with sandpaper, back and forth motion, rust dust accumulating, workshop bench", "duration": 5},
    {"name": "vid_rust_converter_brush", "prompt": "Close-up of a brush applying dark rust converter liquid onto a rusty surface, the liquid turning the rust black on contact", "duration": 5},
    {"name": "vid_hosing_off", "prompt": "Close-up of water from a garden hose rinsing off chemical residue from a treated metal surface, water running clear, driveway", "duration": 5},
    {"name": "vid_crawling_under", "prompt": "Wide shot of a person sliding on a creeper underneath a raised truck on jack stands, flashlight in hand, driveway setting", "duration": 5},
    {"name": "vid_shaking_spray_can", "prompt": "Close-up of a hand shaking a spray can of primer, the ball bearing rattling inside audibly, then popping the cap off, workshop", "duration": 5},
    {"name": "vid_rubbing_bare_metal", "prompt": "Close-up of fingers rubbing across clean bare metal surface after rust removal, showing the smooth phosphate coating, satisfied gesture", "duration": 5},
    {"name": "vid_undercoat_drip", "prompt": "Close-up of black rubberized undercoating being sprayed in thick coat on a frame rail, slight drip forming and being smoothed out", "duration": 5},
    {"name": "vid_comparing_sections", "prompt": "Camera panning slowly between a rusted section and a treated section of the same truck frame, showing the dramatic before and after difference", "duration": 5},
    {"name": "vid_tools_cleanup", "prompt": "Hands gathering wire brush, chemical bottle, and rags from a blue tarp, tidying up after completing the rust treatment job", "duration": 5},
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

# Timeline segments — ~120 cuts over 8 minutes
# type: "avatar" | "image" (still+KenBurns) | "video" (motion clip) | "split"
# "image" refs BROLL_IMAGES name, "video" refs BROLL_VIDEOS name
TIMELINE = [
    # === CHAPTER 1: Hook / Intro (0:00-1:00) ===
    {"type": "avatar", "avatar": "avatar_intro", "start": 0, "dur": 4},
    {"type": "image", "asset": "rusty_frame_rail", "dur": 3},
    {"type": "split", "avatar": "avatar_intro", "asset": "rusty_rocker_panel", "asset_type": "image", "dur": 3},
    {"type": "video", "asset": "vid_hand_peeling_rust", "dur": 3},
    {"type": "image", "asset": "water_on_rust", "dur": 3},
    {"type": "avatar", "avatar": "avatar_explain", "start": 0, "dur": 3},
    {"type": "image", "asset": "repair_invoice_high", "dur": 3},
    {"type": "video", "asset": "vid_holding_invoice", "dur": 3},
    {"type": "split", "avatar": "avatar_explain", "asset": "vid_mechanic_under_lift", "asset_type": "video", "dur": 3},
    {"type": "avatar", "avatar": "avatar_warning", "start": 0, "dur": 3},
    {"type": "image", "asset": "rust_scale_closeup", "dur": 3},
    {"type": "video", "asset": "vid_brushing_chemical", "dur": 3},
    {"type": "image", "asset": "wheel_well_rust", "dur": 3},
    {"type": "split", "avatar": "avatar_warning", "asset": "chemical_bottle_pink", "asset_type": "image", "dur": 3},
    {"type": "image", "asset": "repair_invoice_low", "dur": 3},
    {"type": "avatar", "avatar": "avatar_friendly", "start": 0, "dur": 3},
    {"type": "image", "asset": "tools_on_tarp", "dur": 3},
    {"type": "image", "asset": "four_steps_paper", "dur": 3},
    {"type": "avatar", "avatar": "avatar_pointing", "start": 0, "dur": 3},
    {"type": "image", "asset": "rubber_gloves_table", "dur": 3},
    # === CHAPTER 2: Inspection (1:00-2:00) ===
    {"type": "image", "asset": "truck_driveway", "dur": 4},
    {"type": "video", "asset": "vid_flashlight_inspect", "dur": 3},
    {"type": "image", "asset": "flashlight_under_truck", "dur": 3},
    {"type": "split", "avatar": "avatar_explain", "asset": "rusty_frame_rail", "asset_type": "image", "dur": 3},
    {"type": "video", "asset": "vid_tapping_frame", "dur": 4},
    {"type": "video", "asset": "vid_screwdriver_poke_solid", "dur": 4},
    {"type": "avatar", "avatar": "avatar_explain", "start": 2, "dur": 3},
    {"type": "video", "asset": "vid_screwdriver_poke_through", "dur": 4},
    {"type": "avatar", "avatar": "avatar_warning", "start": 2, "dur": 3},
    {"type": "image", "asset": "paint_bubble_rust", "dur": 3},
    {"type": "image", "asset": "rust_through_hole", "dur": 3},
    {"type": "split", "avatar": "avatar_warning", "asset": "brake_lines_rusty", "asset_type": "image", "dur": 4},
    {"type": "image", "asset": "frame_crossmember", "dur": 3},
    {"type": "video", "asset": "vid_crawling_under", "dur": 3},
    {"type": "image", "asset": "jack_stand_setup", "dur": 3},
    {"type": "image", "asset": "leaf_spring_rust", "dur": 3},
    # === CHAPTER 3: The Bottle / Cheap Fix (2:00-3:00) ===
    {"type": "avatar", "avatar": "avatar_friendly", "start": 2, "dur": 3},
    {"type": "image", "asset": "chemical_bottle_pink", "dur": 4},
    {"type": "image", "asset": "rust_converter_label", "dur": 3},
    {"type": "video", "asset": "vid_brushing_chemical", "start": 2, "dur": 3},
    {"type": "image", "asset": "naval_jelly_applied", "dur": 3},
    {"type": "video", "asset": "vid_rust_converter_brush", "dur": 4},
    {"type": "image", "asset": "bare_metal_after", "dur": 4},
    {"type": "split", "avatar": "avatar_friendly", "asset": "before_after_split", "asset_type": "image", "dur": 3},
    {"type": "image", "asset": "repair_invoice_high", "dur": 3},
    {"type": "image", "asset": "shop_receipt_comparison", "dur": 4},
    {"type": "avatar", "avatar": "avatar_explain", "start": 3, "dur": 3},
    {"type": "image", "asset": "repair_invoice_low", "dur": 3},
    {"type": "video", "asset": "vid_wire_brush_scrub", "dur": 3},
    {"type": "split", "avatar": "avatar_explain", "asset": "vid_hand_peeling_rust", "asset_type": "video", "dur": 3},
    {"type": "image", "asset": "vinegar_soak_bolt", "dur": 3},
    # === CHAPTER 4: Making it Hold (3:00-4:00) ===
    {"type": "avatar", "avatar": "avatar_warning", "start": 3, "dur": 3},
    {"type": "image", "asset": "flash_rust_example", "dur": 3},
    {"type": "video", "asset": "vid_baking_soda_wipe", "dur": 4},
    {"type": "image", "asset": "phosphoric_acid_reaction", "dur": 3},
    {"type": "video", "asset": "vid_hosing_off", "dur": 4},
    {"type": "avatar", "avatar": "avatar_pointing", "start": 2, "dur": 3},
    {"type": "video", "asset": "vid_primer_spray", "dur": 3},
    {"type": "image", "asset": "primer_spray_can", "dur": 3},
    {"type": "split", "avatar": "avatar_pointing", "asset": "bare_metal_after", "asset_type": "image", "dur": 4},
    {"type": "video", "asset": "vid_shaking_spray_can", "dur": 3},
    {"type": "image", "asset": "masking_tape_prep", "dur": 3},
    {"type": "video", "asset": "vid_peeling_masking", "dur": 3},
    {"type": "image", "asset": "before_after_split", "dur": 3},
    {"type": "avatar", "avatar": "avatar_closing", "start": 0, "dur": 4},
    {"type": "image", "asset": "truck_driveway", "dur": 4},
    # === CHAPTER 5: Step by Step Process (4:00-5:00) ===
    {"type": "avatar", "avatar": "avatar_explain", "start": 0, "dur": 4},
    {"type": "video", "asset": "vid_flashlight_inspect", "start": 2, "dur": 4},
    {"type": "image", "asset": "rusty_rocker_panel", "dur": 3},
    {"type": "video", "asset": "vid_sanding_by_hand", "dur": 4},
    {"type": "image", "asset": "sanding_disc_used", "dur": 3},
    {"type": "video", "asset": "vid_drill_wire_wheel", "dur": 4},
    {"type": "split", "avatar": "avatar_explain", "asset": "vid_wire_brush_scrub", "asset_type": "video", "dur": 4},
    {"type": "image", "asset": "rust_dust_pile", "dur": 3},
    {"type": "video", "asset": "vid_rust_converter_brush", "start": 2, "dur": 4},
    {"type": "avatar", "avatar": "avatar_friendly", "start": 0, "dur": 3},
    {"type": "image", "asset": "water_on_rust", "dur": 3},
    {"type": "video", "asset": "vid_baking_soda_wipe", "start": 2, "dur": 4},
    {"type": "image", "asset": "safety_glasses_bench", "dur": 3},
    {"type": "split", "avatar": "avatar_friendly", "asset": "vid_brushing_chemical", "asset_type": "video", "dur": 4},
    {"type": "image", "asset": "newspaper_protect", "dur": 3},
    {"type": "image", "asset": "rust_stain_concrete", "dur": 3},
    # === CHAPTER 6: Sealing & Protecting (5:00-6:00) ===
    {"type": "avatar", "avatar": "avatar_pointing", "start": 0, "dur": 4},
    {"type": "video", "asset": "vid_primer_spray", "start": 2, "dur": 4},
    {"type": "image", "asset": "spray_can_collection", "dur": 3},
    {"type": "video", "asset": "vid_undercoat_spray", "dur": 4},
    {"type": "split", "avatar": "avatar_pointing", "asset": "vid_undercoat_drip", "asset_type": "video", "dur": 4},
    {"type": "image", "asset": "clean_frame_section", "dur": 4},
    {"type": "video", "asset": "vid_rubbing_bare_metal", "dur": 3},
    {"type": "avatar", "avatar": "avatar_explain", "start": 2, "dur": 4},
    {"type": "video", "asset": "vid_undercoat_spray", "start": 2, "dur": 4},
    {"type": "image", "asset": "bare_metal_after", "dur": 3},
    {"type": "split", "avatar": "avatar_explain", "asset": "before_after_split", "asset_type": "image", "dur": 4},
    {"type": "video", "asset": "vid_comparing_sections", "dur": 4},
    {"type": "image", "asset": "finished_underside", "dur": 4},
    # === CHAPTER 7: When to Walk Away (6:00-7:00) ===
    {"type": "avatar", "avatar": "avatar_warning", "start": 0, "dur": 4},
    {"type": "video", "asset": "vid_screwdriver_poke_through", "start": 2, "dur": 4},
    {"type": "image", "asset": "brake_lines_rusty", "dur": 3},
    {"type": "image", "asset": "rust_through_hole", "dur": 4},
    {"type": "split", "avatar": "avatar_warning", "asset": "vid_mechanic_under_lift", "asset_type": "video", "dur": 4},
    {"type": "image", "asset": "exhaust_rust_flakes", "dur": 3},
    {"type": "video", "asset": "vid_tapping_frame", "start": 2, "dur": 4},
    {"type": "image", "asset": "caliper_measuring", "dur": 3},
    {"type": "avatar", "avatar": "avatar_explain", "start": 3, "dur": 4},
    {"type": "image", "asset": "drain_plug_rusty", "dur": 3},
    {"type": "video", "asset": "vid_mechanic_under_lift", "start": 2, "dur": 4},
    {"type": "split", "avatar": "avatar_explain", "asset": "repair_invoice_high", "asset_type": "image", "dur": 4},
    {"type": "image", "asset": "truck_bed_rust_spot", "dur": 3},
    {"type": "image", "asset": "paint_bubble_rust", "dur": 3},
    # === CHAPTER 8: Closing / Recap (7:00-8:00) ===
    {"type": "avatar", "avatar": "avatar_friendly", "start": 2, "dur": 4},
    {"type": "image", "asset": "tools_on_tarp", "dur": 3},
    {"type": "video", "asset": "vid_pouring_vinegar", "dur": 4},
    {"type": "image", "asset": "chemical_bottle_pink", "dur": 3},
    {"type": "image", "asset": "shop_receipt_comparison", "dur": 4},
    {"type": "split", "avatar": "avatar_friendly", "asset": "truck_driveway", "asset_type": "image", "dur": 4},
    {"type": "video", "asset": "vid_tools_cleanup", "dur": 4},
    {"type": "image", "asset": "thumbs_up_result", "dur": 3},
    {"type": "avatar", "avatar": "avatar_closing", "start": 0, "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "finished_underside", "asset_type": "image", "dur": 4},
    {"type": "image", "asset": "before_after_split", "dur": 4},
    {"type": "image", "asset": "sunrise_truck_drive", "dur": 4},
    {"type": "avatar", "avatar": "avatar_closing", "start": 2, "dur": 4},
    # === Extended Closing / Final thoughts (7:57-8:00+) ===
    {"type": "image", "asset": "wire_wheel_drill", "dur": 4},
    {"type": "video", "asset": "vid_comparing_sections", "start": 2, "dur": 4},
    {"type": "image", "asset": "clean_frame_section", "dur": 4},
    {"type": "split", "avatar": "avatar_friendly", "asset": "vid_rubbing_bare_metal", "asset_type": "video", "dur": 4},
    {"type": "image", "asset": "leaf_spring_rust", "dur": 4},
    {"type": "video", "asset": "vid_hosing_off", "start": 2, "dur": 4},
    {"type": "image", "asset": "vinegar_soak_bolt", "dur": 4},
    {"type": "avatar", "avatar": "avatar_pointing", "start": 2, "dur": 4},
    {"type": "image", "asset": "phosphoric_acid_reaction", "dur": 4},
    {"type": "video", "asset": "vid_drill_wire_wheel", "start": 2, "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "thumbs_up_result", "asset_type": "image", "dur": 4},
    {"type": "image", "asset": "finished_underside", "dur": 4},
    {"type": "video", "asset": "vid_tools_cleanup", "start": 2, "dur": 4},
    {"type": "image", "asset": "sunrise_truck_drive", "dur": 4},
    {"type": "split", "avatar": "avatar_closing", "asset": "before_after_split", "asset_type": "image", "dur": 4},
    {"type": "avatar", "avatar": "avatar_closing", "start": 0, "dur": 5},
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


def gen_videos(veo: Veo):
    """Generate all B-roll video clips via GenAI Pro text-to-video."""
    print(f"Generating {len(BROLL_VIDEOS)} B-roll video clips...")
    for vid in BROLL_VIDEOS:
        dest = OUT / f"{vid['name']}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [{vid['name']}] skip (cached)")
            continue
        print(f"  [{vid['name']}] generating...")
        try:
            veo.text_to_video(vid["prompt"], dest, duration=vid["duration"])
            print(f"  [{vid['name']}] OK")
        except Exception as e:
            print(f"  [{vid['name']}] FAILED: {e}")


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

        elif seg["type"] == "video":
            video_path = OUT / f"{seg['asset']}.mp4"
            if not video_path.exists():
                print(f"  [seg_{i:04d}] MISSING video {seg['asset']}, using black")
                _black_frame(seg_dest, dur)
            else:
                start = seg.get("start", 0)
                _trim_clip(video_path, seg_dest, start, dur)
                scaled = OUT / f"seg_{i:04d}_scaled.mp4"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(seg_dest),
                    "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-an", str(scaled)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                scaled.replace(seg_dest)

        elif seg["type"] == "split":
            avatar_clip = OUT / f"{seg['avatar']}.mp4"
            asset_type = seg.get("asset_type", "image")
            if asset_type == "image":
                asset_path = OUT / f"{seg['asset']}.png"
            else:
                asset_path = OUT / f"{seg['asset']}.mp4"
            if not avatar_clip.exists() or not asset_path.exists():
                print(f"  [seg_{i:04d}] MISSING assets for split, using black")
                _black_frame(seg_dest, dur)
            else:
                broll_temp = OUT / f"split_broll_{i:04d}.mp4"
                if asset_type == "image":
                    _ken_burns(asset_path, broll_temp, dur)
                else:
                    bstart = seg.get("start", 0)
                    _trim_clip(asset_path, broll_temp, bstart, dur)
                    scaled_b = OUT / f"split_broll_{i:04d}_s.mp4"
                    subprocess.run([
                        "ffmpeg", "-y", "-i", str(broll_temp),
                        "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-an", str(scaled_b)
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    scaled_b.replace(broll_temp)
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
    ap.add_argument("--gen-videos", action="store_true", help="Generate B-roll video clips")
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

    if args.gen_videos:
        print(f"\n=== GENERATING {len(BROLL_VIDEOS)} B-ROLL VIDEO CLIPS ===")
        gen_videos(veo)

    if args.gen_avatar:
        print(f"\n=== GENERATING {len(AVATAR_CLIPS)} AVATAR CLIPS ===")
        gen_avatar_clips(veo)

    if not args.gen_images and not args.gen_videos and not args.gen_avatar and not args.gen_avatar_image:
        print("\nSpecify --gen-images, --gen-videos, --gen-avatar-image, --gen-avatar, or --assemble-only")

    total_dur = sum(s["dur"] for s in TIMELINE)
    print(f"\nTimeline: {len(TIMELINE)} segments, ~{total_dur}s ({total_dur/60:.1f} min)")
    print(f"B-roll images needed: {len(BROLL_IMAGES)}")
    print(f"B-roll videos needed: {len(BROLL_VIDEOS)}")
    print(f"Avatar clips needed: {len(AVATAR_CLIPS)}")


if __name__ == "__main__":
    main()
