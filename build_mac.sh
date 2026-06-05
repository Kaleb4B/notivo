#!/bin/bash
echo "Mem-build aplikasi Notivo untuk macOS..."

# Pastikan menggunakan path pyinstaller yang sesuai (berada di ~/.local/bin atau ~/Library/Python/3.9/bin)
/Users/macpro-kalebdap/Library/Python/3.9/bin/pyinstaller --name "Notivo" \
--windowed \
--icon "assets/logo.icns" \
--add-data "assets:assets" \
--add-data "ui:ui" \
--add-data "audio:audio" \
--add-data "transcription:transcription" \
--add-data "summary:summary" \
--add-data "utils:utils" \
--add-data "storage:storage" \
--add-data "models:models" \
--hidden-import "markdown" \
--hidden-import "speech_recognition" \
--hidden-import "PySide6" \
--noconfirm app.py

echo "Selesai! Aplikasi macOS 'Notivo.app' telah dibuat di dalam folder 'dist/'."
