# Notivo

Record. Transcribe. Summarize.
Notivo is a cross-platform desktop application built with PySide6 for real-time transcription and AI-powered meeting summaries without relying on cloud services.

## Features
- Real-time transcription using `faster-whisper` and `silero-vad`.
- Offline local AI summary generation using Ollama.
- Saves sessions entirely locally.
- Cross-platform: Windows, macOS, Linux.

## Requirements
- Python 3.12+
- Local installation of [Ollama](https://ollama.com/) with at least one model (`llama3.2`, `gemma3`, or `mistral`) installed.
- System microphone access.

## Installation
1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure Ollama is running in the background.

## Running the Application
```bash
python app.py
```

## Build Instructions
To package the application into a standalone executable using PyInstaller:
```bash
pip install pyinstaller
pyinstaller --name "Notivo" --windowed --icon=assets/logo.png app.py
```
