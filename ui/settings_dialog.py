from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QFileDialog, QFormLayout)
from PySide6.QtCore import Qt
from utils.config import config
from utils.logger import logger
import sounddevice as sd

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 300)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0d12;
                color: #e0e0e6;
            }
            QLabel {
                color: #e0e0e6;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #14141e;
                border: 1px solid #24243a;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e0e0e6;
                min-width: 150px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                border: 1px solid #32324e;
                border-radius: 6px;
                color: #e0e0e6;
                selection-background-color: #6c3ce0;
                selection-color: white;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                margin: 2px 4px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #6c3ce0;
                color: white;
            }
            QPushButton {
                background-color: #24243a;
                color: #e0e0e6;
                border-radius: 6px;
                padding: 8px 16px;
                border: 1px solid #32324e;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #32324e;
            }
        """)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Storage Folder
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_btn = QPushButton("Browse")
        self.folder_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.folder_btn)
        form_layout.addRow("Storage Folder:", folder_layout)

        # Audio Input Device
        self.mic_combo = QComboBox()
        self.mic_combo.addItem("System Default", -1)
        try:
            for i, d in enumerate(sd.query_devices()):
                if d['max_input_channels'] > 0:
                    self.mic_combo.addItem(d['name'], i)
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
        form_layout.addRow("Microphone:", self.mic_combo)

        # Whisper Model
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        form_layout.addRow("Whisper Model:", self.whisper_combo)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        form_layout.addRow("Theme:", self.theme_combo)

        # Ollama Model
        self.ollama_combo = QComboBox()
        self.ollama_combo.addItems(["llama3.2", "llama3.1", "qwen2.5", "gemma2"])
        form_layout.addRow("Ollama Model:", self.ollama_combo)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Storage Folder", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def load_settings(self):
        self.folder_input.setText(config.get("storage_folder"))
        self.whisper_combo.setCurrentText(config.get("whisper_model"))
        self.theme_combo.setCurrentText(config.get("theme"))
        self.ollama_combo.setCurrentText(config.get("ollama_model"))
        
        device_idx = config.get("input_device", -1)
        idx = self.mic_combo.findData(device_idx)
        if idx >= 0:
            self.mic_combo.setCurrentIndex(idx)

    def save_settings(self):
        config.set("storage_folder", self.folder_input.text())
        config.set("whisper_model", self.whisper_combo.currentText())
        config.set("theme", self.theme_combo.currentText())
        config.set("ollama_model", self.ollama_combo.currentText())
        config.set("input_device", self.mic_combo.currentData())
        logger.info("Settings saved.")
        self.accept()
