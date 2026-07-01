#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -e . pyinstaller pillow
python3 scripts/create_icon.py
python3 -m PyInstaller packaging/typozap.spec --clean --noconfirm

rm -f dist/TypoZap.dmg
hdiutil create -volname TypoZap -srcfolder dist/TypoZap.app -ov -format UDZO dist/TypoZap.dmg
echo "Application créée : dist/TypoZap.dmg"
