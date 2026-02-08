import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(settings.GOOGLE_DRIVE_CREDENTIALS_PATH),
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def validate_file_id(file_id: str) -> dict:
    service = get_drive_service()
    meta = service.files().get(
        fileId=file_id,
        fields="id,name,mimeType,size"
    ).execute()
    return meta

def get_binary_download_url(file_id: str) -> str | None:
    """
    Works best for normal files (zip, txt, png, etc.)
    Returns a Google-hosted download link if available.
    """
    service = get_drive_service()
    meta = service.files().get(
        fileId=file_id,
        fields="webContentLink, mimeType, name"
    ).execute()
    return meta.get("webContentLink")

def download_file_bytes(file_id: str):
    """
    Downloads a normal Drive file (zip/txt/png/pdf) using the service account.
    Returns: (filename, mimetype, BytesIO)
    """
    service = get_drive_service()

    meta = service.files().get(
        fileId=file_id,
        fields="name,mimeType",
        supportsAllDrives=True
    ).execute()

    request = service.files().get_media(
        fileId=file_id,
        supportsAllDrives=True
        )

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)  # 1MB chunks

    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    return meta["name"], meta["mimeType"], fh