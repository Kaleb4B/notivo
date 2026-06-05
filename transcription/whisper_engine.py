from faster_whisper import WhisperModel
from utils.logger import logger
import torch

class WhisperEngine:
    def __init__(self):
        self.model = None
        self.current_model_size = None
        
    def load_model(self, model_size: str):
        if self.model is not None and self.current_model_size == model_size:
            return
            
        logger.info(f"Loading Whisper model: {model_size}")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Mac CPU falls back to fp32 by default which is very slow for large models. 
            # Force INT8 quantization to massively speed up (2-3x) inference with negligible accuracy drop.
            compute_type = "float16" if device == "cuda" else "int8"
            
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self.current_model_size = model_size
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e
            
    def transcribe(self, audio_data, language="auto"):
        if not self.model:
            return ""
        try:
            lang = None if language == "auto" else language
            
            # Initial prompt gives the model context about the domain vocabulary
            context_prompt = "Berikut adalah transkripsi rapat tentang Notivo, Python, AI, dan database."
            
            segments, info = self.model.transcribe(
                audio_data, 
                language=lang, 
                beam_size=5,
                vad_filter=True,  # Built-in VAD completely eliminates silence hallucinations
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False,
                initial_prompt=context_prompt,
                no_speech_threshold=0.5
            )
            text = " ".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
