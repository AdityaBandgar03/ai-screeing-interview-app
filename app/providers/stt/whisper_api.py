import io
from openai import AzureOpenAI
from app.providers.stt.base import STTProvider


class AzureWhisperSTTProvider(STTProvider):

    def __init__(self, endpoint: str, api_key: str, deployment_name: str):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-15-preview",
        )
        self.deployment_name = deployment_name

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Sends audio file to Azure Whisper deployment.
        Returns transcript text.
        """
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"

        response = self.client.audio.transcriptions.create(
            file=audio_file,
            model=self.deployment_name,
        )

        return response.text or ""
