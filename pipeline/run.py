#!/usr/bin/env python3
"""Director pipeline CLI. Stages: voice -> plan -> (align) -> generate -> assemble.

Two ways to run each stage:
  * Channel mode (recommended): --channel <name> [--run <slug>]
      niche/persona/scene, avatar, cloned voice, planner model and all paths come
      from the channel config; each video is a "run" under channels/<name>/runs/<slug>/.
  * Legacy mode: pass explicit --script/--shots/--out/--avatar/--vo as before.
"""
import argparse
from pathlib import Path

from director import align as al
from director import assemble as asm
from director import channels as ch
from director import generate as gen
from director import plan as pl
from director import stockedit as se
from director import tts as tts_mod


def _run_dir(channel: "ch.Channel", args, *, for_new: bool) -> Path:
    """Resolve the working dir for this video job within a channel."""
    if getattr(args, "run", None):
        return channel.run_dir(args.run)
    if for_new:                                  # voice/plan: derive a slug from topic/script
        slug = getattr(args, "topic", "") or Path(getattr(args, "script")).stem
        return channel.run_dir(slug)
    latest = channel.latest_run()                # later stages continue the most recent run
    if latest is None:
        raise SystemExit(f"channel '{channel.name}' has no runs yet — run `voice`/`plan` first (or pass --run)")
    return latest


def _resolve_vo(args, rd: Path | None) -> Path:
    if getattr(args, "vo", None):
        return Path(args.vo)
    if rd is not None and (rd / "vo.wav").exists():
        return rd / "vo.wav"
    raise SystemExit("no voiceover found — pass --vo, or run `voice` first to generate it")


def _add_channel_args(sp) -> None:
    sp.add_argument("--channel", help="channel name under channels/ (enables channel mode)")
    sp.add_argument("--run", help="run slug (default: derive from topic/script; latest on later stages)")


