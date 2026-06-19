import requests
import json
from utils.logger import logger

class OllamaClient:
    def __init__(self, host="http://localhost:11434"):
        self.host = host
        self.api_url = f"{self.host}/api/generate"
        self.tags_url = f"{self.host}/api/tags"
        
    def is_available(self):
        try:
            response = requests.get(self.tags_url, timeout=3)
            return response.status_code == 200
        except Exception:
            return False
            
    def get_models(self):
        try:
            response = requests.get(self.tags_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Ollama models: {e}")
            return []
            
    def generate_text(self, prompt: str, model: str, timeout: int = 300):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 8192,       # Expand context window for long transcripts
                "num_predict": 2048,   # Allow longer output
                "temperature": 0.3     # More consistent/focused output
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"Ollama error: {response.text}")
                return f"Error from Ollama: {response.status_code}"
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "AI Generation unavailable"

    # Max chars per chunk (~6000 words). Adjust based on model context window.
    CHUNK_SIZE = 12000

    def generate_summary(self, transcript: str, model: str, language: str = "Indonesian"):
        if not transcript.strip():
            return "No transcript available to summarize."

        transcript = transcript.strip()
        char_count = len(transcript)
        word_count = len(transcript.split())
        logger.info(f"Generating summary for transcript: {char_count} chars, ~{word_count} words")

        # If transcript is very long, chunk it first
        if char_count > self.CHUNK_SIZE:
            return self._generate_chunked_summary(transcript, model, language)
        else:
            return self._generate_single_summary(transcript, model, language)

    def _build_summary_prompt(self, transcript: str, model: str, language: str, is_partial: bool = False, part_info: str = "") -> str:
        detail_instruction = (
            "Be THOROUGH and DETAILED. The longer the transcript, the more detail your summary must contain. "
            "Do NOT produce a generic or vague summary. Extract ALL important information including names, "
            "numbers, dates, decisions, tasks, and specific details mentioned."
        )
        partial_note = f"Note: This is {part_info} of the full transcript.\n" if is_partial else ""

        return f"""You are a professional AI assistant specialized in meeting transcription analysis.
{partial_note}
Your task: Analyze the following transcript and produce a COMPREHENSIVE, DETAILED summary.
{detail_instruction}

Write the summary ENTIRELY in {language}. Use this structure (translate headings to {language}):

## Ringkasan Eksekutif
(Paragraf komprehensif yang merangkum seluruh isi percakapan secara menyeluruh. Minimal 3-5 kalimat.)

## Poin-Poin Diskusi Utama
(List SEMUA topik dan poin penting yang dibahas. Sertakan detail spesifik, angka, nama, dan fakta.)

## Keputusan yang Dibuat
(Semua keputusan yang disepakati, termasuk siapa yang memutuskan jika disebutkan.)

## Action Items & Tugas
(Semua tugas atau tindak lanjut yang disebutkan, beserta penanggung jawabnya jika ada.)

## Risiko & Masalah
(Semua masalah, hambatan, atau risiko yang dibahas.)

## Informasi Penting Lainnya
(Nama, tanggal, angka, atau informasi kunci lain yang disebutkan dalam percakapan.)

Output ONLY in {language}. Use neat Markdown. Do NOT fabricate or add information not in the transcript.

Transcript:
{transcript}
"""

    def _generate_single_summary(self, transcript: str, model: str, language: str) -> str:
        prompt = self._build_summary_prompt(transcript, model, language)
        return self.generate_text(prompt, model, timeout=600)

    def _generate_chunked_summary(self, transcript: str, model: str, language: str) -> str:
        """Split long transcript into chunks, summarize each, then merge."""
        chunks = []
        start = 0
        while start < len(transcript):
            end = start + self.CHUNK_SIZE
            # Try to break at a sentence boundary
            if end < len(transcript):
                boundary = transcript.rfind('.', start, end)
                if boundary == -1:
                    boundary = transcript.rfind('\n', start, end)
                if boundary != -1:
                    end = boundary + 1
            chunks.append(transcript[start:end].strip())
            start = end

        total_chunks = len(chunks)
        logger.info(f"Transcript split into {total_chunks} chunks for summarization")

        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            part_info = f"bagian {i+1} dari {total_chunks}"
            prompt = self._build_summary_prompt(chunk, model, language, is_partial=True, part_info=part_info)
            logger.info(f"Summarizing chunk {i+1}/{total_chunks}...")
            chunk_summary = self.generate_text(prompt, model, timeout=600)
            chunk_summaries.append(f"### {part_info.capitalize()}\n{chunk_summary}")

        # Merge all chunk summaries into a final comprehensive summary
        combined = "\n\n---\n\n".join(chunk_summaries)
        merge_prompt = f"""Kamu adalah asisten AI profesional untuk ringkasan rapat.

Berikut adalah ringkasan dari BEBERAPA BAGIAN transkrip yang panjang. 
Tugasmu: Gabungkan semua ringkasan bagian-bagian di bawah ini menjadi SATU ringkasan komprehensif dan lengkap.
Jangan hilangkan informasi penting apapun. Eliminasi duplikasi tapi pertahankan semua detail unik.

Output HANYA dalam {language} dengan format Markdown yang rapi menggunakan struktur:
## Ringkasan Eksekutif
## Poin-Poin Diskusi Utama  
## Keputusan yang Dibuat
## Action Items & Tugas
## Risiko & Masalah
## Informasi Penting Lainnya

Ringkasan bagian-bagian:
{combined}
"""
        logger.info("Merging chunk summaries into final summary...")
        return self.generate_text(merge_prompt, model, timeout=600)
