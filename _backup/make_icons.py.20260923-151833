# -*- coding: utf-8 -*-
"""Home-screen icons for the installed app (iPhone: Add to Home Screen).

Her own covers, as souls-reader's icon is its cover: the three books side by
side, each scaled to the icon's full height and cut to a third of its width
around the middle, where the dancers are. The first icon was 舞 in red on
black, dropped because it looked like any app; this one says Bomboy.

The icons are the one thing served in the clear, and a cover is on every
bookshop page anyway, so nothing of the text leaks.

    python scripts/make_icons.py
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'icons'
SHELF = ['pas', 'win', 'pie']
GAP = 0.012                  # a hairline of black between the books, as fraction of n
BG = (11, 11, 13)


def mark(n):
    s = 4                                    # draw big, shrink: smooth edges
    N = n * s
    im = Image.new('RGB', (N, N), BG)
    gap = round(N * GAP)
    w = (N - 2 * gap) // 3
    for i, slug in enumerate(SHELF):
        c = Image.open(ROOT / 'public' / f'cover-{slug}.jpg').convert('RGB')
        c = c.resize((round(c.width * N / c.height), N), Image.LANCZOS)
        x0 = (c.width - w) // 2
        im.paste(c.crop((x0, 0, x0 + w, N)), (i * (w + gap), 0))
    return im.resize((n, n), Image.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
for n in (180, 192, 512):
    mark(n).save(OUT / f'icon-{n}.png')
print('wrote', ', '.join(f'icon-{n}.png' for n in (180, 192, 512)))
