import logging
import os

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)


class AudioTranscriber:
    def __init__(self):
        self._client = None

    def _lazy_init(self):
        if self._client is None:
            self._client = Groq(api_key=settings.GROQ_API_KEY)

    def transcribe(self, file_path: str):
        self._lazy_init()
        with open(file_path, "rb") as f:
            transcription = self._client.audio.transcriptions.create(
                file=(os.path.basename(file_path), f.read()),
                model=settings.GROQ_WHISPER_MODEL,
                response_format="verbose_json",
            )

        chunks_data = []
        segments = getattr(transcription, "segments", None) or []
        for segment in segments:
            seg = segment if isinstance(segment, dict) else segment.model_dump()
            text = (seg.get("text") or "").strip()
            if text:
                chunks_data.append({
                    "chunk_text": text,
                    "start_time": seg.get("start"),
                    "end_time": seg.get("end"),
                })

        duration = float(getattr(transcription, "duration", None) or 0.0)
        return chunks_data, duration, len(chunks_data)


transcriber = AudioTranscriber()
