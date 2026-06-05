@echo off
echo Menginstal PyInstaller...
pip install pyinstaller

echo.
echo Mem-build aplikasi Notivo untuk Windows...
pyinstaller --name "Notivo" ^
--windowed ^
--add-data "assets;assets" ^
--add-data "ui;ui" ^
--add-data "audio;audio" ^
--add-data "transcription;transcription" ^
--add-data "summary;summary" ^
--add-data "utils;utils" ^
--add-data "storage;storage" ^
--add-data "models;models" ^
--hidden-import "markdown" ^
--hidden-import "speech_recognition" ^
--hidden-import "PySide6" ^
--noconfirm app.py

echo.
echo Selesai! Aplikasi Notivo berformat .exe sudah ada di dalam folder 'dist/Notivo'.
pause
