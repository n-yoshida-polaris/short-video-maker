from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.oauth2.credentials


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    def __init__(self, client_secrets_path: str, token_path: str):
        self.client_secrets_path = client_secrets_path
        self.token_path = token_path
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        self.creds = None

    def _ensure_creds(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
        self.creds = creds

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        category_id: str = "22",
        privacy_status: str = "private",
        made_for_kids: bool = False,
    ) -> Dict[str, Any]:
        self._ensure_creds()
        youtube = build("youtube", "v3", credentials=self.creds)

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }
        if tags:
            body["snippet"]["tags"] = tags

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        try:
            request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                # We could log progress here
            video_id = response.get("id")
            url = f"https://youtu.be/{video_id}" if video_id else None
            return {"video_id": video_id, "url": url, "response": response}
        except HttpError as e:
            raise RuntimeError(f"YouTube upload failed: {e}")
