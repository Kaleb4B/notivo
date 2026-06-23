import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QWidget, QStackedWidget, QScrollArea, QFrame
)


# ─────────────────────────────────────────────
#  Background worker: runs each setup step
# ─────────────────────────────────────────────
class SetupWorker(QThread):
    step_started  = Signal(str, str)  # (step_id, message)
    step_progress = Signal(str, int)  # (step_id, 0-100)
    step_done     = Signal(str, bool, str)  # (step_id, success, note)
    all_done      = Signal()

    def run(self):
        # ── Step 1: pip packages ────────────────────────────────
        self.step_started.emit("packages", "Installing Python packages...")
        try:
            self.step_progress.emit("packages", 10)
            if getattr(sys, 'frozen', False):
                self.step_progress.emit("packages", 100)
                self.step_done.emit("packages", True, "Bundled (skipped)")
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r",
                     "requirements.txt", "--quiet", "--break-system-packages"],
                    capture_output=True, text=True, timeout=300
                )
                self.step_progress.emit("packages", 100)
                if result.returncode == 0:
                    self.step_done.emit("packages", True, "")
                else:
                    # Critical — can't continue without packages
                    self.step_done.emit("packages", False, result.stderr[:120])
                    return
        except Exception as e:
            self.step_done.emit("packages", False, str(e))
            return

        # ── Step 2: Whisper model ───────────────────────────────
        # Read configured model name (default: tiny)
        whisper_model = "tiny"
        try:
            import json, pathlib
            cfg_path = pathlib.Path.home() / ".notivo" / "config.json"
            if cfg_path.exists():
                whisper_model = json.loads(cfg_path.read_text()).get("whisper_model", "tiny")
        except Exception:
            pass

        self.step_started.emit("whisper", f"Downloading Whisper model ({whisper_model})...")
        try:
            from faster_whisper import WhisperModel
            self.step_progress.emit("whisper", 20)
            model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
            self.step_progress.emit("whisper", 100)
            del model
            self.step_done.emit("whisper", True, f"Model '{whisper_model}' ready")
        except Exception as e:
            self.step_progress.emit("whisper", 100)
            self.step_done.emit("whisper", False, str(e)[:120])
            return # Critical failure, cannot continue

        # ── Step 3: Silero VAD ──────────────────────────────────
        self.step_started.emit("vad", "Downloading Voice Activity Detection model...")
        try:
            import torch
            self.step_progress.emit("vad", 20)
            model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self.step_progress.emit("vad", 100)
            del model
            self.step_done.emit("vad", True, "")
        except Exception as e:
            self.step_progress.emit("vad", 100)
            self.step_done.emit("vad", False, str(e)[:120])
            return # Critical failure, cannot continue

        # ── Step 4: Ollama check & Pull ────────────────────────
        ollama_model = "qwen2.5"
        try:
            cfg_path = pathlib.Path.home() / ".notivo" / "config.json"
            if cfg_path.exists():
                import json
                ollama_model = json.loads(cfg_path.read_text()).get("ollama_model", "qwen2.5")
        except Exception:
            pass

        import requests
        import time
        import urllib.request
        import zipfile
        import os
        import shutil
        
        # Helper to find Ollama CLI
        def get_ollama_cmd():
            if shutil.which("ollama"): return "ollama"
            
            if sys.platform == "win32":
                p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
                if os.path.exists(p): return p
            else:
                paths = ["/Applications/Ollama.app/Contents/Resources/ollama", str(pathlib.Path.home() / "Applications/Ollama.app/Contents/Resources/ollama")]
                for p in paths:
                    if os.path.exists(p): return p
            return None

        # Download progress hook
        def download_progress(count, block_size, total_size):
            if total_size > 0:
                downloaded_mb = (count * block_size) / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                percent = int(count * block_size * 100 / total_size)
                # Keep progress between 10% and 40% for the app download step
                self.step_progress.emit("ollama", 10 + int(percent * 0.3))
                self.step_started.emit("ollama", f"Downloading Ollama app... {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")

        install_requested = getattr(self, "install_ollama_requested", False)
        
        if install_requested:
            self.step_started.emit("ollama", "Downloading Ollama app...")
            self.step_progress.emit("ollama", 10)
            try:
                if sys.platform == "win32":
                    installer_path = pathlib.Path.home() / ".notivo" / "OllamaSetup.exe"
                    urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path, reporthook=download_progress)
                    
                    self.step_started.emit("ollama", "Installing Ollama (Windows)...")
                    self.step_progress.emit("ollama", 45)
                    # Run Windows installer silently
                    subprocess.run([str(installer_path), "/SILENT"], check=True)
                    time.sleep(5)
                else:
                    # macOS
                    zip_path = pathlib.Path.home() / ".notivo" / "ollama-mac.zip"
                    apps_dir = pathlib.Path.home() / "Applications"
                    apps_dir.mkdir(parents=True, exist_ok=True)
                    
                    urllib.request.urlretrieve("https://ollama.com/download/Ollama-darwin.zip", zip_path, reporthook=download_progress)
                    
                    self.step_started.emit("ollama", "Extracting Ollama...")
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(apps_dir)
                        
                    self.step_progress.emit("ollama", 45)
                    
                    bin_path = apps_dir / "Ollama.app" / "Contents" / "MacOS" / "Ollama"
                    os.chmod(bin_path, 0o755)
                    
                    self.step_started.emit("ollama", "Starting Ollama server...")
                    subprocess.run(["open", "-a", str(apps_dir / "Ollama.app")])
                    time.sleep(8)
            except Exception as e:
                self.step_done.emit("ollama", False, f"Install failed: {str(e)[:50]}")
                self.step_progress.emit("ollama", 100)
                return

        self.step_started.emit("ollama", f"Downloading AI model '{ollama_model}' (takes time)...")
        self.step_progress.emit("ollama", 50)
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code == 200:
                cmd = get_ollama_cmd()
                if cmd:
                    # Run ollama pull with real-time output parsing
                    process = subprocess.Popen(
                        [cmd, "pull", ollama_model],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    import re
                    for line in process.stdout:
                        # Try to find percentage and sizes in line, e.g., "pulling 2bada8a74506... 100% ▕██████████████████▏ 4.7 GB / 4.7 GB"
                        match = re.search(r'(\d+)%', line)
                        if match:
                            pct = int(match.group(1))
                            mapped_pct = 50 + int(pct * 0.45)
                            self.step_progress.emit("ollama", mapped_pct)
                            
                            # Grab everything after the percentage and cleanup
                            size_info = line[match.end():].replace('▕', '').replace('▏', '').replace('█', '').strip()
                            self.step_started.emit("ollama", f"Downloading model... {pct}%  {size_info}")
                    
                    process.wait()
                    if process.returncode == 0:
                        self.step_done.emit("ollama", True, f"Ollama & {ollama_model} ready ✓")
                    else:
                        self.step_done.emit("ollama", False, "Model download failed")
                        return # Critical failure
                else:
                    self.step_done.emit("ollama", False, "Ollama running but CLI not found")
            else:
                self.step_done.emit("ollama", False, "Not running — please open Ollama app")
        except Exception:
            self.step_done.emit("ollama", False, "Not found — please open Ollama app")
            
        self.step_progress.emit("ollama", 100)

        # ── Create app directories ──────────────────────────────
        app_dir = pathlib.Path.home() / ".notivo"
        app_dir.mkdir(exist_ok=True)
        sessions_dir = pathlib.Path.home() / "Documents" / "Notivo_Sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        self.all_done.emit()


# ─────────────────────────────────────────────
#  Step row widget
# ─────────────────────────────────────────────
class StepRow(QWidget):
    def __init__(self, icon, title, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(14)

        self.icon_label = QLabel(icon)
        self.icon_label.setFixedWidth(28)
        self.icon_label.setStyleSheet("font-size: 20px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QVBoxLayout()
        right.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #e0e0f0; font-size: 13px; font-weight: 600;")

        self.status_label = QLabel("Waiting...")
        self.status_label.setStyleSheet("color: #606080; font-size: 11px;")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1e1e32; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #6c3ce0, stop:1 #c026d3); border-radius: 3px; }
        """)

        right.addWidget(self.title_label)
        right.addWidget(self.status_label)
        right.addWidget(self.progress)

        layout.addWidget(self.icon_label)
        layout.addLayout(right)

    def set_running(self, msg="Running..."):
        self.icon_label.setText("⏳")
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #a78bfa; font-size: 11px;")

    def set_done(self, note=""):
        self.icon_label.setText("✅")
        self.status_label.setText("Done" if not note else note)
        self.status_label.setStyleSheet("color: #4ade80; font-size: 11px;")
        self.progress.setValue(100)

    def set_warning(self, note=""):
        self.icon_label.setText("⚠️")
        self.status_label.setText(note or "Optional — skipped")
        self.status_label.setStyleSheet("color: #fb923c; font-size: 11px;")
        self.progress.setValue(100)

    def set_error(self, note=""):
        self.icon_label.setText("❌")
        self.status_label.setText(note or "Failed")
        self.status_label.setStyleSheet("color: #f87171; font-size: 11px;")

    def set_progress(self, value):
        self.progress.setValue(value)


# ─────────────────────────────────────────────
#  Main Setup Wizard Dialog
# ─────────────────────────────────────────────
class SetupWizard(QDialog):
    setup_complete = Signal()

    STYLESHEET = """
        QDialog {
            background-color: #0d0d14;
            border-radius: 16px;
        }
        QLabel#heading {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
        }
        QLabel#sub {
            font-size: 13px;
            color: #9090b0;
            line-height: 1.5;
        }
        QPushButton#primaryBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6c3ce0, stop:1 #c026d3);
            color: white;
            border-radius: 12px;
            padding: 12px 32px;
            font-size: 14px;
            font-weight: 700;
            border: none;
        }
        QPushButton#primaryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7c4cf0, stop:1 #d036e3);
        }
        QPushButton#primaryBtn:disabled {
            background: #2a2a42;
            color: #505070;
        }
        QFrame#card {
            background-color: #13131f;
            border-radius: 14px;
            border: 1px solid #1e1e32;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notivo — First-Time Setup")
        self.setFixedSize(520, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(self.STYLESHEET)

        self._build_ui()

    # ── UI Construction ──────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Rounded container card
        container = QWidget()
        container.setObjectName("dialog_bg")
        container.setStyleSheet("""
            QWidget#dialog_bg {
                background-color: #0d0d14;
                border-radius: 20px;
                border: 1px solid #1e1e32;
            }
        """)
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # ── Stacked pages ────────────────────────────────────────
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.stack.addWidget(self._page_welcome())   # page 0
        self.stack.addWidget(self._page_install())   # page 1
        self.stack.addWidget(self._page_done())      # page 2

    # ── Page 0: Welcome ──────────────────────────────────────────
    def _page_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(0)

        # Logo
        logo_label = QLabel()
        from utils.config import get_resource_path
        logo_path = get_resource_path("assets/logo.png")
        pixmap = QPixmap(logo_path).scaled(
            150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel("Welcome to Notivo")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(
            "Before you start recording, Notivo needs to download\n"
            "a few AI models. This only happens once and takes\n"
            "a few minutes depending on your internet speed."
        )
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        # Size estimate info card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_items = [("📦", "Packages", "~500 MB"), ("🎙️", "Whisper AI", "~1.4 GB"), ("🔊", "VAD Model", "~2 MB")]
        for icon, name, size in info_items:
            col = QVBoxLayout()
            col.setSpacing(2)
            icon_l = QLabel(icon)
            icon_l.setStyleSheet("font-size: 22px;")
            icon_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_l = QLabel(name)
            name_l.setStyleSheet("color: #a0a0c0; font-size: 11px;")
            name_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            size_l = QLabel(size)
            size_l.setStyleSheet("color: #e0e0f0; font-size: 12px; font-weight: 700;")
            size_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(icon_l)
            col.addWidget(name_l)
            col.addWidget(size_l)
            info_layout.addLayout(col)
            if info_items.index((icon, name, size)) < 2:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color: #1e1e32;")
                info_layout.addWidget(sep)

        self.btn_start = QPushButton("Get Started →")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_setup)

        footer = QLabel("Developed by Kaleb. Do not modify or copy. © Kaleb")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #404050; font-size: 10px; margin-top: 10px;")

        layout.addStretch(1)
        layout.addWidget(logo_label)
        layout.addSpacing(20)
        layout.addWidget(heading)
        layout.addSpacing(12)
        layout.addWidget(sub)
        layout.addSpacing(24)
        layout.addWidget(info_card)
        layout.addStretch(2)
        layout.addWidget(self.btn_start)
        layout.addWidget(footer)
        return page

    # ── Page 1: Installing ───────────────────────────────────────
    def _page_install(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(0)

        heading = QLabel("Setting Up Notivo")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Please keep the app open. Downloads may take a few minutes.")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        # Step rows
        self.steps = {}
        steps_data = [
            ("packages", "📦", "Python Packages"),
            ("whisper",  "🎙️", "Whisper AI Model (medium)"),
            ("vad",      "🔊", "Voice Activity Detection"),
            ("ollama",   "✨", "Ollama AI Summaries (optional)"),
        ]

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(4)

        for step_id, icon, title in steps_data:
            row = StepRow(icon, title)
            self.steps[step_id] = row
            card_layout.addWidget(row)
            if steps_data.index((step_id, icon, title)) < len(steps_data) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("background-color: #1e1e32; max-height: 1px; border: none;")
                card_layout.addWidget(sep)

        self.btn_continue = QPushButton("Setting up...")
        self.btn_continue.setObjectName("primaryBtn")
        self.btn_continue.setEnabled(False)
        self.btn_continue.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_continue.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        layout.addSpacing(4)
        layout.addWidget(heading)
        layout.addSpacing(8)
        layout.addWidget(sub)
        layout.addSpacing(24)
        layout.addWidget(card)
        layout.addStretch(1)
        layout.addWidget(self.btn_continue)
        return page

    # ── Page 2: Done ─────────────────────────────────────────────
    def _page_done(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(0)

        checkmark = QLabel("🎉")
        checkmark.setStyleSheet("font-size: 72px;")
        checkmark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel("You're All Set!")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(
            "Notivo is ready to record, transcribe, and summarize\n"
            "your meetings — completely offline."
        )
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        btn_launch = QPushButton("Start Using Notivo 🚀")
        btn_launch.setObjectName("primaryBtn")
        btn_launch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_launch.clicked.connect(self._finish)

        layout.addStretch(2)
        layout.addWidget(checkmark)
        layout.addSpacing(16)
        layout.addWidget(heading)
        layout.addSpacing(12)
        layout.addWidget(sub)
        layout.addStretch(3)
        layout.addWidget(btn_launch)
        return page

    # ── Logic ────────────────────────────────────────────────────
    def _start_setup(self):
        try:
            import requests
            requests.get("http://localhost:11434/api/tags", timeout=1)
            self.install_ollama_requested = False
        except Exception:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Install Ollama AI?", 
                "Notivo needs Ollama to generate offline AI Summaries.\n\nWould you like to automatically download and install Ollama now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            self.install_ollama_requested = (reply == QMessageBox.StandardButton.Yes)

        self.stack.setCurrentIndex(1)
        self.worker = SetupWorker()
        self.worker.install_ollama_requested = self.install_ollama_requested
        self.worker.step_started.connect(self._on_step_started)
        self.worker.step_progress.connect(self._on_step_progress)
        self.worker.step_done.connect(self._on_step_done)
        self.worker.all_done.connect(self._on_all_done)
        self.worker.start()

    def _on_step_started(self, step_id, msg):
        if step_id in self.steps:
            self.steps[step_id].set_running(msg)

    def _on_step_progress(self, step_id, value):
        if step_id in self.steps:
            self.steps[step_id].set_progress(value)

    def _on_step_done(self, step_id, success, note):
        if step_id not in self.steps:
            return
        if success:
            self.steps[step_id].set_done(note)
        elif step_id == "ollama":
            self.steps[step_id].set_warning(note)
        else:
            self.steps[step_id].set_error(note)

    def _on_all_done(self):
        # Write the setup_complete marker
        marker = Path.home() / ".notivo" / "setup_complete"
        marker.touch()

        self.btn_continue.setText("Continue →")
        self.btn_continue.setEnabled(True)

    def _finish(self):
        self.setup_complete.emit()
        self.accept()

    # ── Rounded paint ────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        painter.fillPath(path, QColor("#0d0d14"))
