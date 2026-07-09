import logging

from faster_whisper import WhisperModel
import os
from config import settings

logger = logging.getLogger(__name__)


class AudioTranscriber:
    def __init__(self):
        self.model_size = settings.WHISPER_MODEL
        self._model = None

    def _lazy_init(self):
        if self._model is None:
            logger.info("Downloading/Loading Whisper model...")
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            
    def transcribe(self, file_path: str):
        self._lazy_init()
        segments, info = self._model.transcribe(file_path, beam_size=5)
        
        chunks_data = []
        duration = info.duration
        
        for segment in segments:
            text = segment.text.strip()
            if text:
                chunks_data.append({
                    "chunk_text": text,
                    "start_time": segment.start,
                    "end_time": segment.end
                })

        return chunks_data, duration, len(chunks_data)

transcriber = AudioTranscriber()
