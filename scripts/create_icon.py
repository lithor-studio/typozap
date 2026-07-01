"""Génère les icônes Windows et macOS de TypoZap."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

draw.ellipse([10, 10, 246, 246], fill=(255, 193, 7, 255))

lightning = [
    (95, 80), (140, 128), (95, 176), (115, 176), (160, 128), (115, 80)
]
draw.polygon(lightning, fill=(33, 33, 33, 200))

img.save(ROOT / 'icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save(ROOT / 'icon.icns', format='ICNS')
print("Icons created: icon.ico, icon.icns")
