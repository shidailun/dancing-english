# -*- coding: utf-8 -*-
"""Home-screen icons for the installed app (iPhone: Add to Home Screen).

One character, 舞 (dance), in the accent colour on the page's black: the same
mark as the favicon in index.html. Deliberately not a book cover: icons are
served in the clear, the covers are the publisher's, and there are three of
them. 舞 is written the same way in Simplified and Traditional, so the Noto
Serif TC already on this machine draws it correctly.

    python scripts/make_icons.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'public' / 'icons'
FONT = 'C:/Windows/Fonts/NotoSerifTC-VF.ttf'
BG, HOT = (11, 11, 13), (232, 80, 58)


def mark(n):
    s = 4                                    # draw big, shrink: smooth edges
    im = Image.new('RGB', (n * s, n * s), BG)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, int(n * s * .66))
    d.text((n * s / 2, n * s / 2), '舞', font=f, fill=HOT, anchor='mm')
    return im.resize((n, n), Image.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
for n in (180, 192, 512):
    mark(n).save(OUT / f'icon-{n}.png')
print('wrote', ', '.join(f'icon-{n}.png' for n in (180, 192, 512)))
