# -*- coding: utf-8 -*-
"""Home-screen icons for the installed app (iPhone: Add to Home Screen).

The dancer off The Piece's cover, in arabesque on black.

Third try. The first icon was 舞 in red on black, dropped because it looked
like any app. The second was all three covers side by side, each cut to a
third of the icon's width -- it said Bomboy, but at 180px it said it in three
words cut in half: PAS D DEUX, inne, PIEC. "the icon is awful", 23 Sep, and it
was: nothing legible, and the one thing an icon has to do is be recognised at
the size of a thumbnail on a home screen.

One figure on black reads at that size, and it is the only image on any of the
three covers that reads with no words at all. The tagline in the top right of
the cover is painted out rather than cropped round, because every crop tight
enough to lose it lost her head or her foot: the ground behind it is flat black
(11,12,13, and it varies by 3), so the patch is invisible.

The icons are the one thing served in the clear, and a cover is on every
bookshop page anyway, so nothing of the text leaks.

    python scripts/make_icons.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'icons'
COVER = ROOT / 'public' / 'cover-pie.jpg'    # 800x1200
TAGLINE = (425, 125, 770, 270)               # "WHEN THE DREAM BECOMES A NIGHTMARE"
BOX = (100, 95, 800, 795)                    # square: raised arm down to the supporting knee
BG = (11, 12, 13)                            # the cover's own black, measured behind the tagline


def mark(n):
    im = Image.open(COVER).convert('RGB')
    ImageDraw.Draw(im).rectangle(TAGLINE, fill=BG)
    return im.crop(BOX).resize((n, n), Image.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
for n in (180, 192, 512):
    mark(n).save(OUT / f'icon-{n}.png')
print('wrote', ', '.join(f'icon-{n}.png' for n in (180, 192, 512)))
