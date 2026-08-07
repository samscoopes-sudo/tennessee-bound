# Style Presets

Editing-style profiles the video agent's **director LLM** reads to decide *what*
b-roll and graphics to add to a raw avatar video, and *when*. The director emits
an edit decision list (EDL); FFmpeg executes it deterministically.

## Files

- **`default.json`** - the merged reference profile (locked in from two YouTube
  teardowns). This is the house style.

## The style DNA (consistent across both references)

| Trait | Value |
|---|---|
| B-roll dominant | ~70% of runtime |
| Avg shot length | ~2.5s (range 1.5-5s) |
| Transitions | Hard cuts only, no dissolves |
| Motion on stills | Ken Burns push-in, always (105-110%) |
| Primary asset | Real footage -> **Storyblocks first** |
| Continuous subtitles | Off - emphasis text only |
| Lower-thirds | Clean bold white sans-serif |
| Aspect | 16:9 |

## Asset fallback ladder (cost order)

The director tries the cheapest good-enough source first:

1. **Storyblocks** (subscribed) - free marginal cost, ~85% of needs
2. **Web images** - free stills, animated via Ken Burns
3. **Cheap image gen** - custom stills when nothing fits
4. **AI video gen** - last resort, used sparingly

## Tunable knobs

- `energy`: `calm` | `balanced` | `punchy` - shifts b-roll ratio + cut speed
- `split_screen`: allow speaker + reference layouts
- `color_grade`: per-project grade (not baked into base style)

## Derivation

Built from visual-style teardowns of:
- `oaNDqWTaQ6w` - high-energy reference (~80% b-roll, ~2s cuts)
- `F31ug-Q-jCg` - calm/steady reference (~65% b-roll, ~3s cuts)
