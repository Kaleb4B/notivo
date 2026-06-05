from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QLinearGradient, QColor, QBrush
from PySide6.QtCore import Qt, Signal, QRect
from utils.config import get_resource_path

W = 400
H = 460   # single seamless window, slightly taller than logo

class SplashScreen(QWidget):
    skip_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(W, H)

        logo_path = get_resource_path("assets/logo.png")
        self.pixmap = QPixmap(logo_path).scaled(
            W, W,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # ── Layout: controls pinned to bottom of a single unified widget ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 20)
        layout.setSpacing(6)
        layout.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(40, 36, 58, 0.7);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c3ce0, stop:1 #a855f7);
                border-radius: 3px;
            }
        """)

        self.status = QLabel("Loading...")
        self.status.setStyleSheet("color: rgba(200, 200, 230, 0.75); font-size: 11px; background: transparent;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_skip = QPushButton("🚀  Launch Application")
        self.btn_skip.setFixedHeight(40)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c3ce0, stop:1 #8b5cf6);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c4cf0, stop:1 #9b6cff);
            }
            QPushButton:pressed { background: #5a2dc0; }
        """)
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.clicked.connect(self.skip_clicked.emit)

        self.copyright_lbl = QLabel("© 2026 kalebdap. All rights reserved.")
        self.copyright_lbl.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 9px; background: transparent;")
        self.copyright_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.btn_skip)
        layout.addWidget(self.copyright_lbl)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Clip everything to a single rounded rect (seamless shape)
        path = QPainterPath()
        path.addRoundedRect(0, 0, W, H, 24, 24)
        painter.setClipPath(path)

        # 2. Draw the logo covering the full window
        painter.drawPixmap(0, 0, self.pixmap.scaled(
            W, H,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

        # 3. Overlay a smooth gradient from transparent to dark at the bottom
        #    — this seamlessly merges the logo into the control area
        grad = QLinearGradient(0, H // 2, 0, H)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.45, QColor(10, 8, 20, 180))
        grad.setColorAt(1.0, QColor(10, 8, 20, 230))
        painter.fillRect(QRect(0, 0, W, H), QBrush(grad))

    def showMessage(self, msg):
        self.status.setText(msg)
