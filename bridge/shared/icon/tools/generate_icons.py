#!/usr/bin/env python3
"""Regenerate the OMEGA-ARC app icon for every surface from the OFL Aurebesh font.

Deterministic: font glyph outlines -> fisheye layout -> SVG -> platform assets.
Re-running with the same inputs reproduces byte-stable SVGs and equivalent PNGs.

Deps (host tools, not app deps):  pip install fonttools resvg-py pillow
Run:                              python generate_icons.py

Design: a red (#F05252, UI "failure") broken ring that reads as both an Omega and
an arc, with the machine identity "0M3-G4" spelled in genuine Aurebesh (amber
#F2AD40, UI "warning") under an extreme fisheye — center glyphs magnified and
vertically stretched, ends compressed toward the rim. Palette matches Bridge Zero
(Theme.swift). Aurebesh font: SilvinoR, OFL-1.1 (see ../../fonts/LICENSE.md).
"""
import json, math, os, io
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import resvg_py
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FONT = os.path.join(REPO, "bridge", "shared", "fonts", "AurebeshNL.ttf")

CX = CY = 512.0
CAP = 655.0; VC = CAP / 2; R_IN = 344.0
RING_C = "#F05252"; WORD_C = "#F2AD40"; HALO_C = "#F2AD40"
NAME = "0M3-G4"
RING_R = 372; RING_W = 30
# FE3 "extreme fisheye" parameters
FMIN, POWER, VSTRETCH, GAP, HYPHEN_F = 0.22, 0.68, 1.25, 2.0, 0.5
FG_SCALE = 0.80   # shrink ring+text into the Android adaptive safe zone

# ---- glyph outlines from the font ----
def extract():
    font = TTFont(FONT)
    upm = font["head"].unitsPerEm
    gs = font.getGlyphSet(); cmap = font.getBestCmap(); hmtx = font["hmtx"]
    glyphs, x = [], 0
    for ch in NAME:
        gname = cmap.get(ord(ch))
        pen = SVGPathPen(gs); gs[gname].draw(pen)
        glyphs.append({"d": pen.getCommands(), "x": x, "adv": hmtx[gname][0]})
        x += hmtx[gname][0]
    return glyphs, x, upm

GLYPHS, TOTAL_ADV, UPM = extract()

def arc_path(r, a0, a1):
    def pt(a):
        rad = math.radians(a); return CX + r*math.cos(rad), CY - r*math.sin(rad)
    x0, y0 = pt(a0); x1, y1 = pt(a1)
    large = 1 if abs(a1-a0) > 180 else 0
    return f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 0 {x1:.1f} {y1:.1f}"

def feet():
    out = []
    for angle, dirn in [(-68, 1), (248, -1)]:
        rad = math.radians(angle); ex = CX+RING_R*math.cos(rad); ey = CY-RING_R*math.sin(rad)
        out.append(f"M {ex:.1f} {ey:.1f} L {ex+dirn*54:.1f} {ey:.1f}")
    return out

def placements():
    advs = [g["adv"] for g in GLYPHS]; n = len(GLYPHS); center = (n-1)/2
    def facts():
        out = []
        for i, ch in enumerate(NAME):
            u = (i-center)/(center+0.5); lens = max(0.0, 1-u*u)**POWER
            fx = FMIN+(1-FMIN)*lens; fy = fx*(1+VSTRETCH*lens)
            if ch == "-":
                fx = min(fx, HYPHEN_F); fy = min(fy, HYPHEN_F*1.35)
            out.append((fx, fy))
        return out
    def layout(b):
        f = facts(); sx = [b*a for a, _ in f]; sy = [b*c for _, c in f]
        w = [advs[i]*sx[i] for i in range(n)]
        penX = CX - (sum(w)+GAP*(n-1))/2; placed = []
        for i in range(n):
            placed.append((penX, sx[i], sy[i], w[i])); penX += w[i]+GAP
        return placed
    def maxR(placed):
        R = 0.0
        for (px, sx, sy, w) in placed:
            for X in (px, px+w):
                for Y in (CY-sy*(CAP-VC), CY+sy*VC):
                    R = max(R, math.hypot(X-CX, Y-CY))
        return R
    b = 0.9; placed = layout(b); R = maxR(placed)
    if R > R_IN:
        b *= R_IN/R; placed = layout(b)
    return [(placed[i][0], placed[i][1], placed[i][2], GLYPHS[i]["d"]) for i in range(n)]

