from abc import ABC, abstractmethod


class TTSProvider(ABC):

    @abstractmethod
    def synthesize(self, text: str):
        """
        Returns an audio artifact:
        {
            "mime_type": "...",
            "bytes_data": ... OR None,
            "url": ... OR None
        }
        """
        pass
