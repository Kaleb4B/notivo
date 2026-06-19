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
            
    # Known Whisper hallucination phrases to filter out
    HALLUCINATION_PATTERNS = [
        "berikut adalah transkripsi",
        "terima kasih telah menonton",
        "terima kasih banyak-banyak",
        "sampai jumpa lagi",
        "thank you for watching",
        "sottotitoli creati",
        "amara.org",
        "ご覧いただき",
        # Greek/other foreign language hallucinations from silence
        "συνταγη",
    ]

    def transcribe(self, audio_data, language="auto"):
        if not self.model:
            return ""
        try:
            lang = None if language == "auto" else language

            # NOTE: Do NOT use initial_prompt with topic-specific text.
            # Whisper will hallucinate and repeat the prompt verbatim during silence.
            # Use a minimal/neutral prompt only if needed for language hints.

            segments, info = self.model.transcribe(
                audio_data,
                language=lang,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
                condition_on_previous_text=False,
                no_speech_threshold=0.6,       # Higher = stricter, fewer hallucinations
                log_prob_threshold=-1.0,        # Discard very low-confidence segments
                compression_ratio_threshold=2.2 # Filter repetitive/compressed hallucinations
            )

            # Filter out hallucinated segments by log probability and known patterns
            clean_texts = []
            for seg in segments:
                text = seg.text.strip()
                if not text:
                    continue
                # Skip very low probability segments (likely hallucination)
                if hasattr(seg, 'no_speech_prob') and seg.no_speech_prob > 0.6:
                    logger.debug(f"Skipped low-prob segment: {text[:50]}")
                    continue
                # Skip known hallucination phrases
                if self._is_hallucination(text):
                    logger.debug(f"Filtered hallucination: {text[:60]}")
                    continue
                clean_texts.append(text)

            return " ".join(clean_texts).strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def _is_hallucination(self, text: str) -> bool:
        """Return True if text matches a known Whisper hallucination pattern."""
        normalized = text.lower().strip()
        for pattern in self.HALLUCINATION_PATTERNS:
            if pattern in normalized:
                return True
        # Also filter very short non-word outputs (single punctuation, etc.)
        if len(normalized.replace('.', '').replace(',', '').strip()) < 2:
            return True
        return False
