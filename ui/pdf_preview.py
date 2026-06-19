from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextBrowser, QFileDialog,
                               QMessageBox, QLabel, QFrame)
from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QFont, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from datetime import datetime


class PDFPreviewDialog(QDialog):
    def __init__(self, title, transcript, summary_html, parent=None, session=None):
        super().__init__(parent)
        self.setWindowTitle("Export PDF — Notivo")
        self.resize(860, 950)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
        """)

        self.pdf_title = title
        self.session = session

        # Metadata
        now = datetime.now().strftime("%d %B %Y, %H:%M")
        created_at = ""
        duration_str = ""
        if session:
            try:
                created_at = session.metadata.created_at
                secs = int(session.metadata.duration)
                h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
                duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            except Exception:
                pass

        date_label = created_at or now

        # Count words in transcript
        word_count = len(transcript.split()) if transcript else 0

        self.html_content = self._build_html(title, transcript, summary_html,
                                              date_label, duration_str, word_count)
        self._init_ui()

    def _build_html(self, title, transcript, summary_html, date_label, duration_str, word_count):
        dur_text = f"⏱ {duration_str} &nbsp;&nbsp;|&nbsp;&nbsp; " if duration_str else ""
        meta_info = f"📅 {date_label} &nbsp;&nbsp;|&nbsp;&nbsp; {dur_text}📝 {word_count:,} words"

        # Clean transcript for display — replace newlines with <br>
        transcript_html = transcript.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        transcript_html = transcript_html.replace("\n", "<br>")

        summary_block = summary_html if summary_html else "<p style='color:#888;font-style:italic;'>No summary available.</p>"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  /* ── Typography & Clean Style ── */
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    color: #000000;
    background: #ffffff;
    padding: 0;
    line-height: 1.6;
  }}
  
  .header-container {{
    border-bottom: 2px solid #000000;
    padding-bottom: 20px;
    margin-bottom: 30px;
  }}
  .cover-logo {{
    font-size: 9.5pt;
    font-weight: bold;
    color: #666666;
    letter-spacing: 2px;
    margin-bottom: 12px;
  }}
  .cover-title {{
    font-size: 24pt;
    font-weight: bold;
    color: #000000;
    margin-bottom: 15px;
    line-height: 1.1;
  }}
  .cover-meta {{
    color: #555555;
    font-size: 10pt;
  }}

  /* ── Main Content ── */
  .content {{
    padding: 32px 40px 40px;
  }}
  
  .section-label {{
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #000000;
    margin-bottom: 15px;
    margin-top: 30px;
  }}

  /* ── Summary Block ── */
  .summary-wrapper {{
    background: #ffffff;
    padding: 10px 0;
  }}

  /* Markdown-rendered summary styles */
  .summary-wrapper h2 {{
    font-size: 13pt;
    font-weight: 700;
    color: #000000;
    margin-top: 20px;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #dddddd;
  }}
  .summary-wrapper h2:first-child {{ margin-top: 0; }}
  .summary-wrapper h3 {{
    font-size: 11pt;
    font-weight: 600;
    color: #222222;
    margin-top: 15px;
    margin-bottom: 6px;
  }}
  .summary-wrapper p {{
    margin-bottom: 10px;
    color: #222222;
    line-height: 1.6;
    text-align: justify;
  }}
  .summary-wrapper ul, .summary-wrapper ol {{
    padding-left: 20px;
    margin-bottom: 10px;
  }}
  .summary-wrapper li {{
    margin-bottom: 6px;
    color: #222222;
  }}
  .summary-wrapper table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10pt;
    margin-bottom: 15px;
    margin-top: 10px;
  }}
  .summary-wrapper th {{
    background: #f5f5f5;
    color: #000000;
    font-weight: 700;
    padding: 10px;
    text-align: left;
    border: 1px solid #cccccc;
  }}
  .summary-wrapper td {{
    padding: 8px 10px;
    border: 1px solid #dddddd;
    vertical-align: top;
    color: #222222;
  }}
  .summary-wrapper tr:nth-child(even) td {{ background: #fafafa; }}
  .summary-wrapper strong {{ color: #000000; }}
  .summary-wrapper code {{
    background: #f5f5f5;
    border: 1px solid #eeeeee;
    padding: 1px 4px;
    font-size: 9.5pt;
    color: #000000;
  }}
  .summary-wrapper blockquote {{
    border-left: 3px solid #000000;
    margin-left: 0;
    padding-left: 15px;
    color: #444444;
    font-style: italic;
    background: #fafafa;
    padding: 10px 15px;
  }}

  /* ── Divider ── */
  .divider {{
    border: none;
    border-top: 1px solid #000000;
    margin: 30px 0;
  }}

  /* ── Footer ── */
  .footer {{
    border-top: 1px solid #eeeeee;
    padding: 20px 0;
    font-size: 8.5pt;
    color: #888888;
    text-align: center;
    margin-top: 20px;
  }}
  .footer strong {{ color: #000000; }}
</style>
</head>
<body>

<!-- Cover Header -->
<table width="100%" cellpadding="0" cellspacing="0" class="header-container">
  <tr>
    <td>
      <div class="cover-logo">NOTIVO MEETING INTELLIGENCE</div>
      <div class="cover-title">{title}</div>
      <div class="cover-meta">
        {meta_info}
      </div>
    </td>
  </tr>
</table>

<!-- Main Content -->
<div class="content">

  <!-- AI Summary -->
  <div class="section-label">✦ AI Summary</div>
  <div class="summary-wrapper">
    {summary_block}
  </div>



</div>

<!-- Footer -->
<div class="footer">
  Generated by <strong>Notivo</strong> — AI Meeting Recorder<br>
  <span style="color: #bbbbbb; font-size: 8pt;">Exported on {datetime.now().strftime("%d %b %Y at %H:%M")}</span>
</div>

</body>
</html>"""

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar ──
        topbar = QFrame()
        topbar.setFixedHeight(52)
        topbar.setStyleSheet("background-color: #12122a; border-bottom: 1px solid #2a2a4a;")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)

        lbl = QLabel("📄  PDF Preview")
        lbl.setStyleSheet("color: #c4b5fd; font-size: 13px; font-weight: 600;")
        topbar_layout.addWidget(lbl)
        topbar_layout.addStretch()

        hint = QLabel("Review before exporting")
        hint.setStyleSheet("color: #555580; font-size: 11px;")
        topbar_layout.addWidget(hint)

        layout.addWidget(topbar)

        # ── Preview ──
        self.preview = QTextBrowser()
        self.preview.setHtml(self.html_content)
        self.preview.setStyleSheet("""
            QTextBrowser {
                background-color: #e8e8f0;
                border: none;
                padding: 20px;
            }
            QScrollBar:vertical {
                background: #1a1a2e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #4a2aab;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.preview)

        # ── Bottom action bar ──
        actionbar = QFrame()
        actionbar.setFixedHeight(60)
        actionbar.setStyleSheet("background-color: #12122a; border-top: 1px solid #2a2a4a;")
        action_layout = QHBoxLayout(actionbar)
        action_layout.setContentsMargins(20, 0, 20, 0)
        action_layout.setSpacing(10)
        action_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setFixedWidth(100)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9090c0;
                border: 1px solid #3a3a6a;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1e1e40; color: #c4b5fd; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("  💾  Export PDF")
        btn_save.setFixedHeight(36)
        btn_save.setFixedWidth(150)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c3ce0, stop:1 #4a2aab);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c4cf0, stop:1 #5a3abb);
            }
            QPushButton:pressed { background-color: #3a1a9a; }
        """)
        btn_save.clicked.connect(self._save_pdf)

        action_layout.addWidget(btn_cancel)
        action_layout.addWidget(btn_save)
        layout.addWidget(actionbar)

    def _save_pdf(self):
        safe_title = "".join(c for c in self.pdf_title if c.isalnum() or c in " _-").strip()
        default_name = f"Notivo - {safe_title}.pdf" if safe_title else "Notivo_Report.pdf"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", default_name, "PDF Files (*.pdf)"
        )
        if not filename:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filename)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

        self.preview.document().print_(printer)

        msg = QMessageBox(self)
        msg.setWindowTitle("Export Successful")
        msg.setText(f"✅ PDF saved successfully!")
        msg.setInformativeText(filename)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1a1a2e; color: white; }
            QLabel { color: white; }
            QPushButton { background: #6c3ce0; color: white; border-radius: 6px;
                          padding: 6px 20px; border: none; }
        """)
        msg.exec()
        self.accept()
