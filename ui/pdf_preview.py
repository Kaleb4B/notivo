from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QTextBrowser, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtPrintSupport import QPrinter

class PDFPreviewDialog(QDialog):
    def __init__(self, title, transcript, summary_html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Preview - Notivo")
        self.resize(800, 900)
        
        self.pdf_title = title
        
        # Build HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 30px; color: #222; }}
                h1 {{ color: #111; border-bottom: 2px solid #ddd; padding-bottom: 10px; font-size: 22pt; margin-bottom: 20px; }}
                h2 {{ color: #2c3e50; margin-top: 25px; font-size: 16pt; }}
                h3 {{ color: #34495e; font-size: 14pt; }}
                p, li {{ line-height: 1.6; font-size: 11pt; color: #333; }}
                .transcript {{ background-color: #f8f9fa; padding: 20px; border-radius: 6px; border-left: 4px solid #adb5bd; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <h1>Notivo Report: {title}</h1>
            
            <h2>AI Summary</h2>
            {summary_html if summary_html else "<p>No summary available.</p>"}
            
            <h2>Transcript</h2>
            <div class="transcript">
                <p>{transcript.replace(chr(10), '<br>')}</p>
            </div>
        </body>
        </html>
        """
        
        self.init_ui(html_content)
        
    def init_ui(self, html_content):
        layout = QVBoxLayout(self)
        
        # Preview Area
        self.preview_browser = QTextBrowser()
        self.preview_browser.setHtml(html_content)
        self.preview_browser.setStyleSheet("background-color: white; color: black; border-radius: 8px;")
        layout.addWidget(self.preview_browser)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Save as PDF")
        self.btn_save.setStyleSheet("background-color: #6c3ce0; color: white;")
        self.btn_save.clicked.connect(self.save_pdf)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
    def save_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{self.pdf_title}.pdf", "PDF Files (*.pdf)")
        if filename:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filename)
            
            self.preview_browser.document().print_(printer)
            
            QMessageBox.information(self, "Success", "PDF exported successfully!")
            self.accept()