def main() -> None:
    ap = argparse.ArgumentParser(description="script + voiceover -> generated video")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("channels", help="list configured channels")

    v = sub.add_parser("voice", help="script -> cloned-voice VO (F5-TTS on pod, or ElevenLabs)")
    _add_channel_args(v)
    v.add_argument("--script", required=True)
    v.add_argument("--comfy", help="ComfyUI base URL (required only for the F5-TTS engine)")
    v.add_argument("--seed", type=int, default=1)

    sc = sub.add_parser("script", help="topic -> narration-ready script (Claude)")
    _add_channel_args(sc)
    sc.add_argument("--topic", help="topic/title (default: next approved topic in the backlog)")
    sc.add_argument("--minutes", type=int, default=19, help="target spoken length (minutes)")

    tp = sub.add_parser("topics", help="list or approve the channel's topic backlog")
    _add_channel_args(tp)
    tp.add_argument("--approve", action="store_true", help="approve all pending topics")

    p = sub.add_parser("plan", help="script -> shot-list.json (Claude)")
    _add_channel_args(p)
    p.add_argument("--script", required=True)
    p.add_argument("--vo", help="voiceover file (defaults to the run's vo.wav in channel mode)")
    p.add_argument("--topic", default="", help="short video topic; inferred from filename if omitted")
    p.add_argument("--out", default="shot-list.json", help="(legacy mode only)")

    al_p = sub.add_parser("align", help="re-time shot-list to the real VO audio (word timestamps)")
    _add_channel_args(al_p)
    al_p.add_argument("--shots", default="shot-list.json", help="(legacy mode only)")
    al_p.add_argument("--vo", help="voiceover file (defaults to the run's vo.wav in channel mode)")
    al_p.add_argument("--model", default="small", help="faster-whisper model size (base/small/medium)")

    g = sub.add_parser("generate", help="shot-list.json -> assets via ComfyUI")
    _add_channel_args(g)
    g.add_argument("--shots", default="shot-list.json", help="(legacy mode only)")
    g.add_argument("--comfy", required=True, help="ComfyUI base URL, e.g. https://<pod>-8188.proxy.runpod.net")
    g.add_argument("--avatar", default="../assets/avatar.png", help="(legacy mode only; channel supplies its own)")
    g.add_argument("--limit", type=int, default=None, help="only generate N shots (testing)")
    g.add_argument("--start", type=int, default=0, help="skip shots before this index (resume/target)")
    g.add_argument("--force", action="store_true", help="regenerate even shots that already have an asset")
    g.add_argument("--stock", action="store_true", help="opt in to stock footage; default is AI-only")
    g.add_argument("--only", choices=["broll", "avatar"], help="render only b-roll, or only avatar shots "
                   "(keeps InfiniteTalk out of VRAM during the b-roll pass)")
    g.add_argument("--google", action="store_true", help="use Google Images for b-roll stills instead of FLUX")

    se_p = sub.add_parser("stock-edit", help="shot-list -> Pexels stock clips -> assemble (no GPU)")
    _add_channel_args(se_p)
    se_p.add_argument("--shots", default="shot-list.json", help="(legacy mode only)")
    se_p.add_argument("--vo", help="voiceover file (defaults to the run's vo.wav)")
    se_p.add_argument("--out", default="output/video.mp4", help="(legacy mode only)")
    se_p.add_argument("--limit", type=int, default=None, help="only fetch N clips (testing)")
    se_p.add_argument("--start", type=int, default=0, help="skip shots before this index")
    se_p.add_argument("--force", action="store_true", help="re-download even if clip exists")
    se_p.add_argument("--fetch-only", action="store_true", help="download clips but don't assemble")
    se_p.add_argument("--pexels-key", default=None, help="Pexels API key (or set PEXELS_API_KEY)")
    se_p.add_argument("--google-api-key", default=None, help="Google CSE API key (or GOOGLE_API_KEY)")
    se_p.add_argument("--google-cse-id", default=None, help="Google CSE ID (or GOOGLE_CSE_ID)")
    se_p.add_argument("--photos-only", action="store_true", help="Pexels photos only (no video/Wikimedia/Google)")

    a = sub.add_parser("assemble", help="assets + VO -> video.mp4")
    _add_channel_args(a)
    a.add_argument("--shots", default="shot-list.json", help="(legacy mode only)")
    a.add_argument("--vo", help="voiceover file (defaults to the run's vo.wav in channel mode)")
    a.add_argument("--out", default="output/rough_cut.mp4", help="(legacy mode only)")

    args = ap.parse_args()

    if args.cmd == "channels":
        names = ch.list_channels()
        print("\n".join(names) if names else "(no channels — create channels/<name>/channel.json)")
        return

    channel = ch.load(args.channel) if getattr(args, "channel", None) else None

    if args.cmd == "voice":
        if not channel:
            raise SystemExit("voice requires --channel (uses the channel's cloned narrator)")
        rd = _run_dir(channel, args, for_new=True)
        vc = channel.voice or {}
        engine = vc.get("engine", "f5tts")
        if engine == "elevenlabs":
            from director import eleven as el
            el.synthesize(Path(args.script), rd / "vo.wav", rd / "voice_parts",
                          voice_id=vc.get("voice_id", ""),
                          model_id=vc.get("model_id", "eleven_multilingual_v2"),
                          stability=float(vc.get("stability", 0.5)),
                          similarity_boost=float(vc.get("similarity_boost", 0.85)),
                          style=float(vc.get("style", 0.0)),
                          use_speaker_boost=bool(vc.get("use_speaker_boost", True)))
        else:
            if not args.comfy:
                raise SystemExit("the f5tts engine needs --comfy <ComfyUI URL>")
            ref_audio = channel.dir / vc.get("ref_audio", "voice/ref.wav")
            ref_text = vc.get("ref_text")
            if not ref_text:
                rtf = channel.dir / vc.get("ref_text_file", "voice/ref.txt")
                ref_text = rtf.read_text(encoding="utf-8").strip() if rtf.exists() else ""
            tts_mod.synthesize(args.comfy, Path(args.script), ref_audio, ref_text,
                               rd / "vo.wav", rd / "voice_parts",
                               seed=int(vc.get("seed", args.seed)), speed=float(vc.get("speed", 1.0)))
        print(f"[{channel.name}] VO -> {rd / 'vo.wav'}")

    elif args.cmd == "topics":
        if not channel:
            raise SystemExit("topics requires --channel")
        from director import topics as tp_mod
        data = tp_mod.load(channel.dir)
        if args.approve:
            n = tp_mod.approve_pending(data)
            tp_mod.save(data, channel.dir)
            print(f"approved {n} pending topic(s)")
        print(f"[{channel.name}] backlog {tp_mod.counts(data)}")
        for t in data["topics"]:
            print(f"  [{t['status']:>9}] {t['title']}")

    elif args.cmd == "script":
        if not channel:
            raise SystemExit("script requires --channel")
        from director import script as scr_mod
        from director import topics as tp_mod
        data = tp_mod.load(channel.dir)
        topic = args.topic
        if not topic:
            nt = tp_mod.next_approved(data)
            if not nt:
                raise SystemExit("no approved topic in backlog — run `topics --approve` or pass --topic")
            topic = nt["title"]
        args.topic = topic
        rd = _run_dir(channel, args, for_new=True)
        scr_mod.write_script(topic, rd / "script.txt", niche=channel.niche,
                             persona=channel.narrator_persona, minutes=args.minutes,
                             script_notes=channel.script_notes)
        tp_mod.set_status(data, topic, "produced")
        tp_mod.save(data, channel.dir)
        print(f"[{channel.name}] script -> {rd / 'script.txt'}  (topic marked produced)")

    elif args.cmd == "plan":
        topic = args.topic or Path(args.script).stem.replace("-", " ")
        if channel:
            rd = _run_dir(channel, args, for_new=True)
            plan = pl.build_plan(Path(args.script), _resolve_vo(args, rd), topic,
                                 niche=channel.niche, persona=channel.narrator_persona,
                                 scene_style=channel.scene_style, planner_model=channel.planner_model)
            pl.write_plan(plan, rd / "shot-list.json")
            print(f"[{channel.name}] run dir: {rd}")
        else:
            plan = pl.build_plan(Path(args.script), _resolve_vo(args, None), topic)
            pl.write_plan(plan, Path(args.out))

    elif args.cmd == "align":
        rd = _run_dir(channel, args, for_new=False) if channel else None
        shots = (rd / "shot-list.json") if channel else Path(args.shots)
        al.align_shotlist(shots, _resolve_vo(args, rd), args.model)

    elif args.cmd == "generate":
        if channel:
            rd = _run_dir(channel, args, for_new=False)
            gen.generate(rd / "shot-list.json", args.comfy, channel.avatar,
                         args.limit, args.start, args.force, use_stock=args.stock,
                         out_dir=rd / "output", only=args.only,
                         avatars=channel.avatars, style=channel.style_suffix,
                         th_prompt=channel.talking_head_prompt,
                         broll_w=channel.broll_w, broll_h=channel.broll_h,
                         use_google=args.google)
        else:
            gen.generate(Path(args.shots), args.comfy, Path(args.avatar), args.limit,
                         args.start, args.force, use_stock=args.stock)

    elif args.cmd == "stock-edit":
        import os
        api_key = args.pexels_key or os.environ.get("PEXELS_API_KEY")
        if not api_key:
            raise SystemExit("need --pexels-key or PEXELS_API_KEY env var")
        if channel:
            rd = _run_dir(channel, args, for_new=False)
            shots = rd / "shot-list.json"
            out_dir = rd / "output"
        else:
            shots = Path(args.shots)
            out_dir = shots.parent / "output"
        g_key = args.google_api_key or os.environ.get("GOOGLE_API_KEY")
        g_cse = args.google_cse_id or os.environ.get("GOOGLE_CSE_ID")
        se.fetch_stock(shots, api_key, out_dir, args.limit, args.start, args.force,
                       google_api_key=g_key, google_cse_id=g_cse,
                       photos_only=args.photos_only)
        if not args.fetch_only:
            vo = _resolve_vo(args, rd if channel else None)
            out = (rd / "output" / "video.mp4") if channel else Path(args.out)
            asm.assemble(shots, vo, out)

    elif args.cmd == "assemble":
        if channel:
            rd = _run_dir(channel, args, for_new=False)
            asm.assemble(rd / "shot-list.json", _resolve_vo(args, rd), rd / "output" / "video.mp4")
        else:
            asm.assemble(Path(args.shots), _resolve_vo(args, None), Path(args.out))


if __name__ == "__main__":
    main()