PL = placements()
RING = arc_path(RING_R, -68, 248)
FEET = feet()
GLOW = ('<filter id="g" x="-30%" y="-30%" width="160%" height="160%">'
        '<feGaussianBlur stdDeviation="6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

def word_svg():
    parts = []
    for (px, sx, sy, d) in PL:
        ty = CY+sy*VC
        parts.append(f'<g transform="translate({px:.2f},{ty:.2f}) scale({sx:.5f},{-sy:.5f})"><path d="{d}"/></g>')
    return f'<g fill="{WORD_C}">{"".join(parts)}</g>'

def emblem():
    feet_svg = "".join(f'<path d="{p}"/>' for p in FEET)
    return (f'<g filter="url(#g)" stroke="{RING_C}" stroke-width="{RING_W}" fill="none" stroke-linecap="round">'
            f'<path d="{RING}"/>{feet_svg}</g><g filter="url(#g)">{word_svg()}</g>')

def master_svg(rounded=True):
    rx = 220 if rounded else 0
    border = f'<rect x="18" y="18" width="988" height="988" rx="{max(0,rx-16)}" fill="none" stroke="#24333C" stroke-width="3"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E171D"/><stop offset="1" stop-color="#05090c"/></linearGradient>
<radialGradient id="halo" cx="0.5" cy="0.46" r="0.55"><stop offset="0" stop-color="{HALO_C}" stop-opacity="0.15"/><stop offset="1" stop-color="{HALO_C}" stop-opacity="0"/></radialGradient>
{GLOW}
</defs>
<rect width="1024" height="1024" rx="{rx}" fill="url(#bg)"/>
{border}
<rect width="1024" height="1024" rx="{rx}" fill="url(#halo)"/>
{emblem()}
</svg>'''

def android_fg_svg():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>{GLOW}</defs>
<g transform="translate(512,512) scale({FG_SCALE}) translate(-512,-512)">{emblem()}</g>
</svg>'''

def render_png(svg, size):
    png = resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)
    return bytes(png) if isinstance(png, list) else png

def write(rel, content, binary=False):
    full = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
        f.write(content)

def main():
    # shared master
    write("bridge/shared/icon/omega-arc-icon.svg", master_svg(True))

    # iOS: full-bleed 1024, alpha stripped (App Store requires no alpha)
    png = render_png(master_svg(False), 1024)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    base = "bridge/bridge-zero-ios/Sources/Assets.xcassets"
    write(f"{base}/AppIcon.appiconset/icon_1024.png", buf.getvalue(), binary=True)
    write(f"{base}/AppIcon.appiconset/Contents.json", json.dumps(
        {"images": [{"filename": "icon_1024.png", "idiom": "universal",
                     "platform": "ios", "size": "1024x1024"}],
         "info": {"author": "xcode", "version": 1}}, indent=2))
    write(f"{base}/Contents.json", json.dumps({"info": {"author": "xcode", "version": 1}}, indent=2))

    # Android: adaptive icon
    res = "bridge/bridge-zero-android/app/src/main/res"
    fg = android_fg_svg()
    for dens, px in {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}.items():
        write(f"{res}/mipmap-{dens}/ic_launcher_foreground.png", render_png(fg, px), binary=True)
    adaptive = ('<?xml version="1.0" encoding="utf-8"?>\n'
                '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '    <background android:drawable="@drawable/ic_launcher_background" />\n'
                '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
                '</adaptive-icon>\n')
    write(f"{res}/mipmap-anydpi-v26/ic_launcher.xml", adaptive)
    write(f"{res}/mipmap-anydpi-v26/ic_launcher_round.xml", adaptive)
    write(f"{res}/drawable/ic_launcher_background.xml",
          '<?xml version="1.0" encoding="utf-8"?>\n'
          '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\n'
          '    <gradient android:type="linear" android:angle="270"\n'
          '        android:startColor="#0E171D" android:endColor="#05090C" />\n'
          '</shape>\n')
    print("Regenerated iOS + Android icon assets and the shared master SVG.")

if __name__ == "__main__":
    main()
