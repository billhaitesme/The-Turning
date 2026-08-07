# OMEGA-ARC app icon

The mark: a **red broken ring** (`#F05252`, the Bridge Zero "failure" red) that reads
as both an **Ω** and an **arc**, with the machine identity **`0M3-G4`** spelled in
genuine **Aurebesh** (amber `#F2AD40`, the "warning" tone) under an **extreme fisheye** —
the center glyphs are magnified and stretched tall, the ends compressed toward the rim,
so the word forms a lens that fills the ring. Background and palette match the operator
consoles (`bridge-zero-ios/Sources/Theme.swift`): the `#071016` void, `#24333C` hairline.

The Aurebesh is real, not decorative ASCII — rendered from the bundled font's actual
glyph outlines. It keeps the Star Wars nod that runs through Bridge Zero (see the
desktop Aurebesh Utility).

## Files

- `omega-arc-icon.svg` — the master (rounded, with glow). Source of truth for previews.
- `tools/generate_icons.py` — regenerates every platform asset from the font. Deterministic.

### Generated into the apps (do not hand-edit — re-run the generator)

- **iOS:** `bridge-zero-ios/Sources/Assets.xcassets/AppIcon.appiconset/` — a single
  full-bleed 1024×1024 PNG, **alpha stripped** (the App Store rejects icons with an alpha
  channel). iOS applies its own squircle mask.
- **Android:** an adaptive icon (`minSdk 26`) —
  `res/mipmap-anydpi-v26/ic_launcher{,_round}.xml`, a gradient
  `res/drawable/ic_launcher_background.xml`, and glowing foreground bitmaps in
  `res/mipmap-*/ic_launcher_foreground.png` (all densities). The foreground is scaled to
  the adaptive safe zone so no launcher mask clips the ring.

## Regenerating

```bash
pip install fonttools resvg-py pillow
python bridge/shared/icon/tools/generate_icons.py
```

To adjust the look, edit the constants at the top of `generate_icons.py` (`FMIN`,
`POWER`, `VSTRETCH` control the fisheye; `RING_C` / `WORD_C` the colors) and re-run.

## Licensing

The glyphs come from **SilvinoR's Aurebesh font**, SIL Open Font License 1.1 — see
[`../fonts/LICENSE.md`](../fonts/LICENSE.md). OFL permits redistribution (including in
this public repo) and use in derived artwork; the icon uses the font unmodified. Aurebesh
is a *Star Wars*–associated alphabet; this is a fan nod, not an official mark.
