"""Speech-to-text with timestamps (Module 1, step 3) using faster-whisper."""

from config import settings


def merge_segments(segments: list[dict], window_sec: float) -> list[dict]:
    """Merge consecutive Whisper segments into windows of up to ``window_sec`` seconds.

    Whisper segments are often a single short sentence, which embeds and matches poorly;
    a ~30 s window keeps enough context while still pointing at an exact time range.
    """
    merged: list[dict] = []
    for seg in segments:
        text = seg["chunk_text"].strip()
        if not text:
            continue
        if merged and seg["end_time"] - merged[-1]["start_time"] <= window_sec:
            merged[-1]["chunk_text"] += " " + text
            merged[-1]["end_time"] = seg["end_time"]
        else:
            merged.append({"chunk_text": text, "start_time": seg["start_time"], "end_time": seg["end_time"]})
    return merged


class AudioTranscriber:
    def __init__(self):
        self.model_size = settings.WHISPER_MODEL
        self._model = None

    def _lazy_init(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # heavy import, only when audio is ingested

            print("Downloading/Loading Whisper model...")
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def transcribe(self, file_path: str):
        """Returns ``(windows, duration_seconds, n_whisper_segments)``."""
        self._lazy_init()
        segments, info = self._model.transcribe(file_path, beam_size=5)
        raw = [
            {"chunk_text": s.text, "start_time": float(s.start), "end_time": float(s.end)} for s in segments
        ]
        return merge_segments(raw, settings.AUDIO_WINDOW_SEC), float(info.duration), len(raw)


transcriber = AudioTranscriber()
