#!/bin/bash
pyinstaller --onefile --console --name Atlas --add-data "atlas:atlas" atlas/main.py
echo "Done. Executable is in dist/Atlas"
