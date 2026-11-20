"""The ninja monkey, drawn with half blocks: two pixels per terminal cell. No I/O.

Pixels: X fur, S face, E eyes and mouth, H headband (the belt color), D sparkle.
"""

SPRITE = (
    "....XXXXXX..HH..",
    "..HHHHHHHHHHH...",
    "XXXSSSSSSSSXXX..",
    "XSXXSSSSSSXXSX..",
    "XXXSSSSSSSSXXX..",
    ".XXSSSSSSSSXX...",
    "..XXSSSSSSXX....",
    "....XXXXXX......",
)
WIDTH = len(SPRITE[0])
FACE_WIDTH = 14  # without the headband tails
HEIGHT = len(SPRITE) // 2  # terminal rows

_EYES_OPEN = {(2, 4), (2, 5), (2, 8), (2, 9)}

FACES = {
    "calm": _EYES_OPEN | {(5, 6), (5, 7)},
    "ready": _EYES_OPEN | {(3, 4), (3, 9), (5, 6), (5, 7)},
    "happy": _EYES_OPEN | {(5, 6), (5, 7), (5, 8), (4, 9)},
    "sad": {(2, 5), (2, 8), (3, 5), (3, 8), (5, 5), (5, 6), (5, 7), (5, 8)},
    "cheer": _EYES_OPEN | {(4, 5), (4, 6), (4, 7), (4, 8), (5, 6), (5, 7)},
}
SPARKLES = {"sad": {(1, 14)}, "cheer": {(0, 1), (2, 15)}}

ROLES = {"X": "fur", "S": "face", "E": "eye", "H": "band", "D": "sparkle"}


def pixels(face="calm"):
    grid = [list(row) for row in SPRITE]
    for y, x in FACES[face]:
        grid[y][x] = "E"
    for y, x in SPARKLES.get(face, ()):
        grid[y][x] = "D"
    return ["".join(row) for row in grid]


def cells(face="calm"):
    """Rows of (top role, bottom role) per terminal cell; None is empty."""
    rows = pixels(face)
    return [[(ROLES.get(a), ROLES.get(b)) for a, b in zip(top, bottom)]
            for top, bottom in zip(rows[::2], rows[1::2])]
