# -*- coding: utf-8 -*-
"""The three books, in shelf order. Every script reads its chapter codes from
here rather than counting chapters itself, which is what souls-reader did with
range(1, 32) scattered through six files.

A chapter code is the book's slug and a two-digit number (pas01, win55, pie32):
unique across the shelf, so one dictionary, one Word Review deck and one audio
folder serve all three books without a clash.

All three epubs come from the same Draft2Digital template: a chapter is an
xhtml file in the spine whose name is chapter-NNN.xhtml, with its title in h1
and its subtitle in h3.
"""

BOOKS = [
    # The Pas de Deux names its chapters after ballet steps and groups them the
    # way a grand pas de deux is built (ENTREE, ADAGIO, the variations, CODA).
    # Those section pages are a sentence each; they go at the head of the
    # chapter that follows them rather than into the chapter list.
    {'slug': 'pas', 'title': 'The Pas de Deux', 'sub': 'A Classical Ballet Romance',
     'zh': '双人舞', 'year': 2018, 'chapters': 27, 'rev': [0.5, 0.556],
     'voice': 'en-US-AriaNeural',
     'sections': ['entree', 'adagio', 'male-variation', 'female-variation',
                  'coda', 'curtain-call']},
    {'slug': 'win', 'title': 'The Winner', 'sub': 'A Ballroom Dance Novel',
     'zh': '赢家', 'year': 2016, 'chapters': 55, 'sections': [], 'rev': [0.5, 0.82],
     'voice': 'en-US-AvaNeural'},
    {'slug': 'pie', 'title': 'The Piece', 'sub': 'A Contemporary Ballet Novel',
     'zh': '舞作', 'year': 2020, 'chapters': 32, 'sections': [], 'rev': [0.21, 0.5],
     'voice': 'en-US-MichelleNeural'},
]
# 'rev' is where the Word Review button sits on each cover, as fractions of
# the cover's width and height: a patch of plain ground on each (between the
# subtitle and the tiara; between "novel" and the author; the black left of the dancer), as
# souls-reader put its button just below the guitar.
# 'voice' is each book's narrator: three women, one per book, so the shelf
# does not sound like one reader doing all three. All en-US because all three
# novels are American. Aria and Michelle are the two voices Microsoft tags for
# novels; Ava, the most expressive, gets the ballroom book.
AUTHOR = 'Erin Bomboy'

BY_SLUG = {b['slug']: b for b in BOOKS}


def codes(slug=None):
    """Every chapter code on the shelf, in reading order; or one book's."""
    return [f"{b['slug']}{n:02d}" for b in BOOKS if slug in (None, b['slug'])
            for n in range(1, b['chapters'] + 1)]


def book_of(code):
    return BY_SLUG[code[:3]]
