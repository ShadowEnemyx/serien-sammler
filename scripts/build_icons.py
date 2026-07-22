"""Create native icon containers from the transparent PNG master."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "app-icon.png"
PNG = ROOT / "assets" / "app-icon-1024.png"
ICO = ROOT / "assets" / "app-icon.ico"
ICNS = ROOT / "assets" / "app-icon.icns"


def main() -> None:
    with Image.open(MASTER) as source:
        image = source.convert("RGBA")
        image.thumbnail((900, 900), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((1024 - image.width) // 2, (1024 - image.height) // 2))
        canvas.save(PNG)
        canvas.save(ICO, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        canvas.save(ICNS, format="ICNS")


if __name__ == "__main__":
    main()
