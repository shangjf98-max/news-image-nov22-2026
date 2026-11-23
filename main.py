#!/usr/bin/env python3
"""One-day world news front page: Sunday 22 November 2026.

Draws a 1024x1024 newspaper front page with pure stdlib Python: 3 lead
stories, 11 picture cards, 32 one-line briefs, a UTC timeline, a numbers
strip, a dotted world map, a date-check box and a confidence legend.
No fonts, no image files, no network. Deterministic: same bytes every run.
"""
import os
import struct
import zlib
from collections import Counter

W = 1024
H = 1024

# ---- palette ------------------------------------------------------------
PAPER = (247, 242, 228)
PAPER2 = (238, 231, 210)
INK = (26, 24, 20)
RED = (168, 30, 28)
NAVY = (31, 60, 102)
TEAL = (14, 92, 76)
GOLD = (178, 128, 26)
MUTED = (104, 97, 82)
LINEC = (196, 185, 158)
WHITE = (255, 255, 255)
SKY = (214, 228, 238)
SEA = (44, 96, 140)
SMOKE = (150, 148, 140)

# ---- canvas -------------------------------------------------------------
buf = bytearray(W * H * 3)
for i in range(0, W * H * 3, 3):
    buf[i] = PAPER[0]
    buf[i + 1] = PAPER[1]
    buf[i + 2] = PAPER[2]


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        o = (y * W + x) * 3
        buf[o] = c[0]
        buf[o + 1] = c[1]
        buf[o + 2] = c[2]


def rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        o = (yy * W + x0) * 3
        for xx in range(x0, x1):
            buf[o] = c[0]
            buf[o + 1] = c[1]
            buf[o + 2] = c[2]
            o += 3


def hline(x, y, w, c, t=1):
    rect(x, y, w, t, c)


def vline(x, y, h, c, t=1):
    rect(x, y, t, h, c)


def line(x0, y0, x1, y1, c):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def circle(cx, cy, r, c):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                px(xx, yy, c)


def ring(cx, cy, r, c, t=2):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d = (xx - cx) ** 2 + (yy - cy) ** 2
            if (r - t) ** 2 <= d <= r * r:
                px(xx, yy, c)


