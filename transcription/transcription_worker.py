import queue
import numpy as np
from PySide6.QtCore import QThread, Signal
from .whisper_engine import WhisperEngine
from utils.logger import logger
from utils.constants import SAMPLE_RATE
from utils.config import config
import torch

class TranscriptionWorker(QThread):
    text_transcribed = Signal(str)       # Final committed text for a speech segment
    interim_transcribed = Signal(str)    # Interim partial text for real-time feedback
    speech_status = Signal(bool)         # True = speaking, False = silent
    status_message = Signal(str)         # Loading status for UI
    error_occurred = Signal(str)
    
    def __init__(self, audio_queue: queue.Queue):
        super().__init__()
        self.audio_queue = audio_queue
        self.is_running = False
        self.engine = WhisperEngine()
        self.vad_model = None
        
    def load_vad(self):
        try:
            logger.info("Loading Silero VAD")
            model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                          model='silero_vad',
                                          force_reload=False,
                                          trust_repo=True)
            self.vad_model = model
            logger.info("Silero VAD loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load VAD: {e}")
            raise e
            
    def _is_speech(self, audio_chunk_np):
        """Run VAD on a single chunk. Returns True if speech detected in any 512-sample window."""
        try:
            # Silero VAD requires exactly 512 samples per call at 16kHz
            WINDOW = 512
            for i in range(0, len(audio_chunk_np) - WINDOW + 1, WINDOW):
                window = audio_chunk_np[i:i + WINDOW]
                tensor = torch.from_numpy(window).float()
                prob = self.vad_model(tensor, SAMPLE_RATE).item()
                if prob > 0.45:
                    return True
            return False
        except Exception as e:
            logger.error(f"VAD chunk error: {e}")
            return False
            
    def run(self):
        self.is_running = True
        try:
            model_size = config.get("whisper_model", "tiny")
            self.status_message.emit(f"Loading Whisper model '{model_size}'... (first time may download)")
            self.engine.load_model(model_size)
            self.status_message.emit("Loading VAD model...")
            self.load_vad()
            self.status_message.emit("")
        except Exception as e:
            self.error_occurred.emit(f"Initialization error: {e}")
            return

        # Segment-based approach:
        # 1. Accumulate audio only while speech is happening
        # 2. When silence is detected after speech, transcribe that segment
        # 3. Emit the result as committed text (never re-transcribed)
        
        speech_buffer = []          # Chunks of audio during current speech segment
        is_speaking = False         # Whether we're in a speech segment
        silent_samples = 0          # How many consecutive silent samples after speech
        current_samples = 0         # Total samples in current speech_buffer
        SILENCE_THRESHOLD = int(16000 * 1.5)  # 1.5s silence before final commit
        MAX_SAMPLES = int(16000 * 15)         # Force final commit after 15s to prevent buffer growing too large
        
        import time
        
        while self.is_running or not self.audio_queue.empty():
            try:
                # 1. Block for at least one chunk if running
                if self.is_running:
                    first_chunk = self.audio_queue.get(timeout=0.5)
                else:
                    first_chunk = self.audio_queue.get_nowait()
                    
                chunks_to_process = [first_chunk.flatten()]
                
                # 2. Drain all other pending chunks to catch up instantly
                while not self.audio_queue.empty():
                    try:
                        chunks_to_process.append(self.audio_queue.get_nowait().flatten())
                    except queue.Empty:
                        break
                        
                # 3. Process the batched chunks
                combined_chunk = np.concatenate(chunks_to_process)
                has_speech = self._is_speech(combined_chunk)
                
                if has_speech:
                    if not is_speaking:
                        is_speaking = True
                        self.speech_status.emit(True)
                    speech_buffer.append(combined_chunk)
                    current_samples += len(combined_chunk)
                    silent_samples = 0
                elif is_speaking:
                    speech_buffer.append(combined_chunk)
                    current_samples += len(combined_chunk)
                    silent_samples += len(combined_chunk)
                
                # 4. Make commit decisions on the up-to-date state
                if is_speaking:
                    
                    # Force final commit if segment is extremely long
                    if current_samples >= MAX_SAMPLES:
                        self._commit_segment(speech_buffer, final=True)
                        speech_buffer = []
                        is_speaking = False
                        current_samples = 0
                        silent_samples = 0
                        self.speech_status.emit(False)
                        
                    # Final commit if user paused
                    elif silent_samples >= SILENCE_THRESHOLD:
                        self._commit_segment(speech_buffer, final=True)
                        speech_buffer = []
                        is_speaking = False
                        current_samples = 0
                        silent_samples = 0
                        self.speech_status.emit(False)
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Transcription loop error: {e}")
                
        # Flush remaining buffer on stop
        if len(speech_buffer) > 0:
            self._commit_segment(speech_buffer, final=True, force=True)
            
    def _commit_segment(self, speech_buffer, final=True, force=False):
        """Transcribe a speech segment and emit the result."""
        if not force and len(speech_buffer) < 2:
            return  # Discard if it's less than 1 second (noise)
            
        audio_data = np.concatenate(speech_buffer)
        lang = config.get("language", "auto")
        try:
            text = self.engine.transcribe(audio_data, language=lang)
            if text:
                # Clean up Whisper hallucinations (trailing dots and spaces)
                text = text.strip()
                while text.endswith('.') or text.endswith(' '):
                    text = text[:-1].strip()
                    
                if not text:
                    return
                    
                if final:
                    self.text_transcribed.emit(text + ".") # Add a single clean period
                else:
                    self.interim_transcribed.emit(text)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
                
    def stop(self):
        self.is_running = False
