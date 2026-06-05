from PySide6.QtCore import QThread, Signal
from .ollama_client import OllamaClient
from utils.logger import logger
from utils.config import config
from models.session import Session

class SummaryWorker(QThread):
    summary_finished = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, transcript_file: str, summary_file: str, session: Session = None, language: str = "Indonesian"):
        super().__init__()
        self.transcript_file = transcript_file
        self.summary_file = summary_file
        self.session = session
        self.language = language
        self.client = OllamaClient()
        
    def run(self):
        try:
            with open(self.transcript_file, 'r', encoding='utf-8') as f:
                transcript = f.read()
                
            model = config.get("ollama_model", "llama3.2")
            if not self.client.is_available():
                summary = "AI Summary unavailable"
            else:
                summary = self.client.generate_summary(transcript, model, self.language)
                
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
                
            if self.session:
                self.session.metadata.summary_generated = True
                self.session.save_metadata()
                
            self.summary_finished.emit(summary)
        except Exception as e:
            logger.error(f"SummaryWorker error: {e}")
            self.error_occurred.emit(str(e))
