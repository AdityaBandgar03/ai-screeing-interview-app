from types import SimpleNamespace
from murf import Murf
from app.providers.tts.base import TTSProvider


class MurfTTSProvider(TTSProvider):

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        audio_format: str = "WAV",
        timeout: float = 120,
    ):
        self.client = Murf(api_key=api_key, timeout=timeout)
        self.voice_id = voice_id
        self.audio_format = audio_format

    def synthesize(self, text: str):
        res = self.client.text_to_speech.generate(
            text=text,
            voice_id=self.voice_id,
            format=self.audio_format
        )

        audio_url = res.audio_file

        if not audio_url:
            raise Exception("Murf did not return audio file URL")

        return SimpleNamespace(
            mime_type=self._resolve_mime(),
            bytes_data=None,
            url=audio_url,
        )

    def _resolve_mime(self):
        mapping = {
            "WAV": "audio/wav",
            "MP3": "audio/mpeg",
            "FLAC": "audio/flac",
            "OGG": "audio/ogg",
        }
        return mapping.get(self.audio_format.upper(), "audio/wav")
