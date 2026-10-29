"""生成 macOS 应用图标 assets/icon.icns（无第三方设计依赖）。"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

CANVAS = 1024
SUPERSAMPLE = 4
ICON_INSET = 72
ICON_RADIUS = 200

BACKGROUND_TOP = (14, 27, 42)
BACKGROUND_BOTTOM = (8, 56, 72)
GRID_COLOR = (255, 255, 255, 26)
AXIS_COLOR = (255, 255, 255, 150)
CURVE_COLOR = (56, 225, 214, 255)
MARKER_COLOR = (124, 255, 155, 255)

ICONSET_SIZES = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


def vertical_gradient(
    width: int,
    height: int,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    column = Image.new("RGB", (1, height))
    for y in range(height):
        ratio = y / max(1, height - 1)
        column.putpixel(
            (0, y),
            tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom, strict=True)),
        )
    return column.resize((width, height))


def curve_points(width: int, height: int, steps: int = 220) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    left, right = width * 0.20, width * 0.80
    top, bottom = height * 0.24, height * 0.76
    for i in range(steps + 1):
        t = i / steps
        x = left + (right - left) * t
        envelope = math.sin(math.pi * t) ** 0.85
        y = bottom - (bottom - top) * (0.18 + 0.82 * t) - envelope * height * 0.10
        points.append((x, y))
    return points


def build_icon() -> Image.Image:
    size = CANVAS * SUPERSAMPLE
    inset = ICON_INSET * SUPERSAMPLE
    radius = ICON_RADIUS * SUPERSAMPLE

    background = vertical_gradient(size, size, BACKGROUND_TOP, BACKGROUND_BOTTOM)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inset, inset, size - inset, size - inset), radius=radius, fill=255
    )
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(background.convert("RGBA"), (0, 0), mask)

    # 网格
    grid = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    step = 96 * SUPERSAMPLE
    for x in range(inset + step, size - inset, step):
        grid_draw.line((x, inset, x, size - inset), fill=GRID_COLOR, width=2 * SUPERSAMPLE)
    for y in range(inset + step, size - inset, step):
        grid_draw.line((inset, y, size - inset, y), fill=GRID_COLOR, width=2 * SUPERSAMPLE)
    icon.alpha_composite(Image.composite(grid, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    axis_draw = ImageDraw.Draw(icon)
    axis_left = int(size * 0.20)
    axis_bottom = int(size * 0.80)
    axis_width = 6 * SUPERSAMPLE
    axis_draw.line(
        (axis_left, int(size * 0.18), axis_left, axis_bottom),
        fill=AXIS_COLOR,
        width=axis_width,
    )
    axis_draw.line(
        (axis_left, axis_bottom, int(size * 0.84), axis_bottom),
        fill=AXIS_COLOR,
        width=axis_width,
    )

    # 曲线光晕 + 主体
    points = curve_points(size, size)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(
        points, fill=(56, 225, 214, 160), width=18 * SUPERSAMPLE, joint="curve"
    )
    icon.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16 * SUPERSAMPLE)))
    ImageDraw.Draw(icon).line(
        points, fill=CURVE_COLOR, width=9 * SUPERSAMPLE, joint="curve"
    )

    # 定标点
    marker_draw = ImageDraw.Draw(icon)
    for index in (0, len(points) // 2, len(points) - 1):
        x, y = points[index]
        r = 13 * SUPERSAMPLE
        marker_draw.ellipse((x - r, y - r, x + r, y + r), fill=MARKER_COLOR)
        marker_draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(8, 30, 34, 255),
            width=3 * SUPERSAMPLE,
        )

    return icon.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    assets = project_root / "assets"
    iconset = assets / "icon.iconset"
    assets.mkdir(parents=True, exist_ok=True)
    iconset.mkdir(parents=True, exist_ok=True)

    icon = build_icon()
    png_path = assets / "icon.png"
    icon.save(png_path)

    for filename, dimension in ICONSET_SIZES:
        icon.resize((dimension, dimension), Image.Resampling.LANCZOS).save(
            iconset / filename
        )

    icns_path = assets / "icon.icns"
    try:
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"iconutil 生成 .icns 失败，将使用 PNG: {error}", file=sys.stderr)
        return 1

    print(f"生成图标: {png_path}\n生成图标: {icns_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
