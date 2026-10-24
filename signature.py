#!/usr/bin/env python3
"""Make light/dark signature variants for the README.

Source is black ink on a transparent 1024px canvas. We crop to the ink,
tint the RGB while keeping the alpha, and export at 2x display size.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SRC = os.path.join(ASSETS, "signature black.png")

DISPLAY_W = 150          # shown at 150px wide in the README
SCALE = 2                # export at 2x so it stays crisp on retina
PAD = 12                 # breathing room around the ink, in source pixels

TARGETS = {
    "signature-light.png": (31, 35, 40),     # near-black ink, for light mode
    "signature-dark.png": (255, 210, 30),    # blonde, matches the theme accents
}


def main():
    src = Image.open(SRC).convert("RGBA")
    bbox = src.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit("source signature has no ink")

    left = max(0, bbox[0] - PAD)
    top = max(0, bbox[1] - PAD)
    right = min(src.width, bbox[2] + PAD)
    bottom = min(src.height, bbox[3] + PAD)
    ink = src.crop((left, top, right, bottom))
    print(f"cropped to {ink.size}")

    out_w = DISPLAY_W * SCALE
    out_h = round(ink.height * out_w / ink.width)
    resized = ink.resize((out_w, out_h), Image.LANCZOS)
    alpha = resized.getchannel("A")
    print(f"export size {resized.size}")

    for name, rgb in TARGETS.items():
        variant = Image.new("RGBA", resized.size, rgb + (0,))
        variant.putalpha(alpha)
        path = os.path.join(ASSETS, name)
        variant.save(path, optimize=True)
        print(f"{name}: {os.path.getsize(path) // 1024} KB")

    # preview strip: signature on both backgrounds so it can be eyeballed
    gap, margin = 24, 20
    w = margin * 2 + out_w * 2 + gap
    h = margin * 2 + out_h
    strip = Image.new("RGB", (w, h), (13, 17, 23))
    strip.paste((255, 255, 255), (w // 2 + gap // 2, 0, w, h))
    dark = Image.open(os.path.join(ASSETS, "signature-dark.png"))
    light = Image.open(os.path.join(ASSETS, "signature-light.png"))
    strip.paste(dark, (margin, margin), dark)
    strip.paste(light, (w // 2 + gap // 2 + margin, margin), light)
    strip = strip.resize((w * 2, h * 2), Image.NEAREST)
    strip.save(os.path.join(HERE, "signature_preview.png"))
    print("preview written")


if __name__ == "__main__":
    main()
