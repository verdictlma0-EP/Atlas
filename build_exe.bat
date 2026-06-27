@echo off
echo Building Atlas.exe with PyInstaller...
pyinstaller --onefile --console --name Atlas --add-data "atlas;atlas" atlas/main.py
echo Done. Executable is in dist\Atlas.exe
pause
