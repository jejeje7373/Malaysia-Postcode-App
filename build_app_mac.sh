\#!/bin/bash
set -e

pip install --upgrade pip
pip install pyinstaller pyside6

pyinstaller \
  --name "Malaysia Postcode Lookup" \
  --windowed \
  --noconfirm \
  --clean \
  --add-data "data/postcodes.json:data" \
  app_qt.py

echo "✅ App built successfully!"
echo "📦 Find it in: dist/Malaysia Postcode Lookup.app"
