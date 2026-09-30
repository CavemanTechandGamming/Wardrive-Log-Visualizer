#!/usr/bin/env python3
"""
Generate a Windows .ico (including 256px) from the repo PNG.

Used by scripts/build_app.bat before running PyInstaller with --icon.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def generate_ico(png_path: Path, ico_path: Path) -> None:
    img = Image.open(png_path).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(ico_path, format="ICO", sizes=sizes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input PNG path")
    ap.add_argument("--output", required=True, help="Output ICO path")
    args = ap.parse_args()

    png_path = Path(args.input)
    ico_path = Path(args.output)

    if not png_path.exists():
        raise SystemExit(f"Input PNG not found: {png_path}")

    generate_ico(png_path, ico_path)
    print(f"Generated: {ico_path}")


if __name__ == "__main__":
    main()
