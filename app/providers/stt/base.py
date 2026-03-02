from abc import ABC, abstractmethod


class STTProvider(ABC):

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        pass
