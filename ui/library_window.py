import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QLabel, QListWidget,
                               QSplitter, QMessageBox, QListWidgetItem, QWidget)
from PySide6.QtCore import Qt, QFileSystemWatcher
from utils.config import config
from utils.logger import logger
import markdown

class LibraryWindow(QDialog):
    def __init__(self, session_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notivo - Recording History")
        self.resize(1000, 700)
        self.session_manager = session_manager
        
        # Setup File Watcher for Real-time Updates
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.directoryChanged.connect(self.load_sessions)
        
        self.init_ui()
        self.watch_sessions_directory()
        self.load_sessions()
        self.apply_theme()
        
    def watch_sessions_directory(self):
        sessions_dir = str(self.session_manager.root_dir)
        if os.path.exists(sessions_dir) and sessions_dir not in self.file_watcher.directories():
            self.file_watcher.addPath(sessions_dir)
            
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Sessions List)
        left_panel = QVBoxLayout()
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.on_session_selected)
        left_panel.addWidget(QLabel("Sessions"))
        left_panel.addWidget(self.session_list)
        
        # Session Control Buttons
        btn_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_export_pdf = QPushButton("📄 Export PDF")
        self.btn_rename = QPushButton("✏️ Rename")
        self.btn_delete_session = QPushButton("🗑 Delete")
        
        self.btn_open_folder.clicked.connect(self.open_session_folder)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_rename.clicked.connect(self.rename_session)
        self.btn_delete_session.clicked.connect(self.delete_session)
        
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addWidget(self.btn_export_pdf)
        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_delete_session)
        left_panel.addLayout(btn_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        
        # Right Panel (Transcript & Summary)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        
        # Transcript header row with translate controls
        transcript_header = QHBoxLayout()
        transcript_header.addWidget(QLabel("📝 Transcript"))
        transcript_header.addStretch()
        
        from PySide6.QtWidgets import QComboBox
        self.combo_translate_lang = QComboBox()
        self.combo_translate_lang.setObjectName("translateLangCombo")
        self.combo_translate_lang.addItems(["🇮🇩 Indonesia", "🇺🇸 English", "🇨🇳 Mandarin", "🌐 Auto Detect"])
        self.combo_translate_lang.setFixedWidth(130)
        
        self.btn_translate = QPushButton("🌐 Translate")
        self.btn_translate.setObjectName("translateBtn")
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.clicked.connect(self.translate_transcript)
        
        self.btn_restore_original = QPushButton("↩ Original")
        self.btn_restore_original.setObjectName("restoreBtn")
        self.btn_restore_original.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore_original.clicked.connect(self.restore_original_transcript)
        self.btn_restore_original.setVisible(False)

        transcript_header.addWidget(self.combo_translate_lang)
        transcript_header.addWidget(self.btn_translate)
        transcript_header.addWidget(self.btn_restore_original)
        
        self._original_transcript = ""
        self._translated_transcript = ""
        self._is_translated = False
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        right_panel.addLayout(transcript_header)
        right_panel.addWidget(self.transcript_area)
        
        self.summary_area = QTextEdit()
        self.summary_area.setReadOnly(True)
        right_panel.addWidget(QLabel("✨ AI Summary"))
        right_panel.addWidget(self.summary_area)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([300, 600])
        main_layout.addWidget(splitter)
        

    def apply_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0d12;
                color: #e0e0e6;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #e0e0e6;
                margin-bottom: 5px;
                margin-top: 5px;
            }
            QListWidget {
                background-color: #14141e;
                border: 1px solid #24243a;
                border-radius: 12px;
                padding: 5px;
                color: #e0e0e6;
                outline: 0;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: #6c3ce0;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #24243a;
            }
            QTextEdit {
                background-color: #14141e;
                border: 1px solid #24243a;
                border-radius: 12px;
                padding: 15px;
                color: #e0e0e6;
                font-size: 14px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #24243a;
                color: #e0e0e6;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
                border: 1px solid #32324e;
            }
            QPushButton:hover {
                background-color: #32324e;
            }
            QPushButton#translateBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e3a2a, stop:1 #1a2e22);
                color: #6ee7b7;
                border: 1px solid #34604a;
                border-radius: 8px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#translateBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a5040, stop:1 #22402e);
                border-color: #10b981;
            }
            QPushButton#translateBtn:disabled {
                color: #405050; border-color: #1e3030; background: #131e1a;
            }
            QPushButton#restoreBtn {
                background-color: #1e1e2e;
                color: #a0a0c0;
                border: 1px solid #2a2a3a;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton#restoreBtn:hover { background-color: #2a2a3a; }
            QComboBox#translateLangCombo {
                background-color: #14141e;
                border: 1px solid #24243a;
                border-radius: 8px;
                padding: 4px 8px;
                color: #a0c0a0;
                font-size: 11px;
            }
            QComboBox#translateLangCombo QAbstractItemView {
                background-color: #1a1a2e;
                border: 1px solid #3a3460;
                color: #a0c0a0;
                selection-background-color: #10b981;
                selection-color: white;
                outline: 0;
            }
            QSplitter::handle {
                background-color: #24243a;
                margin: 2px;
                width: 2px;
                border-radius: 1px;
            }
        """)

    def load_sessions(self):
        # Remember currently selected folder_path if any
        selected_path = None
        if self.session_list.currentItem():
            session = self.session_list.currentItem().data(Qt.ItemDataRole.UserRole)
            if session:
                selected_path = session.folder_path
                
        self.session_list.clear()
        sessions = self.session_manager.get_all_sessions()
        
        for session in sessions:
            title = session.metadata.title
            if not title or title == "New Recording" or title == "Meeting Session":
                title = session.metadata.created_at
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.session_list.addItem(item)
            
        # Restore selection or select first item
        if self.session_list.count() > 0:
            if selected_path:
                for i in range(self.session_list.count()):
                    item = self.session_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole).folder_path == selected_path:
                        self.session_list.setCurrentItem(item)
                        self.on_session_selected(item)
                        return
            
            # If no selection restored, select first item
            first_item = self.session_list.item(0)
            self.session_list.setCurrentItem(first_item)
            self.on_session_selected(first_item)
            
    def select_session(self, target_session):
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            session = item.data(Qt.ItemDataRole.UserRole)
            if session.folder_path == target_session.folder_path:
                self.session_list.setCurrentItem(item)
                self.on_session_selected(item)
                break
                
    def on_session_selected(self, item):
        session = item.data(Qt.ItemDataRole.UserRole)
        
        # Reset translation state
        self._is_translated = False
        self._translated_transcript = ""
        self._translated_summary = ""
        self.btn_restore_original.setVisible(False)
        self.btn_translate.setEnabled(True)
        
        # Load transcript
        if session.transcript_file.exists():
            with open(session.transcript_file, 'r', encoding='utf-8') as f:
                raw = f.read()
                self._original_transcript = raw
                self.transcript_area.setPlainText(raw)
        else:
            self._original_transcript = ""
            self.transcript_area.clear()
            
        # Load summary
        if session.summary_file.exists():
            with open(session.summary_file, 'r', encoding='utf-8') as f:
                md_text = f.read()
                self._original_summary = md_text
                html = markdown.markdown(md_text)
                self.summary_area.setHtml(html)
        else:
            self._original_summary = ""
            self.summary_area.setPlainText("AI Summary unavailable")

    def delete_session(self):
        item = self.session_list.currentItem()
        if not item:
            return
            
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     'Are you sure you want to delete this session?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            session = item.data(Qt.ItemDataRole.UserRole)
            self.session_manager.delete_session(session)
            self.load_sessions()
            self.transcript_area.clear()
            self.summary_area.clear()

    def open_session_folder(self):
        item = self.session_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        self.session_manager.open_in_explorer(session.folder_path)

    def rename_session(self):
        item = self.session_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Session", "Enter new name:", text=session.metadata.title)
        
        if ok and new_name.strip():
            session.metadata.title = new_name.strip()
            session.save_metadata()
            self.load_sessions()

    def translate_transcript(self):
        if not self._original_transcript.strip():
            QMessageBox.warning(self, "No Transcript", "No transcript to translate.")
            return
        
        LANG_LABELS = {
            "🇮🇩 Indonesia": "Indonesian",
            "🇺🇸 English": "English",
            "🇨🇳 Mandarin": "Mandarin Chinese (Simplified)",
            "🌐 Auto Detect": "the most appropriate language",
        }
        selected_label = self.combo_translate_lang.currentText()
        target_lang = LANG_LABELS.get(selected_label, "English")
        
        self.btn_translate.setEnabled(False)
        self.btn_translate.setText("⏳ Translating...")
        
        # Disable controls while translating
        self.combo_translate_lang.setEnabled(False)
        self.btn_rename.setEnabled(False)
        self.btn_delete_session.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        
        from PySide6.QtCore import QThread, Signal
        from utils.config import config
        from summary.ollama_client import OllamaClient
        
        class TranslateWorker(QThread):
            done = Signal(str, str)
            error = Signal(str)
            def __init__(self, transcript, summary, lang, model):
                super().__init__()
                self.transcript = transcript
                self.summary = summary
                self.lang = lang
                self.model = model
            def run(self):
                try:
                    client = OllamaClient()
                    
                    # 1. Translate Transcript
                    prompt_trans = (
                        f"Translate the following meeting transcript to {self.lang}.\n"
                        f"Preserve the meaning exactly. Output ONLY the translated text, nothing else.\n\n"
                        f"Transcript:\n{self.transcript}"
                    )
                    res_trans = client.generate_text(prompt_trans, self.model)
                    
                    # 2. Translate Summary
                    res_sum = ""
                    if self.summary.strip():
                        prompt_sum = (
                            f"Translate the following meeting summary to {self.lang}.\n"
                            f"Preserve the markdown formatting exactly. Output ONLY the translated text, nothing else.\n\n"
                            f"Summary:\n{self.summary}"
                        )
                        res_sum = client.generate_text(prompt_sum, self.model)
                    
                    self.done.emit(res_trans, res_sum)
                except Exception as e:
                    self.error.emit(str(e))
        
        model = config.get("ollama_model", "qwen2.5")
        self._translate_worker = TranslateWorker(self._original_transcript, getattr(self, "_original_summary", ""), target_lang, model)
        self._translate_worker.done.connect(self._on_translate_done)
        self._translate_worker.error.connect(self._on_translate_error)
        self._translate_worker.start()

    def _on_translate_done(self, translated_transcript, translated_summary):
        self._translated_transcript = translated_transcript
        self._translated_summary = translated_summary
        self._is_translated = True
        
        self.transcript_area.setPlainText(translated_transcript)
        if translated_summary:
            import markdown
            self.summary_area.setHtml(markdown.markdown(translated_summary))
            
        self.btn_translate.setText("🌐 Translate")
        self.btn_translate.setEnabled(True)
        self.btn_restore_original.setVisible(True)
        
        # Re-enable controls
        self.combo_translate_lang.setEnabled(True)
        self.btn_rename.setEnabled(True)
        self.btn_delete_session.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)

    def _on_translate_error(self, err):
        self.btn_translate.setText("🌐 Translate")
        self.btn_translate.setEnabled(True)
        
        # Re-enable controls
        self.combo_translate_lang.setEnabled(True)
        self.btn_rename.setEnabled(True)
        self.btn_delete_session.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        
        QMessageBox.warning(self, "Translation Failed", f"Could not translate:\n{err}")

    def restore_original_transcript(self):
        self._is_translated = False
        self._translated_transcript = ""
        self._translated_summary = ""
        self.transcript_area.setPlainText(self._original_transcript)
        
        if hasattr(self, "_original_summary") and self._original_summary:
            import markdown
            self.summary_area.setHtml(markdown.markdown(self._original_summary))
        else:
            self.summary_area.setPlainText("AI Summary unavailable")
            
        self.btn_restore_original.setVisible(False)

    def export_pdf(self):
        item = self.session_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        
        # Use translated transcript if available, otherwise original
        if self._is_translated and self._translated_transcript:
            transcript = self._translated_transcript
        elif self._original_transcript:
            transcript = self._original_transcript
        elif session.transcript_file.exists():
            with open(session.transcript_file, 'r', encoding='utf-8') as f:
                transcript = f.read()
        else:
            transcript = ""
                
        summary_html = ""
        if self._is_translated and self._translated_summary:
            summary_html = markdown.markdown(self._translated_summary)
        elif hasattr(self, "_original_summary") and self._original_summary:
            summary_html = markdown.markdown(self._original_summary)
        elif session.summary_file.exists():
            with open(session.summary_file, 'r', encoding='utf-8') as f:
                md_text = f.read()
                summary_html = markdown.markdown(md_text)
                
        from ui.pdf_preview import PDFPreviewDialog
        title = session.metadata.title
        if not title or title == "New Recording" or title == "Meeting Session":
            title = session.metadata.created_at
            
        dialog = PDFPreviewDialog(title, transcript, summary_html, self)
        dialog.exec()