def poly(points, c):
    """Scanline fill of a simple polygon."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                px(x, y, c)


# ---- 5x7 bitmap font ('.' off, '#' on) ----------------------------------
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '%': ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#..##"),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '&': (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '*': (".....", "#...#", ".#.#.", ".###.", ".#.#.", "#...#", "....."),
    '#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    '@': (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    '·': (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
}
BLANK = (".....", ".....", ".....", ".....", ".....", ".....", ".....")


def text_w(s, sc):
    w = 0
    for ch in s:
        w += 3 * sc if ch == ' ' else 6 * sc
    return w - sc if w else 0


def draw_text(x, y, s, sc, c, serif=False, align="left"):
    """Draw uppercase bitmap text. serif=True adds slab-serif bars."""
    s = s.upper()
    if align == "center":
        x -= text_w(s, sc) // 2
    elif align == "right":
        x -= text_w(s, sc)
    cx = x
    for ch in s:
        g = FONT.get(ch, BLANK)
        if ch != ' ':
            for r in range(7):
                row = g[r]
                for col in range(5):
                    if row[col] == '#':
                        rect(cx + col * sc, y + r * sc, sc, sc, c)
            if serif and sc >= 4:
                rect(cx, y, 5 * sc, sc, c)
                rect(cx, y + 6 * sc, 5 * sc, sc, c)
        cx += 3 * sc if ch == ' ' else 6 * sc
    return cx


def wrap(s, width, sc):
    words = s.split()
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(trial, sc) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# ---- PNG writer ---------------------------------------------------------
def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw.extend(buf[y * W * 3:(y + 1) * W * 3])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---- story data ---------------------------------------------------------
LEADS = [
    {
        "num": 1, "region": "EUROPE", "field": "CLIMATE",
        "head": "COP31 COLLAPSES WITH NO DEAL",
        "deck": "Antalya talks end in failure after two weeks: no fossil-fuel line, no pact. Longest COP ever; first breakdown since 2009.",
        "tag": "CONFIRMED", "src": "CNN / REUTERS", "art": "climate",
    },
    {
        "num": 2, "region": "MIDDLE EAST", "field": "CONFLICT",
        "head": "IRAN: TWO MORE TANKERS HIT MINES",
        "deck": "Tehran says supertankers caught fire east of Hormuz. Bahrain seeks UN action; IRGC claims a 4th US drone downed.",
        "tag": "CLAIM", "src": "TASNIM / AP", "art": "tanker",
    },
    {
        "num": 3, "region": "EUROPE", "field": "CONFLICT",
        "head": "DRONE FLATTENS KYIV FLATS",
        "deck": "Three killed in Dymer; 186 drones overnight. Zelenskyy pleads for Patriots.",
        "tag": "CONFIRMED", "src": "AP / KYIV", "art": "kyiv",
    },
]

CARDS = [
    {"num": 4, "region": "EUROPE", "field": "CONFLICT",
     "head": "POLAND CONFIRMS KH-101 MISSILES",
     "cap": "FELL ON FRIDAY", "tag": "CONFIRMED", "src": "REUTERS", "art": "missile"},
    {"num": 5, "region": "SE ASIA", "field": "DISASTER",
     "head": "FACTORY FIRE: 3 DEAD, 34 MISSING",
     "cap": "DIGGING IN THE RUINS", "tag": "CONFIRMED", "src": "AP", "art": "flame"},
    {"num": 6, "region": "AFRICA", "field": "DISASTER",
     "head": "BOAT CAPSIZES: 24 DEAD IN NIGERIA",
     "cap": "BOUND FOR A FUNERAL", "tag": "CONFIRMED", "src": "AP", "art": "boat"},
    {"num": 7, "region": "N. AMERICA", "field": "SPORT",
     "head": "SKUBAL TO METS: $450M, 9 YEARS",
     "cap": "RECORD PITCHER DEAL", "tag": "CONFIRMED", "src": "AP", "art": "baseball"},
    {"num": 8, "region": "EUROPE", "field": "SPORT",
     "head": "LIVERPOOL 4-0 MAN UTD",
     "cap": "CLUB-WORST RUN", "tag": "CONFIRMED", "src": "NBC", "art": "soccer"},
    {"num": 9, "region": "MIDDLE EAST", "field": "CONFLICT",
     "head": "SETTLERS TORCH 12 VEHICLES",
     "cap": "OVERNIGHT RAIDS", "tag": "CONFIRMED", "src": "AP", "art": "house"},
    {"num": 10, "region": "N. AMERICA", "field": "TECH",
     "head": "US PRESSES NVIDIA ON CHINA CHIPS",
     "cap": "PROBES WIDEN", "tag": "REPORTED", "src": "NYT", "art": "chip"},
    {"num": 11, "region": "AFRICA", "field": "CONFLICT",
     "head": "DRONE BLAST HITS RUSSIAN SHIP",
     "cap": "PORT BLAZE", "tag": "REPORTED", "src": "AP", "art": "ship"},
    {"num": 12, "region": "ASIA-PACIFIC", "field": "ECONOMY",
     "head": "CHINA EASES MARGIN RULES",
     "cap": "STOCKS BOOST", "tag": "CONFIRMED", "src": "EXCHANGES", "art": "chart"},
    {"num": 13, "region": "MIDDLE EAST", "field": "SOCIETY",
     "head": "PUGH SWIMS WAR-HIT HORMUZ",
     "cap": "A SWIM FOR THE SEA", "tag": "CONFIRMED", "src": "REPORTS", "art": "swim"},
    {"num": 14, "region": "EUROPE", "field": "SOCIETY",
     "head": "THOUSANDS MARCH IN ISTANBUL",
     "cap": "AGAINST TV SEIZURE", "tag": "CONFIRMED", "src": "REPORTS", "art": "crowd"},
]

BRIEFS = [
    ("Bahrain seeks UN action, payment from Iran", "MIDDLE EAST", "DIPLOMACY"),
    ("IRGC: 4th US drone shot down in 24 hours", "MIDDLE EAST", "CONFLICT"),
    ("Iran unveils underground 'missile city'", "MIDDLE EAST", "CONFLICT"),
    ("14+ Iran tankers mass at Kharg; convoy unproven", "MIDDLE EAST", "CONFLICT"),
    ("Trump says Iran wants a deal", "N. AMERICA", "DIPLOMACY"),
    ("Saudi Arabia, Yemen Houthis trade fire", "MIDDLE EAST", "CONFLICT"),
    ("Israeli forces kill 2 in Gaza", "MIDDLE EAST", "CONFLICT"),
    ("UN weapons talks end with no binding ban", "EUROPE", "DIPLOMACY"),
    ("90+ nations sign COP31 electrification pledge", "EUROPE", "CLIMATE"),
    ("Saudi blamed for blocking fossil-fuel text", "EUROPE", "CLIMATE"),
    ("Australia: calls for minister Bowen to quit", "ASIA-PACIFIC", "CLIMATE"),
    ("Pacific islands voice despair at COP failure", "ASIA-PACIFIC", "CLIMATE"),
    ("White House removes cyber chief Cairncross", "N. AMERICA", "SOCIETY"),
    ("ICE protest at Seattle airport; march in Gilroy", "N. AMERICA", "SOCIETY"),
    ("Army to detonate lead azide despite court order", "N. AMERICA", "CONFLICT"),
    ("Taiwan warns Canada over deeper China ties", "ASIA-PACIFIC", "DIPLOMACY"),
    ("India youth wing protests at Meta offices", "S. ASIA", "SOCIETY"),
    ("Lowy index: US lead over China narrowing", "ASIA-PACIFIC", "ECONOMY"),
    ("China chipmakers CXMT, YMTC gain ground", "ASIA-PACIFIC", "TECH"),
    ("China-Japan ties worsen over Taiwan, minerals", "ASIA-PACIFIC", "DIPLOMACY"),
    ("Mlambo-Ngcuka, ex-UN Women chief, dies at 71", "AFRICA", "SOCIETY"),
    ("NFL: Lions 31-21 Bucs, sixth straight win", "N. AMERICA", "SPORT"),
    ("NFL: Bears 21-13 Saints; Cowboys 51-30 Titans", "N. AMERICA", "SPORT"),
    ("NFL: 49ers 35-10 Vikings in Mexico City", "N. AMERICA", "SPORT"),
    ("NFL: Chiefs 34-7 Cards; Bills 26-9 Dolphins", "N. AMERICA", "SPORT"),
    ("NFL: Panthers 35-33 Ravens; Eagles 19-16 Steelers", "N. AMERICA", "SPORT"),
    ("NFL: Jets end skid 27-24; Herbert concussed", "N. AMERICA", "SPORT"),
    ("Montana State top seed in FCS playoff bracket", "N. AMERICA", "SPORT"),
    ("Odesa power grid crippled by Russian strikes", "EUROPE", "CONFLICT"),
    ("Zelenskyy: 2,700 drones in a week on Ukraine", "EUROPE", "CONFLICT"),
    ("EU rejects COP31 text with no fossil fuels", "EUROPE", "CLIMATE"),
    ("US stayed out of COP31 after Trump pullout", "N. AMERICA", "CLIMATE"),
]

NUMBERS = [
    ("0", "COP31 DEAL REACHED"),
    ("$450M", "SKUBAL METS DEAL"),
    ("34", "MISSING IN FACTORY FIRE"),
    ("24", "DEAD IN NIGERIA BOAT"),
    ("186", "DRONES AT UKRAINE OVERNIGHT"),
    ("3", "KH-101 MISSILES IN POLAND"),
]

TIMELINE = [
    ("00:30", "DRONE HITS DYMER FLATS"),
    ("13:00", "COP31 FINAL PLENARY OPENS"),
    ("15:00", "POLAND CONFIRMS KH-101S"),
    ("16:00", "LIVERPOOL 4-0 MAN UTD"),
    ("19:10", "IRAN: TANKERS HIT MINES"),
    ("22:21", "SKUBAL $450M DEAL REPORTED"),
    ("23:00", "NFL SUNDAY FINALS IN"),
]

EXCLUDED = [
    ("Shenzhen summit", "19 NOV"),
    ("ICJ Myanmar ruling", "19 NOV"),
    ("EU-Indonesia deal", "21 NOV"),
    ("Kryvyi Rih strike", "20 NOV"),
    ("First Hormuz strikes", "21 NOV"),
    ("Poland incursion", "20 NOV"),
    ("Bayer $7.25B ruling", "20 NOV"),
    ("Riemann proof claim", "20 NOV"),
    ("S&P 500 correction", "20 NOV"),
    ("Mexico cartel capture", "21 NOV"),
]

# pins: story number, longitude, latitude
PINS = [
    (1, 30.7, 36.9, 9, 9), (2, 56.5, 26.5, 11, 7), (3, 30.3, 50.8, 9, -9),
    (4, 22.0, 51.0, -11, -7), (5, 106.3, -6.2, 0, 0), (6, 8.0, 9.0, 0, 0),
    (7, 20.1, 32.1, -9, 11), (8, -3.0, 53.4, 0, 0), (9, -74.0, 40.7, 0, 0),
    (10, 29.0, 41.0, -11, -11),
]

WORLD = [
    "....#####........#####....................##########..........",
    "..##########......######..................#############......",
    ".############.....#######..................##############....",
    "..##########.......######....####...........############......",
    "...########........#######.######..........###########.......",
    "....######..........############............##########.......",
    ".....####............##########..............########........",
    "......##.............##########.....##........######..........",
    "......##..............########....####........#####...........",
    ".....###...............######....######.......####............",
    "....####.................####....#######......###.............",
    "....###...........................######......##..............",
    "...##..............................####......................",
    "..##................................##......................",
    "..#..................................#......................",
    ".##..................................##......##..............",
    ".###..................................##....####.............",
    "..##...................................#####................",
    "..#.....................................###................",
    ".##......................................#.................",
    ".#............................................................",
]


# ---- flat illustrations -------------------------------------------------
def art_climate(x, y, w, h):
    rect(x, y, w, h, SKY)
    circle(x + w - 34, y + 26, 16, GOLD)
    for a in range(0, 360, 45):
        import math as _m
        r0 = 20
        r1 = 26
        x0 = x + w - 34 + int(r0 * _m.cos(_m.radians(a)))
        y0 = y + 26 + int(r0 * _m.sin(_m.radians(a)))
        x1 = x + w - 34 + int(r1 * _m.cos(_m.radians(a)))
        y1 = y + 26 + int(r1 * _m.sin(_m.radians(a)))
        line(x0, y0, x1, y1, GOLD)
    circle(x + 40, y + h - 22, 20, TEAL)
    poly([(x + 20, y + h - 22), (x + 34, y + h - 6), (x + 46, y + h - 22),
          (x + 60, y + h - 22)], TEAL)
    rect(x + 14, y + h - 34, 12, 34, INK)
    rect(x + 30, y + h - 44, 12, 44, INK)
    rect(x + 46, y + h - 28, 12, 28, INK)
    circle(x + 20, y + h - 40, 5, SMOKE)
    circle(x + 36, y + h - 50, 6, SMOKE)


def art_tanker(x, y, w, h):
    rect(x, y, w, h, SKY)
    rect(x, y + h - 26, w, 26, SEA)
    for k in range(4):
        wx = x + 8 + k * 26
        poly([(wx, y + h - 26), (wx + 8, y + h - 32), (wx + 16, y + h - 26),
              (wx + 24, y + h - 20), (wx + 32, y + h - 26)], (255, 255, 255))
    poly([(x + 18, y + h - 40), (x + w - 30, y + h - 40), (x + w - 18, y + h - 26),
          (x + 18, y + h - 26)], INK)
    rect(x + w - 62, y + h - 62, 26, 22, RED)
    rect(x + w - 56, y + h - 72, 14, 10, RED)
    circle(x + 26, y + 22, 7, INK)
    for a in (45, 135, 225, 315):
        import math as _m
        line(x + 26 + int(7 * _m.cos(_m.radians(a))),
             y + 22 + int(7 * _m.sin(_m.radians(a))),
             x + 26 + int(12 * _m.cos(_m.radians(a))),
             y + 22 + int(12 * _m.sin(_m.radians(a))), INK)


def art_kyiv(x, y, w, h):
    rect(x, y, w, h, SKY)
    rect(x + 16, y + 14, 46, h - 14, (196, 188, 168))
    for r in range(4):
        for c in range(3):
            rect(x + 22 + c * 14, y + 20 + r * 13, 8, 8, GOLD)
    poly([(x + 62, y + 14), (x + 92, y + 30), (x + 78, y + 44), (x + 96, y + 58),
          (x + 62, y + h)], (120, 112, 96))
    circle(x + 78, y + 22, 6, SMOKE)
    circle(x + 88, y + 14, 5, SMOKE)
    line(x + w - 34, y + 16, x + w - 22, y + 16, INK)
    line(x + w - 28, y + 10, x + w - 28, y + 22, INK)
    circle(x + w - 28, y + 16, 3, INK)


def icon(x, y, kind, c):
    """Small 22x22 pictogram for a card."""
    if kind == "missile":
        poly([(x + 2, y + 14), (x + 18, y + 6), (x + 20, y + 10), (x + 4, y + 18)], c)
        poly([(x + 2, y + 16), (x + 6, y + 20), (x + 8, y + 16)], GOLD)
    elif kind == "flame":
        poly([(x + 11, y + 2), (x + 18, y + 12), (x + 15, y + 19), (x + 7, y + 19),
              (x + 4, y + 12)], c)
        circle(x + 11, y + 15, 3, GOLD)
    elif kind == "boat":
        poly([(x + 2, y + 12), (x + 20, y + 12), (x + 17, y + 19), (x + 5, y + 19)], c)
        line(x + 11, y + 12, x + 11, y + 3, c)
        poly([(x + 11, y + 3), (x + 19, y + 11), (x + 11, y + 11)], RED)
    elif kind == "baseball":
        circle(x + 11, y + 11, 9, WHITE)
        ring(x + 11, y + 11, 9, c, 1)
        line(x + 5, y + 4, x + 9, y + 8, RED)
        line(x + 17, y + 14, x + 13, y + 18, RED)
    elif kind == "soccer":
        circle(x + 11, y + 11, 9, WHITE)
        ring(x + 11, y + 11, 9, c, 1)
        poly([(x + 11, y + 6), (x + 16, y + 10), (x + 14, y + 16), (x + 8, y + 16),
              (x + 6, y + 10)], INK)
    elif kind == "house":
        poly([(x + 2, y + 11), (x + 11, y + 3), (x + 20, y + 11)], c)
        rect(x + 5, y + 11, 12, 9, c)
        poly([(x + 9, y + 2), (x + 13, y + 8), (x + 8, y + 8)], GOLD)
    elif kind == "chip":
        rect(x + 6, y + 6, 10, 10, c)
        for k in range(3):
            hline(x + 2, y + 8 + k * 4, 4, c)
            hline(x + 16, y + 8 + k * 4, 4, c)
            vline(x + 8 + k * 4, y + 2, 4, c)
            vline(x + 8 + k * 4, y + 16, 4, c)
    elif kind == "ship":
        poly([(x + 2, y + 13), (x + 20, y + 13), (x + 17, y + 19), (x + 5, y + 19)], c)
        rect(x + 8, y + 6, 7, 7, c)
        circle(x + 16, y + 4, 3, SMOKE)
    elif kind == "chart":
        rect(x + 3, y + 14, 4, 6, c)
        rect(x + 9, y + 10, 4, 10, c)
        rect(x + 15, y + 5, 4, 15, TEAL)
    elif kind == "swim":
        circle(x + 11, y + 6, 4, c)
        line(x + 3, y + 13, x + 19, y + 13, c)
        line(x + 5, y + 17, x + 17, y + 17, SEA)
        line(x + 7, y + 20, x + 15, y + 20, SEA)
    elif kind == "crowd":
        circle(x + 6, y + 6, 3, c)
        circle(x + 11, y + 4, 3, c)
        circle(x + 16, y + 6, 3, c)
        rect(x + 2, y + 10, 7, 9, c)
        rect(x + 8, y + 8, 7, 11, RED)
        rect(x + 15, y + 10, 7, 9, c)

# ---- layout -------------------------------------------------------------
MX = 16
CW = W - 2 * MX

ALL_STORIES = LEADS + CARDS + [(t, r, f) for (t, r, f) in BRIEFS]
REGIONS = Counter()
FIELDS = Counter()
for s in LEADS + CARDS:
    REGIONS[s["region"]] += 1
    FIELDS[s["field"]] += 1
for (_t, r, f) in BRIEFS:
    REGIONS[r] += 1
    FIELDS[f] += 1
TOTAL = len(LEADS) + len(CARDS) + len(BRIEFS)
assert TOTAL == 46, TOTAL
assert len(REGIONS) == 7, REGIONS
assert len(FIELDS) == 8, FIELDS


def rule(y, c=INK, t=2):
    hline(MX, y, CW, c, t)


def draw_header():
    draw_text(W // 2, 12, "THE WORLD'S NEWS OF ONE DAY", 2, RED, align="center")
    draw_text(W // 2, 34, "%d STORIES · %d REGIONS · %d FIELDS" % (
        TOTAL, len(REGIONS), len(FIELDS)), 2, INK, align="center")
    draw_text(W // 2, 56, "SUNDAY 22 NOVEMBER 2026", 6, INK,
              align="center")
    draw_text(W // 2, 106,
              "ONE DAY IN THREE LAYERS: 3 LEADS · 11 PICTURES · 32 BRIEFS",
              2, MUTED, align="center")
    chips = []
    order = ["N. AMERICA", "EUROPE", "MIDDLE EAST", "ASIA-PACIFIC",
             "AFRICA", "S. ASIA", "SE ASIA"]
    for r in order:
        chips.append("%s %d" % (r, REGIONS[r]))
    widths = [text_w(c, 1) + 16 for c in chips]
    total_w = sum(widths) + 6 * (len(chips) - 1)
    x = (W - total_w) // 2
    y = 126
    for c, w in zip(chips, widths):
        rect(x, y, w, 18, PAPER2)
        rect(x, y, w, 18, LINEC) if False else None
        hline(x, y, w, NAVY, 2)
        draw_text(x + 8, y + 5, c, 1, NAVY)
        x += w + 6
    rule(150)


def draw_timeline():
    y0 = 154
    rect(0, y0, W, 46, NAVY)
    draw_text(MX, y0 + 8, "THE DAY", 2, WHITE)
    draw_text(MX, y0 + 24, "IN UTC", 2, GOLD)
    cell_w = (W - MX - 120) // 7
    x = MX + 120
    for (t, label) in TIMELINE:
        draw_text(x, y0 + 5, t, 2, GOLD)
        for i, ln in enumerate(wrap(label, cell_w - 8, 1)):
            draw_text(x, y0 + 21 + i * 9, ln, 1, WHITE)
        x += cell_w


def draw_leads():
    y0 = 206
    col_w = 320
    xs = [MX, MX + 336, MX + 672]
    arts = {"climate": art_climate, "tanker": art_tanker, "kyiv": art_kyiv}
    for (lead, x) in zip(LEADS, xs):
        arts[lead["art"]](x, y0, col_w, 64)
        draw_text(x, y0 + 72, "%d · %s · %s" % (
            lead["num"], lead["region"], lead["field"]), 1, RED)
        hy = y0 + 86
        lines = wrap(lead["head"], col_w, 3)
        for i, ln in enumerate(lines[:2]):
            draw_text(x, hy + i * 24, ln, 3, INK)
        dy = hy + 24 * len(lines[:2]) + 4
        deck = " ".join(lead["deck"].split())
        for i, ln in enumerate(wrap(deck, col_w, 1)):
            draw_text(x, dy + i * 9, ln, 1, MUTED)
        draw_text(x, y0 + 184, "%s · %s" % (lead["tag"], lead["src"]), 1, MUTED)
    rule(398)


def draw_numbers():
    y0 = 402
    rect(0, y0, W, 46, PAPER2)
    cell_w = W // 6
    for i, (big, label) in enumerate(NUMBERS):
        x = i * cell_w
        draw_text(x + cell_w // 2, y0 + 5, big, 4, RED, align="center")
        for j, ln in enumerate(wrap(label, cell_w - 16, 1)):
            draw_text(x + cell_w // 2, y0 + 33 + j * 8, ln, 1, INK,
                      align="center")
    hline(0, y0 + 46, W, INK, 2)


def draw_cards():
    y0 = 452
    card_w = 239
    card_h = 72
    rows = [CARDS[0:4], CARDS[4:8], CARDS[8:11]]
    for ri, row in enumerate(rows):
        y = y0 + ri * (card_h + 6)
        for ci, card in enumerate(row):
            x = MX + ci * (card_w + 12)
            rect(x, y, card_w, card_h, WHITE)
            hline(x, y, card_w, RED, 2)
            rect(x + 6, y + 4, 18, 18, RED)
            draw_text(x + 15, y + 9, str(card["num"]), 1, WHITE,
                      align="center")
            icon(x + 30, y + 4, card["art"], NAVY)
            draw_text(x + 58, y + 9, "%s · %s" % (
                card["region"], card["field"]), 1, MUTED)
            for i, ln in enumerate(wrap(card["head"], card_w - 12, 2)[:2]):
                draw_text(x + 6, y + 26 + i * 17, ln, 2, INK)
            draw_text(x + 6, y + 61, "%s · %s · %s" % (
                card["cap"], card["tag"], card["src"]), 1, MUTED)


def draw_map_briefs():
    y0 = 686
    draw_text(MX, y0, "WHERE IT HAPPENED", 2, INK)
    map_x, map_y, map_w, map_h = MX, y0 + 22, 320, 176
    rows = len(WORLD)
    cols = len(WORLD[0])
    for r, row in enumerate(WORLD):
        for c, ch in enumerate(row):
            if ch == '#':
                px(map_x + c * map_w // cols + 2, map_y + r * map_h // rows + 3,
                   TEAL)
                px(map_x + c * map_w // cols + 3, map_y + r * map_h // rows + 3,
                   TEAL)
    for (num, lon, lat, dx, dy) in PINS:
        px0 = map_x + int((lon + 180.0) / 360.0 * map_w) + dx
        py0 = map_y + int((75.0 - lat) / 130.0 * map_h) + dy
        circle(px0, py0, 8, RED)
        circle(px0, py0, 7, WHITE)
        circle(px0, py0, 6, RED)
        draw_text(px0, py0 - 3, str(num), 1, WHITE, align="center")
    bx = 368
    draw_text(bx, y0, "ALSO ON SUNDAY 22 NOVEMBER", 2, INK)
    col_w = 316
    for i, (text, _r, _f) in enumerate(BRIEFS):
        col = i // 16
        row = i % 16
        x = bx + col * (col_w + 8)
        y = y0 + 22 + row * 11
        draw_text(x, y, "%d. %s" % (15 + i, text), 1, INK)


def draw_checks():
    y0 = 890
    rule(y0)
    y0 += 8
    draw_text(MX, y0, "DATE CHECK: LEFT OUT - OLDER NEWS", 1, RED)
    draw_text(592, y0, "HOW SURE ARE WE?", 1, RED)
    for i, (text, date) in enumerate(EXCLUDED):
        col = i // 5
        row = i % 5
        draw_text(MX + col * 280, y0 + 14 + row * 11,
                  "%s - %s" % (text, date), 1, MUTED)
    legend = [
        "CONFIRMED - 2+ OUTLETS AGREE",
        "OFFICIAL - THE BODY ITSELF",
        "REPORTED - ONE OUTLET",
        "CLAIM - ONE SIDE'S WORD",
        "FORECAST - EXPECTED, NOT DONE",
    ]
    for i, ln in enumerate(legend):
        draw_text(592, y0 + 14 + i * 11, ln, 1, MUTED)


def draw_footer():
    y0 = 972
    rule(y0)
    draw_text(W // 2, y0 + 10,
              "EVERY STORY HERE HAPPENED, OR WAS FIRST REPORTED, ON SUNDAY "
              "22 NOVEMBER 2026. CLAIMS ARE ATTRIBUTED.", 1, INK,
              align="center")
    draw_text(W // 2, y0 + 24,
              "SOURCES: REUTERS, AP, CNN, LE MONDE, WSJ, NBC SPORTS, "
              "AL JAZEERA, AFP, UKMTO, TASNIM, LOWY INSTITUTE.", 1, MUTED,
              align="center")
    draw_text(W // 2, y0 + 38, "46 STORIES · SUNDAY 22 NOVEMBER 2026 · "
              "ONE DAY, ONE PAGE", 1, RED, align="center")


def main():
    draw_header()
    draw_timeline()
    draw_leads()
    draw_numbers()
    draw_cards()
    draw_map_briefs()
    draw_checks()
    draw_footer()
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
