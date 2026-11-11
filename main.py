#!/usr/bin/env python3
"""Cutest cat for make.fun bounty cutest-cat-01.

A program that DRAWS a cute cat in code and writes it to /output/entry.png.

Python 3.13, standard library only: no Pillow, no network, no model calls,
no randomness, no clock. The picture is rasterised into a byte buffer with a
tiny span-fill rasteriser (circles, rotated ellipses, polygons, thick
polylines, arcs) and encoded as a PNG with zlib, so both runs of the program
write byte-identical output.

The cat: a happy ginger kitten, sitting front-on and centred, head tilted,
big bright amber eyes, small smile with a tongue blep, pink bow on one ear,
curled tail, one paw resting on a red ball of yarn, on a soft cream
background. One glance says cat; soft round shapes; one small story (the
yarn ball); clean storybook outlines; nothing crowds the frame.

Run locally:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
CREAM_TOP = (255, 247, 232)
CREAM_BOT = (255, 229, 197)
GLOW = (255, 239, 205)
SHADOW = (232, 196, 150)
OUTLINE = (172, 102, 38)       # warm brown outline for the fur
FUR = (245, 169, 92)           # ginger
FUR_LIGHT = (250, 192, 122)
FUR_DARK = (222, 136, 56)      # tabby stripes
CREAM_FUR = (255, 240, 216)    # muzzle / chest / paws
INNER_EAR = (248, 168, 178)
NOSE = (232, 122, 138)
BOW = (242, 125, 157)
BOW_DARK = (214, 84, 120)
TONGUE = (244, 140, 155)
BLUSH = (246, 166, 158)
IRIS = (216, 134, 30)
IRIS_DARK = (158, 88, 18)
PUPIL = (38, 26, 20)
WHITE = (255, 255, 255)
WHISKER = (158, 118, 78)
MOUTH = (120, 74, 44)
YARN = (228, 87, 90)
YARN_DARK = (196, 58, 64)
GOLD = (247, 205, 110)

# ---------------------------------------------------------------- canvas
# rows[y] is a bytearray of W*3 RGB bytes.
rows = [bytearray(W * 3) for _ in range(H)]


def _span(y, x0, x1, rgb):
    """Fill row y from x0 to x1 inclusive with rgb (fast C-level slice)."""
    if y < 0 or y >= H:
        return
    if x0 < 0:
        x0 = 0
    if x1 >= W:
        x1 = W - 1
    if x1 < x0:
        return
    n = x1 - x0 + 1
    rows[y][x0 * 3:(x1 + 1) * 3] = bytes(rgb) * n


def ellipse(cx, cy, rx, ry, rgb, rot=0.0):
    """Filled ellipse, optionally rotated by rot radians."""
    if rx <= 0 or ry <= 0:
        return
    c = math.cos(rot)
    s = math.sin(rot)
    a = c * c / (rx * rx) + s * s / (ry * ry)
    b_factor = 2.0 * c * s * (1.0 / (rx * rx) - 1.0 / (ry * ry))
    c_factor = s * s / (rx * rx) + c * c / (ry * ry)
    # vertical extent of the rotated ellipse
    ext = math.sqrt((rx * s) ** 2 + (ry * c) ** 2)
    y0 = max(0, int(math.floor(cy - ext)))
    y1 = min(H - 1, int(math.ceil(cy + ext)))
    for y in range(y0, y1 + 1):
        dy = y - cy
        b = b_factor * dy
        cc = c_factor * dy * dy - 1.0
        disc = b * b - 4.0 * a * cc
        if disc < 0:
            continue
        root = math.sqrt(disc)
        x_lo = cx + (-b - root) / (2.0 * a)
        x_hi = cx + (-b + root) / (2.0 * a)
        _span(y, int(math.ceil(x_lo)), int(math.floor(x_hi)), rgb)


def circle(cx, cy, r, rgb):
    ellipse(cx, cy, r, r, rgb)


def polygon(points, rgb):
    """Filled polygon (scanline). Points: list of (x, y)."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(H - 1, int(math.ceil(max(ys))))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1p = points[i]
            x2, y2p = points[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _span(y, int(math.ceil(xs[i])), int(math.floor(xs[i + 1])), rgb)


def thick_line(x1, y1, x2, y2, width, rgb):
    """A straight thick line, drawn as overlapping circles."""
    dist = math.hypot(x2 - x1, y2 - y1)
    steps = max(2, int(dist / max(1.0, width * 0.4)) + 1)
    r = width / 2.0
    for i in range(steps + 1):
        t = i / steps
        circle(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r, rgb)


def polyline(points, width, rgb):
    for i in range(len(points) - 1):
        thick_line(points[i][0], points[i][1],
                   points[i + 1][0], points[i + 1][1], width, rgb)


def arc(cx, cy, rx, ry, a0, a1, width, rgb):
    """Thick elliptical arc from angle a0 to a1 (radians)."""
    steps = max(4, int(abs(a1 - a0) * max(rx, ry) / 2.5) + 1)
    r = width / 2.0
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        circle(cx + rx * math.cos(a), cy + ry * math.sin(a), r, rgb)


def outline_ellipse(cx, cy, rx, ry, rgb, rot=0.0, pad=7):
    ellipse(cx, cy, rx + pad, ry + pad, rgb, rot)


def star4(cx, cy, r, rgb):
    """A small four-point sparkle."""
    polygon([(cx, cy - r), (cx + r * 0.28, cy - r * 0.28),
             (cx + r, cy), (cx + r * 0.28, cy + r * 0.28),
             (cx, cy + r), (cx - r * 0.28, cy + r * 0.28),
             (cx - r, cy), (cx - r * 0.28, cy - r * 0.28)], rgb)


def flower(cx, cy, petal, rgb, centre):
    for k in range(5):
        a = -math.pi / 2 + k * 2 * math.pi / 5
        circle(cx + petal * 1.05 * math.cos(a),
               cy + petal * 1.05 * math.sin(a), petal, rgb)
    circle(cx, cy, petal * 0.75, centre)


# ---------------------------------------------------------------- background
def background():
    for y in range(H):
        t = y / (H - 1)
        rgb = tuple(int(CREAM_TOP[i] + (CREAM_BOT[i] - CREAM_TOP[i]) * t)
                    for i in range(3))
        rows[y][:] = bytes(rgb) * W
    # soft warm glow behind the kitten's head
    ellipse(512, 480, 335, 335, GLOW)
    # faint bokeh dots, kept pale so nothing crowds the cat
    circle(150, 210, 26, (255, 238, 205))
    circle(880, 300, 20, (255, 238, 205))
    circle(120, 620, 18, (255, 240, 212))
    circle(905, 640, 24, (255, 240, 212))


# ---------------------------------------------------------------- the kitten
def tail():
    # curled tail on the kitten's left (viewer's right), behind the body
    pts = []
    for i in range(41):
        t = i / 40.0
        # quadratic bezier: start (688, 838), control (848, 828), end (838, 668)
        x = (1 - t) ** 2 * 688 + 2 * (1 - t) * t * 848 + t * t * 838
        y = (1 - t) ** 2 * 838 + 2 * (1 - t) * t * 828 + t * t * 668
        pts.append((x, y))
    for (x, y) in pts:
        circle(x, y, 42, OUTLINE)
    for (x, y) in pts:
        circle(x, y, 35, FUR)
    # tabby bands across the tail
    for t in (0.30, 0.55, 0.80):
        x = (1 - t) ** 2 * 688 + 2 * (1 - t) * t * 848 + t * t * 838
        y = (1 - t) ** 2 * 838 + 2 * (1 - t) * t * 828 + t * t * 668
        thick_line(x - 30, y - 8, x + 30, y + 10, 13, FUR_DARK)
    # cream tip (small, at the very end of the curl)
    circle(840, 664, 28, CREAM_FUR)


def body():
    ellipse(512, 908, 312, 44, SHADOW)          # ground shadow
    outline_ellipse(512, 798, 215, 178, OUTLINE)
    ellipse(512, 798, 215, 178, FUR)
    # haunches
    outline_ellipse(352, 872, 96, 76, OUTLINE)
    ellipse(352, 872, 96, 76, FUR)
    outline_ellipse(672, 872, 96, 76, OUTLINE)
    ellipse(672, 872, 96, 76, FUR)
    # cream chest
    ellipse(512, 832, 126, 116, CREAM_FUR)
    # front legs
    outline_ellipse(444, 848, 58, 102, OUTLINE)
    ellipse(444, 848, 58, 102, FUR_LIGHT)
    outline_ellipse(580, 848, 58, 102, OUTLINE)
    ellipse(580, 848, 58, 102, FUR_LIGHT)
    # paws with toe lines, and a divider between the two paws
    ellipse(444, 928, 62, 38, CREAM_FUR)
    ellipse(580, 928, 62, 38, CREAM_FUR)
    thick_line(512, 906, 512, 950, 4, MOUTH)
    for px in (444, 580):
        thick_line(px - 18, 912, px - 18, 940, 4, MOUTH)
        thick_line(px + 18, 912, px + 18, 940, 4, MOUTH)


def yarn_ball():
    # favourite toy: a red ball of yarn by the kitten's paw
    outline_ellipse(782, 884, 74, 74, (150, 40, 46))
    circle(782, 884, 74, YARN)
    arc(782, 884, 62, 62, math.pi * 0.15, math.pi * 0.85, 7, YARN_DARK)
    arc(782, 884, 62, 62, math.pi * 1.15, math.pi * 1.85, 7, YARN_DARK)
    arc(782, 884, 40, 40, math.pi * 0.9, math.pi * 1.6, 7, YARN_DARK)
    arc(782, 884, 74, 74, math.pi * 1.05, math.pi * 1.45, 7, YARN_DARK)
    # a loose strand curling towards the paw
    polyline([(724, 918), (690, 940), (652, 946), (622, 936)], 7, YARN_DARK)


def head():
    tilt = -0.12  # head tilt: the charm
    # ears (left ear higher, matching the tilt)
    polygon([(306, 330), (388, 158), (486, 326)], OUTLINE)
    polygon([(318, 318), (392, 178), (472, 312)], FUR)
    polygon([(352, 292), (396, 208), (442, 296)], INNER_EAR)
    polygon([(556, 322), (640, 182), (716, 330)], OUTLINE)
    polygon([(568, 310), (640, 202), (700, 316)], FUR)
    polygon([(596, 292), (640, 216), (676, 296)], INNER_EAR)
    # cheek fur tufts (drawn after the head so they stick out past it)
    polygon([(252, 516), (302, 498), (286, 566)], OUTLINE)
    polygon([(260, 518), (298, 502), (284, 556)], FUR)
    polygon([(772, 498), (722, 482), (738, 550)], OUTLINE)
    polygon([(764, 500), (726, 486), (740, 540)], FUR)
    # head
    outline_ellipse(512, 465, 255, 228, OUTLINE, tilt)
    ellipse(512, 465, 255, 228, FUR, tilt)
    # forehead tabby stripes
    for (sx, sy, rot) in ((448, 272, 0.25), (512, 256, 0.0), (576, 272, -0.25)):
        ellipse(sx, sy, 15, 38, FUR_DARK, rot)
    # cream muzzle: two round cheeks + chin
    ellipse(456, 570, 90, 64, CREAM_FUR, -0.06)
    ellipse(568, 562, 90, 64, CREAM_FUR, -0.06)
    ellipse(512, 606, 62, 40, CREAM_FUR)
    # blush
    ellipse(352, 578, 40, 24, BLUSH, -0.1)
    ellipse(674, 560, 40, 24, BLUSH, -0.1)


def eye(cx, cy, side):
    """Huge bright amber eye. side: -1 left eye, +1 right eye (lashes outside)."""
    # huge bright amber eye: outline, white, iris, pupil, sparkles
    ellipse(cx, cy, 68, 78, OUTLINE)
    ellipse(cx, cy, 62, 72, WHITE)
    ellipse(cx, cy + 4, 46, 54, IRIS_DARK)
    ellipse(cx, cy + 4, 40, 48, IRIS)
    ellipse(cx, cy + 6, 21, 29, PUPIL)
    circle(cx - 18, cy - 20, 15, WHITE)   # big sparkle highlight
    circle(cx + 16, cy + 20, 7, WHITE)    # small sparkle highlight
    # lashes on the outer upper corner
    thick_line(cx + side * 52, cy - 52, cx + side * 68, cy - 70, 5, PUPIL)
    thick_line(cx + side * 58, cy - 38, cx + side * 76, cy - 46, 5, PUPIL)


def face():
    eye(414, 466, -1)
    eye(610, 452, +1)
    # tiny pink nose
    polygon([(490, 548), (542, 544), (516, 580)], NOSE)
    # small smile: two arcs under the nose
    arc(496, 578, 26, 20, math.pi * 0.15, math.pi * 0.95, 5, MOUTH)
    arc(534, 576, 26, 20, math.pi * 0.05, math.pi * 0.85, 5, MOUTH)
    # tongue blep
    ellipse(515, 622, 24, 30, TONGUE)
    thick_line(515, 606, 515, 634, 4, BOW_DARK)
    # whiskers, three a side
    for (x1, y1, x2, y2) in ((398, 572, 268, 548), (396, 590, 272, 592),
                             (398, 606, 282, 640)):
        thick_line(x1, y1, x2, y2, 4, WHISKER)
    for (x1, y1, x2, y2) in ((632, 564, 756, 536), (634, 582, 758, 582),
                             (632, 598, 748, 632)):
        thick_line(x1, y1, x2, y2, 4, WHISKER)


def bow():
    # pink bow on the left ear (small, tucked against the ear base)
    polygon([(392, 306), (330, 274), (336, 338)], BOW_DARK)
    polygon([(392, 306), (330, 274), (336, 338)], BOW)
    polygon([(412, 296), (474, 262), (470, 326)], BOW_DARK)
    polygon([(412, 296), (474, 262), (470, 326)], BOW)
    circle(402, 300, 16, BOW_DARK)
    circle(402, 300, 12, BOW)


def decorations():
    star4(178, 176, 26, GOLD)
    star4(862, 208, 20, GOLD)
    star4(896, 430, 16, GOLD)
    star4(140, 420, 14, GOLD)
    # one tiny heart, top right
    circle(838, 132, 13, BOW)
    circle(862, 132, 13, BOW)
    polygon([(828, 140), (872, 140), (850, 168)], BOW)
    # small flowers low in the corners, out of the cat's way
    flower(148, 922, 15, (255, 255, 255), GOLD)
    flower(892, 918, 13, (255, 255, 255), GOLD)


# ---------------------------------------------------------------- PNG encode
def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += rows[y]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    background()
    tail()
    body()
    yarn_ball()
    head()
    face()
    bow()
    decorations()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path}: {W}x{H} PNG, {size} bytes")


if __name__ == "__main__":
    main()
