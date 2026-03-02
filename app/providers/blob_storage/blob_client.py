from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas


def _parse_connection_string(connection_string: str) -> tuple[str, str]:
    """Return (account_name, account_key)."""
    conn_dict = {}
    for part in connection_string.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            conn_dict[k.strip()] = v.strip()
    account_name = conn_dict.get("AccountName")
    account_key = conn_dict.get("AccountKey")
    if not account_name or not account_key:
        raise ValueError("Connection string must contain AccountName and AccountKey")
    return account_name, account_key


class AudioStorageService:

    def __init__(self, connection_string: str, container_name: str):
        self._connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        self.container_name = container_name

    def generate_read_sas_url(self, blob_path: str, expiry_hours: int = 24) -> str:
        """Return a URL with read-only SAS for the given blob path (e.g. for audio playback)."""
        account_name, account_key = _parse_connection_string(self._connection_string)
        if blob_path.startswith(self.container_name + "/"):
            blob_path = blob_path[len(self.container_name) + 1 :]
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        encoded_blob_name = quote(blob_path, safe="/")
        return f"https://{account_name}.blob.core.windows.net/{self.container_name}/{encoded_blob_name}?{sas_token}"

    def upload_from_url(self, audio_url: str, session_id: str, question_index: int):

        # 1️⃣ Download from Murf
        response = requests.get(audio_url)
        if response.status_code != 200:
            raise Exception("Failed to download Murf audio")

        audio_bytes = response.content

        # 2️⃣ Create blob path
        blob_path = f"{session_id}/questions/q{question_index}.wav"

        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path,
        )

        blob_client.upload_blob(audio_bytes, overwrite=True)

        return self.generate_read_sas_url(blob_path)

    def generate_video_upload_sas(self, session_id: str, expiry_hours: int = 1):
        """Return (upload_url, blob_path) for client-side video upload."""
        blob_path = f"videos/{session_id}.webm"
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path,
        )
        account_name, account_key = _parse_connection_string(self._connection_string)
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(create=True, write=True),
            expiry=expiry,
        )
        upload_url = f"{blob_client.url}?{sas_token}"
        return upload_url, blob_path
