#!/usr/bin/env python3
"""
Generate a temporary placeholder icon set under ``assets/``.

Replace these files with the real brand icon when one is designed.
Build scripts and the window expect:

- ``assets/wardrive-log-visualizer-icon.png`` (master, square)
- ``assets/wardrive-log-visualizer-icon-256.png``
- ``assets/WardriveLogVisualizer.ico``
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MASTER = ASSETS / "wardrive-log-visualizer-icon.png"
PNG_256 = ASSETS / "wardrive-log-visualizer-icon-256.png"
ICO = ASSETS / "WardriveLogVisualizer.ico"


def _draw_placeholder(size: int) -> Image.Image:
    """Simple dark square with a map pin — temporary until a real icon exists."""

    img = Image.new("RGBA", (size, size), (20, 20, 24, 255))
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad),
        radius=size // 10,
        outline=(126, 182, 255, 255),
        width=max(2, size // 64),
    )
    # Pin head
    cx, cy = size // 2, size * 38 // 100
    r = size // 7
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(126, 182, 255, 255))
    hole = r // 3
    draw.ellipse(
        (cx - hole, cy - hole, cx + hole, cy + hole),
        fill=(20, 20, 24, 255),
    )
    # Pin tip
    tip_y = size * 78 // 100
    draw.polygon(
        [(cx - r * 3 // 4, cy + r // 2), (cx + r * 3 // 4, cy + r // 2), (cx, tip_y)],
        fill=(126, 182, 255, 255),
    )
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    master = _draw_placeholder(512)
    master.save(MASTER, format="PNG")
    master.resize((256, 256), Image.Resampling.LANCZOS).save(PNG_256, format="PNG")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save(ICO, format="ICO", sizes=sizes)
    print(f"Wrote {MASTER}")
    print(f"Wrote {PNG_256}")
    print(f"Wrote {ICO}")
    print("Placeholder only — replace when the real icon is ready.")


if __name__ == "__main__":
    main()
