"""Regenerates every texture of the Glucose Device from i18n_src.py (needs Pillow, numpy and Noto Sans CJK Bold).

Run from the repository root:  python3 tools/make_textures.py
Writes unity/GlucoseDevice/Textures/ and the preview images in docs/images/.
To check the output without touching the repo:  python3 tools/make_textures.py /some/empty/folder
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
# Textures go into the Unity folder; preview images go to docs/images.
# Pass a folder as the first argument to write everything there instead (for checking).
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "unity", "GlucoseDevice", "Textures")
PREVIEW_DIR = os.path.join(OUT, "previews") if len(sys.argv) > 1 else os.path.join(REPO, "docs", "images")
PREVIEW = os.path.join(PREVIEW_DIR, "preview_states.png")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)
for f in os.listdir(OUT):
    if f.startswith("lcd_") and f.endswith(".png"):
        os.remove(os.path.join(OUT, f))

COLORS = {"ok": (127, 224, 188), "low": (255, 156, 200), "high": (255, 176, 92), "stale": (154, 160, 168)}
SS = 4               # supersampling for smooth edges
GHOST_ALPHA = 0.10   # unlit segments


# ---------------------------------------------------------------- helpers
def mask_from_polys(w, h, polys):
    img = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(img)
    for poly in polys:
        d.polygon([(x * SS, y * SS) for x, y in poly], fill=255)
    return np.asarray(img.resize((w, h), Image.BOX), dtype=np.float32) / 255.0


ALPHAS = {}


def to_rgba(alpha, color):
    h, w = alpha.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = color
    out[..., 3] = np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def seg7(cx, cy, w, h, t, gap):
    """Polygons for the seven segments of a digit centred on (cx, cy)."""
    hw = t / 2.0
    L = (w - t) / 2.0 - gap
    Lv = (h - t) / 4.0 - gap
    xl, xr = cx - (w - t) / 2.0, cx + (w - t) / 2.0
    yt, yb = cy - (h - t) / 2.0, cy + (h - t) / 2.0

    def hseg(x, y):
        return [(x - L, y), (x - L + hw, y - hw), (x + L - hw, y - hw),
                (x + L, y), (x + L - hw, y + hw), (x - L + hw, y + hw)]

    def vseg(x, y):
        return [(x, y - Lv), (x + hw, y - Lv + hw), (x + hw, y + Lv - hw),
                (x, y + Lv), (x - hw, y + Lv - hw), (x - hw, y - Lv + hw)]

    return {
        "a": hseg(cx, yt), "g": hseg(cx, cy), "d": hseg(cx, yb),
        "f": vseg(xl, (yt + cy) / 2.0), "b": vseg(xr, (yt + cy) / 2.0),
        "e": vseg(xl, (cy + yb) / 2.0), "c": vseg(xr, (cy + yb) / 2.0),
    }


DIGIT_SEGS = {
    0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc",
    5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abfgcd", 10: "",
}


# ---------------------------------------------------------------- digits (11 frames, 64x96)
FW, FH, NF = 64, 96, 11
strip = np.zeros((FH, FW * NF), dtype=np.float32)
for k in range(NF):
    segs = seg7(32, 48, 40, 76, 8.5, 2.2)
    ghost = mask_from_polys(FW, FH, segs.values())
    active = mask_from_polys(FW, FH, [segs[s] for s in DIGIT_SEGS[k]]) if DIGIT_SEGS[k] else np.zeros((FH, FW), np.float32)
    strip[:, k * FW:(k + 1) * FW] = np.maximum(ghost * GHOST_ALPHA, active)
ALPHAS["lcd_digits"] = strip.copy()

# ---------------------------------------------------------------- arrows (3 frames, 64x64): blank, single, double. Points RIGHT; the animator rotates it.
AW, AH, AN = 64, 64, 3


def arrow_polys(double):
    polys = []
    if double:
        polys.append([(32 - 24, 32 - 4.5), (32 - 4, 32 - 4.5), (32 - 4, 32 + 4.5), (32 - 24, 32 + 4.5)])
        polys.append([(32 + 8, 32 - 14), (32 + 24, 32), (32 + 8, 32 + 14)])
        polys.append([(32 - 8, 32 - 14), (32 + 8, 32), (32 - 8, 32 + 14)])
    else:
        polys.append([(32 - 24, 32 - 4.5), (32 + 6, 32 - 4.5), (32 + 6, 32 + 4.5), (32 - 24, 32 + 4.5)])
        polys.append([(32 + 4, 32 - 15), (32 + 24, 32), (32 + 4, 32 + 15)])
    return polys


strip = np.zeros((AH, AW * AN), dtype=np.float32)
strip[:, AW:2 * AW] = mask_from_polys(AW, AH, arrow_polys(False))
strip[:, 2 * AW:3 * AW] = mask_from_polys(AW, AH, arrow_polys(True))
ALPHAS["lcd_arrow"] = strip.copy()

# ---------------------------------------------------------------- state labels (4 frames, 64x32) - bold block letters
LW, LH, LN = 64, 32, 4


def block_letter(ch, x, y, w=19, h=26, s=5.5):
    """Return (fill_rects, cut_rects) for a bold block letter whose top-left is (x, y)."""
    if ch == "L":
        return [(x, y, x + s, y + h), (x, y + h - s, x + w, y + h)], []
    if ch == "O":
        return [(x, y, x + w, y + h)], [(x + s, y + s, x + w - s, y + h - s)]
    if ch == "H":
        return [(x, y, x + s, y + h), (x + w - s, y, x + w, y + h), (x, y + h / 2 - s / 2, x + w, y + h / 2 + s / 2)], []
    if ch == "I":
        cx = x + w / 2
        return [(cx - s / 2, y, cx + s / 2, y + h), (x + 2, y, x + w - 2, y + s), (x + 2, y + h - s, x + w - 2, y + h)], []
    if ch == "-":
        return [(x + 1, y + h / 2 - s / 2, x + w - 1, y + h / 2 + s / 2)], []
    raise ValueError(ch)


LABELS = {0: "", 1: "LO", 2: "HI", 3: "--"}
strip = np.zeros((LH, LW * LN), dtype=np.float32)
for k in range(LN):
    if not LABELS[k]:
        continue
    img = Image.new("L", (LW * SS, LH * SS), 0)
    d = ImageDraw.Draw(img)
    for i, ch in enumerate(LABELS[k]):
        fills, cuts = block_letter(ch, 9 + i * 28, 3)
        for r in fills:
            d.rectangle([c * SS for c in r], fill=255)
        for r in cuts:
            d.rectangle([c * SS for c in r], fill=0)
    strip[:, k * LW:(k + 1) * LW] = np.asarray(img.resize((LW, LH), Image.BOX), dtype=np.float32) / 255.0
ALPHAS["lcd_state"] = strip.copy()

# ---------------------------------------------------------------- unit labels (2 frames, 128x32), 5x9 pixel font
UW, UH, UN = 128, 32, 2
GLYPHS = {
    "m": {2: "11010", 3: "10101", 4: "10101", 5: "10101", 6: "10101"},
    "o": {2: "01110", 3: "10001", 4: "10001", 5: "10001", 6: "01110"},
    "l": {0: "01100", 1: "00100", 2: "00100", 3: "00100", 4: "00100", 5: "00100", 6: "01110"},
    "L": {0: "10000", 1: "10000", 2: "10000", 3: "10000", 4: "10000", 5: "10000", 6: "11111"},
    "d": {0: "00001", 1: "00001", 2: "01111", 3: "10001", 4: "10001", 5: "10001", 6: "01111"},
    "g": {2: "01111", 3: "10001", 4: "10001", 5: "10001", 6: "01111", 7: "00001", 8: "01110"},
    "/": {0: "00001", 1: "00001", 2: "00010", 3: "00010", 4: "00100", 5: "00100", 6: "01000", 7: "01000", 8: "10000"},
}
UNITS = {0: "mmol/L", 1: "mg/dL"}
PX, SP = 3, 3
strip = np.zeros((UH, UW * UN), dtype=np.float32)
for k in range(UN):
    text = UNITS[k]
    total = len(text) * 5 * PX + (len(text) - 1) * SP
    x0 = k * UW + (UW - total) // 2
    y0 = (UH - 9 * PX) // 2
    for i, ch in enumerate(text):
        gx = x0 + i * (5 * PX + SP)
        for row, bits in GLYPHS[ch].items():
            for col, b in enumerate(bits):
                if b == "1":
                    strip[y0 + row * PX:y0 + (row + 1) * PX, gx + col * PX:gx + (col + 1) * PX] = 1.0
ALPHAS["lcd_units"] = strip.copy()

# ---------------------------------------------------------------- decimal dot (32x32)
dot = np.zeros((32, 32), dtype=np.float32)
dot[8:24, 8:24] = 1.0
ALPHAS["lcd_dot"] = dot.copy()


# ---------------------------------------------------------------- words panels: 10 languages x 4 colour rows
import sys
sys.path.insert(0, HERE)
import i18n_src as I
from PIL import ImageDraw, ImageFont

WW, WH = 176, 120
FONT_FILE = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_INDEX = {"ja": 0, "ko": 1, "zh-Hans": 2, "zh-Hant": 3}   # everything else uses the JP face (Latin + Cyrillic)
ORDER = ["ok", "low", "high", "stale"]


def lines_size(font, lines):
    widths = [font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines]
    return max(widths)


def fit_font(lang):
    """Largest font size at which every line of every state fits the panel."""
    idx = FONT_INDEX.get(lang, 0)
    for size in range(44, 8, -1):
        font = ImageFont.truetype(FONT_FILE, size, index=idx)
        gap = int(size * 0.18)
        ok = True
        for st in ORDER:
            lines = I.WORDS[lang][st]
            if lines_size(font, lines) > WW - 14:
                ok = False
                break
            if len(lines) * size + (len(lines) - 1) * gap > WH - 10:
                ok = False
                break
        if ok:
            return font, size, gap
    raise RuntimeError("text does not fit for " + lang)


def render_words(lang, state):
    font, size, gap = fit_font(lang)
    SSW = 4
    big = ImageFont.truetype(FONT_FILE, size * SSW, index=FONT_INDEX.get(lang, 0))
    img = Image.new("L", (WW * SSW, WH * SSW), 0)
    d = ImageDraw.Draw(img)
    lines = I.WORDS[lang][state]
    line_h = size * SSW + gap * SSW
    total = len(lines) * size * SSW + (len(lines) - 1) * gap * SSW
    y = (WH * SSW - total) // 2
    for line in lines:
        bbox = big.getbbox(line)
        w = bbox[2] - bbox[0]
        x = (WW * SSW - w) // 2 - bbox[0]
        d.text((x, y - bbox[1] + (size * SSW - (bbox[3] - bbox[1])) // 2 if False else y), line, font=big, fill=255, anchor="la")
        y += line_h
    return np.asarray(img.resize((WW, WH), Image.LANCZOS), dtype=np.float32) / 255.0


word_alpha = {lang: {st: render_words(lang, st) for st in ORDER} for lang in I.WORD_LANGS}

# ---------------------------------------------------------------- stack colour rows into atlases
# Row order seen in Unity (v offset 0, 0.25, 0.5, 0.75): ok, low, high, stale.
# PNG rows run top to bottom, so the file stacks stale, high, low, ok.


def stack(alphas_by_key):
    rows = [np.asarray(to_rgba(alphas_by_key[k], COLORS[k])) for k in reversed(ORDER)]
    return Image.fromarray(np.vstack(rows), "RGBA")


for base, alpha in ALPHAS.items():
    stack({k: alpha for k in ORDER}).save(os.path.join(OUT, f"{base}.png"))

# words atlas: columns = languages, rows = colours
rows = []
for st in reversed(ORDER):
    row = np.hstack([np.asarray(to_rgba(word_alpha[lang][st], COLORS[st])) for lang in I.WORD_LANGS])
    rows.append(row)
Image.fromarray(np.vstack(rows), "RGBA").save(os.path.join(OUT, "lcd_words.png"))

# cover for "no data": opaque black with a grey "--"
cover = np.zeros((64, 128, 4), np.uint8)
cover[..., 3] = 255
for x0 in (30, 70):
    cover[28:36, x0:x0 + 28, :3] = COLORS["stale"]
Image.fromarray(cover, "RGBA").save(os.path.join(OUT, "lcd_nodata.png"))

# ---------------------------------------------------------------- previews (same layout the Unity builder uses)
SCREEN = (0.060, 0.040)
PXM = 10000
LAYOUT = {
    "digit": dict(size=(0.011, 0.0165), xs=[-0.017, -0.005, 0.011], y=0.0055),
    "dot": dict(size=(0.003, 0.003), x=0.003, y=-0.0010),
    "arrow": dict(size=(0.011, 0.011), x=0.0235, y=0.0050),
    "state": dict(size=(0.014, 0.007), x=-0.0225, y=-0.0135),
    "unit": dict(size=(0.020, 0.005), x=0.0185, y=-0.0135),
    "words": dict(size=(0.044, 0.030), x=-0.0055, y=0.002),
}


def frame(name, cols, k, color):
    img = Image.open(os.path.join(OUT, f"{name}.png"))
    w, h = img.width // cols, img.height // 4
    top = (3 - ORDER.index(color)) * h
    return img.crop((k * w, top, (k + 1) * w, top + h))


def paste_item(base, tile, cx, cy, size, rot=0):
    w, h = round(size[0] * PXM), round(size[1] * PXM)
    tile = tile.resize((w, h), Image.LANCZOS)
    if rot:
        tile = tile.rotate(rot, resample=Image.BICUBIC)
    px = round(base.width / 2 + cx * PXM - w / 2)
    py = round(base.height / 2 - cy * PXM - h / 2)
    base.alpha_composite(tile, (px, py))


def render(c, digits, arrow, state, unit_frame, dot_on=True, words=False):
    W, H = round(SCREEN[0] * PXM), round(SCREEN[1] * PXM)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    if words:
        paste_item(img, frame("lcd_words", len(I.WORD_LANGS), 0, c), LAYOUT["words"]["x"], LAYOUT["words"]["y"], LAYOUT["words"]["size"])
    else:
        for x, k in zip(LAYOUT["digit"]["xs"], digits):
            paste_item(img, frame("lcd_digits", 11, k, c), x, LAYOUT["digit"]["y"], LAYOUT["digit"]["size"])
        if dot_on:
            paste_item(img, frame("lcd_dot", 1, 0, c), LAYOUT["dot"]["x"], LAYOUT["dot"]["y"], LAYOUT["dot"]["size"])
        paste_item(img, frame("lcd_state", 4, state, c), LAYOUT["state"]["x"], LAYOUT["state"]["y"], LAYOUT["state"]["size"])
        paste_item(img, frame("lcd_units", 2, unit_frame, c), LAYOUT["unit"]["x"], LAYOUT["unit"]["y"], LAYOUT["unit"]["size"])
    fr, rot = arrow
    paste_item(img, frame("lcd_arrow", 3, fr, c), LAYOUT["arrow"]["x"], LAYOUT["arrow"]["y"], LAYOUT["arrow"]["size"], rot)
    return img


def sheet_of(panels, path):
    pad = 30
    pw, ph = panels[0].size
    sh = Image.new("RGBA", (pw * 2 + pad * 3, ph * 2 + pad * 3), (36, 40, 46, 255))
    for i, p in enumerate(panels):
        sh.alpha_composite(p, (pad + (i % 2) * (pw + pad), pad + (i // 2) * (ph + pad)))
    sh.convert("RGB").save(path)


sheet_of([
    render("ok", (10, 6, 2), (1, 0), 0, 0),
    render("low", (10, 3, 4), (1, -45), 1, 0),
    render("high", (1, 2, 0), (2, 90), 2, 1, False),
    render("stale", (10, 10, 10), (0, 0), 3, 1, False),
], PREVIEW)
sheet_of([
    render("ok", None, (1, 0), 0, 0, words=True),
    render("low", None, (1, -45), 0, 0, words=True),
    render("high", None, (2, 90), 0, 0, words=True),
    render("stale", None, (1, 0), 0, 0, words=True),
], os.path.join(PREVIEW_DIR, "preview_simple.png"))
# contact sheet: all languages x four states
cs = Image.new("RGB", (4 * WW + 5 * 8, len(I.WORD_LANGS) * WH + (len(I.WORD_LANGS) + 1) * 8), (36, 40, 46))
for li, lang in enumerate(I.WORD_LANGS):
    for si, st in enumerate(ORDER):
        tile = Image.new("RGBA", (WW, WH), (0, 0, 0, 255))
        tile.alpha_composite(frame("lcd_words", len(I.WORD_LANGS), li, st))
        cs.paste(tile.convert("RGB"), (8 + si * (WW + 8), 8 + li * (WH + 8)))
cs.save(os.path.join(PREVIEW_DIR, "preview_languages.png"))
print(sorted(os.listdir(OUT)))

# ---------------------------------------------------------------- alternative: dot-matrix look for the words panel
# Same grid and file layout as lcd_words.png, so it can be swapped in by renaming it. The text is drawn
# at half size with no smoothing and doubled with hard edges, which gives a blocky LCD feel.
ALT_DIR = os.path.join(OUT, "Alternatives")
os.makedirs(ALT_DIR, exist_ok=True)
HW, HH = WW // 2, WH // 2


def render_words_dot(lang, state):
    idx = FONT_INDEX.get(lang, 0)
    size = None
    for sz in range(22, 5, -1):
        font = ImageFont.truetype(FONT_FILE, sz, index=idx)
        gap = max(1, int(sz * 0.15))
        fits = True
        for st in ORDER:
            lines = I.WORDS[lang][st]
            if lines_size(font, lines) > HW - 6 or len(lines) * sz + (len(lines) - 1) * gap > HH - 4:
                fits = False
                break
        if fits:
            size = sz
            break
    font = ImageFont.truetype(FONT_FILE, size, index=idx)
    gap = max(1, int(size * 0.15))
    img = Image.new("L", (HW, HH), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    lines = I.WORDS[lang][state]
    total = len(lines) * size + (len(lines) - 1) * gap
    y = (HH - total) // 2
    for line in lines:
        w = font.getbbox(line)[2] - font.getbbox(line)[0]
        d.text(((HW - w) // 2 - font.getbbox(line)[0], y), line, font=font, fill=255, anchor="la")
        y += size + gap
    big = img.resize((WW, WH), Image.NEAREST)
    return np.asarray(big, dtype=np.float32) / 255.0


dot_alpha = {lang: {st: render_words_dot(lang, st) for st in ORDER} for lang in I.WORD_LANGS}
rows = []
for st in reversed(ORDER):
    rows.append(np.hstack([np.asarray(to_rgba(dot_alpha[lang][st], COLORS[st])) for lang in I.WORD_LANGS]))
Image.fromarray(np.vstack(rows), "RGBA").save(os.path.join(ALT_DIR, "lcd_words_dotmatrix.png"))
cs2 = Image.new("RGB", (4 * WW + 5 * 8, 4 * WH + 5 * 8), (36, 40, 46))
for li, lang in enumerate(["en", "de", "ja", "ru"]):
    for si, st in enumerate(ORDER):
        tile = Image.new("RGBA", (WW, WH), (0, 0, 0, 255))
        a = np.asarray(to_rgba(dot_alpha[lang][st], COLORS[st]))
        tile.alpha_composite(Image.fromarray(a, "RGBA"))
        cs2.paste(tile.convert("RGB"), (8 + si * (WW + 8), 8 + li * (WH + 8)))
cs2.save(os.path.join(PREVIEW_DIR, "preview_dotmatrix.png"))
print("alternative written:", os.path.join(ALT_DIR, "lcd_words_dotmatrix.png"))
