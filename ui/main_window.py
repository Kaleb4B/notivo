import os
import queue
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QLabel, QListWidget,
                               QSplitter, QToolBar, QStatusBar, QMessageBox,
                               QListWidgetItem, QFileDialog, QInputDialog, QComboBox)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence

from utils.config import config
from utils.logger import logger
from storage.session_manager import SessionManager
from audio.audio_worker import AudioWorker
from transcription.transcription_worker import TranscriptionWorker
from summary.summary_worker import SummaryWorker
from audio.recorder import check_microphone_available
from .settings_dialog import SettingsDialog
from ui.waveform import WaveformWidget
from ui.library_window import LibraryWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notivo - Record. Transcribe. Summarize.")
        self.resize(850, 550)
        
        self.session_manager = SessionManager()
        self.current_session = None
        self.committed_text = ""
        
        self.audio_queue = queue.Queue()
        
        self.audio_worker = None
        self.transcription_worker = None
        self.summary_worker = None
        
        self.is_recording = False
        self.is_paused = False
        self.timer_count = 0
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_timer)
        
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_transcript)
        
        self._old_workers = []  # Keep references to prevent GC crash
        
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        # Menu Bar for Export and Settings
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        self.action_settings = QAction("Settings", self)
        self.action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.action_settings.triggered.connect(self.open_settings)
        file_menu.addAction(self.action_settings)
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Top Bar (Library & Settings Buttons)
        top_layout = QHBoxLayout()
        self.btn_library = QPushButton("📚 Recording History")
        self.btn_library.setObjectName("secondaryBtn")
        self.btn_library.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_library.clicked.connect(self.open_library)
        
        # Language Selector — styled pill dropdown
        self.LANG_MAP = {
            "🌐 Auto": "auto",
            "🇮🇩 Indonesia": "id",
            "🇺🇸 English": "en",
            "🇨🇳 Mandarin": "zh",
        }
        self.LANG_MAP_REVERSE = {v: k for k, v in self.LANG_MAP.items()}
        self.combo_language = QComboBox()
        self.combo_language.setObjectName("langCombo")
        self.combo_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_language.addItems(list(self.LANG_MAP.keys()))
        current_lang = config.get("language", "auto")
        self.combo_language.setCurrentText(self.LANG_MAP_REVERSE.get(current_lang, "🌐 Auto"))
        self.combo_language.currentTextChanged.connect(
            lambda label: config.set("language", self.LANG_MAP.get(label, "auto"))
        )
        
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("iconBtn")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        
        top_layout.addWidget(self.btn_library)
        top_layout.addStretch()
        top_layout.addWidget(self.combo_language)
        top_layout.addWidget(self.btn_settings)
        main_layout.addLayout(top_layout)
        
        # Waveform Visualizer
        self.waveform = WaveformWidget()
        main_layout.addWidget(self.waveform, 1) # Give it stretching priority
        
        # Spacer
        main_layout.addSpacing(20)
        
        # Bottom Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)
        
        self.lbl_speech = QLabel("")
        self.lbl_speech.setObjectName("speechLabel")
        controls_layout.addWidget(self.lbl_speech)
        
        controls_layout.addStretch()
        
        self.btn_record = QPushButton("● RECORD")
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.setFixedSize(180, 54)
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.btn_record)
        
        controls_layout.addStretch()
        
        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setObjectName("timerLabel")
        controls_layout.addWidget(self.lbl_timer)
        
        main_layout.addLayout(controls_layout)
        
        # Status Bar (minimal)
        # © Developed by Kaleb. Do not modify or copy.
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 0, 8, 0)
        self.lbl_mic = QLabel("🎙 Mic: Ready")
        self.lbl_mic.setObjectName("statusLabel")
        self.lbl_rec = QLabel("Idle")
        self.lbl_rec.setObjectName("statusLabel")
        status_layout.addWidget(self.lbl_mic)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_rec)
        self.statusbar.addPermanentWidget(status_widget)

    def apply_theme(self):
        theme = config.get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                /* ── Global ── */
                QMainWindow {
                    background-color: #0f0f14;
                    color: #e0e0e6;
                    font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', sans-serif;
                    font-size: 13px;
                }
                QMenuBar {
                    background-color: #0f0f14;
                    color: #a0a0b0;
                    border: none;
                    font-size: 13px;
                }
                QMenuBar::item:selected { background-color: #2a2a3a; border-radius: 4px; }
                QMenu {
                    background-color: #1a1a24;
                    color: #e0e0e6;
                    border: 1px solid #2a2a3a;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item:selected { background-color: #3a3a5a; border-radius: 4px; }
                QStatusBar { 
                    background-color: #0f0f14; 
                    color: #606070; 
                    border-top: 1px solid #1a1a24;
                    font-size: 11px;
                }
                QSplitter::handle { background-color: #1a1a24; }
                QScrollBar:vertical {
                    background: transparent;
                    width: 6px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #3a3a5a;
                    border-radius: 3px;
                    min-height: 30px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
                QScrollBar:horizontal { height: 0; }
                
                /* ── Left Panel ── */
                #leftPanel {
                    background-color: #14141e;
                    border-radius: 16px;
                    border: 1px solid #1e1e2e;
                }
                #panelTitle {
                    font-size: 16px;
                    font-weight: bold;
                    color: #ffffff;
                }
                #iconBtn {
                    background-color: #1e1e2e;
                    color: #a0a0b0;
                    border: none;
                    border-radius: 16px;
                    font-size: 16px;
                }
                #iconBtn:hover { background-color: #2a2a3a; color: #ffffff; }
                
                #sessionList {
                    background-color: #1a1a28;
                    border: 1px solid #24243a;
                    border-radius: 10px;
                    padding: 6px;
                    color: #c0c0d0;
                    font-size: 12px;
                    outline: none;
                }
                #sessionList::item {
                    padding: 8px 10px;
                    border-radius: 6px;
                    margin: 2px 0;
                }
                #sessionList::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6c3ce0, stop:1 #8b5cf6);
                    color: white;
                }
                #sessionList::item:hover:!selected {
                    background-color: #22223a;
                }
                
                #secondaryBtn {
                    background-color: #1e1e2e;
                    color: #c0c0d0;
                    border: 1px solid #2a2a3a;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                #secondaryBtn:hover { background-color: #2a2a3a; color: #ffffff; }
                
                #dangerBtn {
                    background-color: #1e1e2e;
                    color: #f87171;
                    border: 1px solid #2a2a3a;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                #dangerBtn:hover { background-color: #2a1a1a; }
                
                /* ── Cards ── */
                #card {
                    background-color: #14141e;
                    border-radius: 14px;
                    border: 1px solid #1e1e2e;
                }
                #cardTitle {
                    font-size: 14px;
                    font-weight: bold;
                    color: #a0a0c0;
                }
                #transcriptArea, #summaryArea {
                    background-color: #1a1a28;
                    color: #e0e0f0;
                    border: 1px solid #24243a;
                    border-radius: 10px;
                    padding: 12px;
                    font-size: 13px;
                    selection-background-color: #6c3ce0;
                }
                
                /* ── Controls ── */
                #controlsArea {
                    background-color: #14141e;
                    border-radius: 14px;
                    border: 1px solid #1e1e2e;
                }
                #recordBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #dc2626, stop:1 #ef4444);
                    color: white;
                    border-radius: 24px;
                    font-size: 15px;
                    font-weight: bold;
                    border: none;
                }
                #recordBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #b91c1c, stop:1 #dc2626);
                }
                #recordBtn:disabled {
                    background: #FFA726;
                    color: #1a1a1a;
                }
                #stopBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #374151, stop:1 #4b5563);
                    color: white;
                    border-radius: 24px;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #6b7280;
                }
                #stopBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4b5563, stop:1 #6b7280);
                }
                #processingBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #f59e0b, stop:1 #fbbf24);
                    color: #1a1a1a;
                    border-radius: 24px;
                    font-size: 15px;
                    font-weight: bold;
                    border: none;
                }
                #timerLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #6c3ce0;
                    font-family: 'SF Mono', 'JetBrains Mono', 'Menlo', monospace;
                }
                #speechLabel {
                    font-size: 13px;
                    font-weight: bold;
                    color: #888;
                    min-width: 140px;
                }
                #statusLabel {
                    color: #505060;
                    font-size: 11px;
                }
                
                /* ── Language Pill Selector ── */
                QComboBox#langCombo {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1e1a3a, stop:1 #1a1a2e);
                    color: #c0b8f0;
                    border: 1px solid #3a3460;
                    border-radius: 14px;
                    padding: 5px 14px 5px 12px;
                    font-size: 12px;
                    font-weight: 600;
                    min-width: 130px;
                }
                QComboBox#langCombo:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2a2050, stop:1 #23203e);
                    border-color: #6c3ce0;
                    color: #e0d8ff;
                }
                QComboBox#langCombo:disabled {
                    color: #404060;
                    border-color: #1e1e32;
                    background: #13131e;
                }
                QComboBox#langCombo::drop-down {
                    border: none;
                    width: 18px;
                }
                QComboBox#langCombo::down-arrow {
                    width: 0; height: 0;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #6c3ce0;
                }
                QComboBox#langCombo QAbstractItemView {
                    background-color: #1a1a2e;
                    border: 1px solid #3a3460;
                    border-radius: 10px;
                    color: #c0b8f0;
                    selection-background-color: #6c3ce0;
                    selection-color: white;
                    outline: 0;
                    padding: 4px;
                }
                QComboBox#langCombo QAbstractItemView::item {
                    padding: 7px 14px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }

                /* ── Dialog Overrides ── */
                QDialog {
                    background-color: #14141e;
                    color: #e0e0e6;
                    border-radius: 12px;
                }
                QComboBox {
                    background-color: #1a1a28;
                    color: #e0e0e6;
                    border: 1px solid #24243a;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QComboBox::drop-down { border: none; }
                QLineEdit {
                    background-color: #1a1a28;
                    color: #e0e0e6;
                    border: 1px solid #24243a;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
            """)
        else:
            self.setStyleSheet("")

    def open_library(self, session_to_select=None):
        lib = LibraryWindow(self.session_manager, self)
        if session_to_select:
            lib.select_session(session_to_select)
        lib.exec()

    def export_current(self):
        QMessageBox.information(self, "Export", "Open Library to view and copy transcripts.")
        
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.apply_theme()

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if not check_microphone_available():
            QMessageBox.critical(self, "Error", "Microphone not available!")
            return
            
        self.current_session = self.session_manager.create_new_session()
        self.audio_queue = queue.Queue()
        
        # Clean up old workers that have finished
        self._old_workers = [w for w in self._old_workers if not w.isFinished()]
        
        # Save current workers to prevent GC crash if they are still running
        if self.audio_worker:
            self._old_workers.append(self.audio_worker)
        if self.transcription_worker:
            self._old_workers.append(self.transcription_worker)
            
        self.audio_worker = AudioWorker(self.current_session.audio_file, self.audio_queue)
        self.audio_worker.audio_level.connect(self.waveform.update_audio_level)
        self.transcription_worker = TranscriptionWorker(self.audio_queue)
        
        self.transcription_worker.text_transcribed.connect(self.append_transcript)
        self.transcription_worker.interim_transcribed.connect(self.update_interim_transcript)
        self.transcription_worker.speech_status.connect(self.update_speech_status)
        self.transcription_worker.status_message.connect(self.update_status_message)
        self.transcription_worker.error_occurred.connect(self.handle_error)
        self.transcription_worker.finished.connect(self.on_transcription_finished)
        self.audio_worker.error_occurred.connect(self.handle_error)
        
        self.audio_worker.start()
        self.transcription_worker.start()
        
        self.is_recording = True
        self.is_paused = False
        self.timer_count = 0
        self.lbl_timer.setText("00:00:00")
        self.committed_text = ""
        self.waveform.start()
        
        self.btn_record.setText("■  STOP")
        self.btn_record.setObjectName("stopBtn")
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)
        self.lbl_rec.setText("Recording")
        
        self.btn_library.setEnabled(False)
        self.btn_settings.setEnabled(False)
        self.combo_language.setEnabled(False)
        self.action_settings.setEnabled(False)
        
        self.recording_timer.start(1000)
        auto_save = config.get("auto_save_interval", 5) * 1000
        self.autosave_timer.start(auto_save)
        
    def pause_recording(self):
        pass

    def resume_recording(self):
        pass

    def stop_recording(self):
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.recording_timer.stop()
        self.autosave_timer.stop()
        
        self.audio_worker.stop()
        self.waveform.stop()
        
        # Wait for audio worker to completely finish pushing all chunks to the queue
        self.audio_worker.wait(2000)
        
        # Stop transcription worker only after audio worker is fully done
        self.transcription_worker.stop()
        
        self.autosave_transcript()
        
        self.btn_record.setText("⏳ Processing...")
        self.btn_record.setEnabled(False)
        self.btn_record.setObjectName("processingBtn")
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)
        self.lbl_rec.setText("Processing")
        
        self.current_session.metadata.duration = self.timer_count
        self.current_session.save_metadata()
        

    def on_transcription_finished(self):
        if not self.is_recording:
            self.generate_summary()

    def update_timer(self):
        self.timer_count += 1
        hours = self.timer_count // 3600
        minutes = (self.timer_count % 3600) // 60
        seconds = self.timer_count % 60
        self.lbl_timer.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def update_audio_meter(self, level):
        pass
        
    def update_speech_status(self, is_speaking):
        if is_speaking:
            self.lbl_speech.setText("🎤 Listening...")
            self.lbl_speech.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_speech.setText("")
            self.lbl_speech.setStyleSheet("color: #888; font-style: italic;")

    def update_status_message(self, msg):
        if msg:
            self.lbl_speech.setText(f"⏳ {msg}")
            self.lbl_speech.setStyleSheet("color: #FFA726; font-weight: bold;")
        else:
            self.lbl_speech.setText("")
            self.lbl_speech.setStyleSheet("color: #888; font-style: italic;")

    def append_transcript(self, text):
        if text.strip():
            if self.committed_text:
                self.committed_text += "\n"
            self.committed_text += text.strip()
            self.autosave_transcript()
            
    def update_interim_transcript(self, text):
        pass # UI is clean now, no interim text displayed.
            
    def autosave_transcript(self):
        if self.current_session:
            try:
                with open(self.current_session.transcript_file, 'w', encoding='utf-8') as f:
                    f.write(self.committed_text)
            except Exception as e:
                logger.error(f"Autosave failed: {e}")

    def generate_summary(self):
        if not self.current_session:
            return
            
        self.lbl_rec.setText("Status: Generating Summary...")
        
        selected_lang_code = config.get("language", "auto")
        code_to_name = {
            "auto": "Indonesian",
            "id": "Indonesian",
            "en": "English",
            "zh": "Mandarin Chinese (Simplified)"
        }
        lang_name = code_to_name.get(selected_lang_code, "Indonesian")
        
        self.summary_worker = SummaryWorker(
            self.current_session.transcript_file,
            self.current_session.summary_file,
            self.current_session,
            lang_name
        )
        self.summary_worker.summary_finished.connect(self.on_summary_finished)
        self.summary_worker.error_occurred.connect(self.on_summary_error)
        self.summary_worker.start()
        
    def on_summary_finished(self, summary):
        self.btn_record.setText("● RECORD")
        self.btn_record.setEnabled(True)
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)
        self.lbl_rec.setText("Idle")
        self.lbl_speech.setText("")
        self.lbl_timer.setText("00:00:00")
        
        self.btn_library.setEnabled(True)
        self.btn_settings.setEnabled(True)
        self.combo_language.setEnabled(True)
        self.action_settings.setEnabled(True)
        
        # Ask for a session name
        new_name, ok = QInputDialog.getText(self, "Session Name", "Please enter a name for this meeting session:", text=self.current_session.metadata.title)
        if ok and new_name.strip():
            self.current_session.metadata.title = new_name.strip()
            self.current_session.save_metadata()
        
        self.open_library(session_to_select=self.current_session)
        
    def on_summary_error(self, err):
        self.lbl_rec.setText("Status: Idle")
        self.btn_record.setText("● RECORD")
        self.btn_record.setEnabled(True)
        self.btn_library.setEnabled(True)
        self.btn_settings.setEnabled(True)
        self.combo_language.setEnabled(True)
        self.action_settings.setEnabled(True)
        QMessageBox.warning(self, "Summary Error", err)

    def handle_error(self, err):
        logger.error(f"Worker error: {err}")
        QMessageBox.critical(self, "Error", str(err))

    def closeEvent(self, event):
        if self.is_recording:
            reply = QMessageBox.question(
                self, "Recording in Progress",
                "You are currently recording. Are you sure you want to exit?\nThe recording will be stopped and lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_recording()
                event.accept()
            else:
                event.ignore()
            return
            
        if self.summary_worker and self.summary_worker.isRunning():
            reply = QMessageBox.question(
                self, "Processing in Progress",
                "AI is currently generating a summary. Are you sure you want to exit?\nThe process will be canceled.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
            return
            
        event.accept()
