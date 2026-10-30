# -*- coding: utf-8 -*-
"""Rounded, semi-transparent bar drawn behind burned-in subtitles over the source subtitle band."""


def write_subtitle_bar(path: str, width: int, height: int, radius: int, alpha: float = 0.7) -> str:
    """Write an RGBA PNG: black at `alpha` opacity with rounded corners; fully transparent outside."""
    from PIL import Image, ImageDraw

    width = max(2, int(width))
    height = max(2, int(height))
    radius = max(0, min(int(radius), min(width, height) // 2))
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, width - 1, height - 1], radius=radius, fill=(0, 0, 0, int(round(255 * alpha))))
    img.save(path)
    return path
