SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

import base64
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class GetEmailAttachments:
    def __init__(self):
        load_dotenv()
        self.invoice_keyword = os.getenv("INVOICE_REGEX", "your redmart invoice")
        self.pdf_mime = os.getenv("PDF_MIME", "application/pdf")
        self.drive_folder_id = os.getenv("DRIVE_FOLDER_ID", "YOUR_GOOGLE_DRIVE_FOLDER_ID")
        self.gmail_service = self.get_gmail_service()
        self.drive_service = self.get_drive_service()

        # Form gmail query
        lookback_days = os.getenv("EMAIL_LOOKBACK_DAYS", "30")
        lookback_days = int(lookback_days)
        today = datetime.utcnow()
        one_month_ago = today - timedelta(days=lookback_days)
        after = int(one_month_ago.timestamp())
        before = int(today.timestamp())
        self.gmail_query = f'after:{after} before:{before} has:attachment "{self.invoice_keyword}"'

    def authenticate_gmail(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_gmail_service(self):
        creds = self.authenticate_gmail()
        return build('gmail', 'v1', credentials=creds)

    def get_drive_service(self):
        creds = self.authenticate_gmail()
        return build('drive', 'v3', credentials=creds)

    def list_drive_pdfs(self):
        """Return existing PDF filenames in Drive so we can skip duplicates."""
        query = (
            f"'{self.drive_folder_id}' in parents "
            f"and mimeType='{self.pdf_mime}' "
            f"and trashed = false"
        )
        files = set()
        page_token = None

        while True:
            response = (
                self.drive_service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(name)",
                    pageToken=page_token,
                )
                .execute()
            )
            files.update(f["name"] for f in response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return files

    def search_emails(self):
        """Run the Gmail query prepared in __init__."""
        results = self.gmail_service.users().messages().list(userId='me', q=self.gmail_query).execute()
        messages = results.get('messages', [])
        return messages

    def get_message(self, msg_id):
        return self.gmail_service.users().messages().get(userId='me', id=msg_id, format='full').execute()

    def extract_pdf_attachments(self, message):
        """Pull (filename, bytes) tuples out of a Gmail message payload."""
        pdf_files = []
        def find_pdfs(parts):
            for part in parts:
                filename = part.get('filename')
                mime_type = part.get('mimeType')
                body = part.get('body', {})
                if filename and mime_type == self.pdf_mime:
                    attachment_id = body.get('attachmentId')
                    if attachment_id:
                        msg_id = message['id'] if 'id' in message else message.get('id')
                        att = self.gmail_service.users().messages().attachments().get(userId='me', messageId=msg_id, id=attachment_id).execute()
                        file_data = base64.urlsafe_b64decode(att['data'].encode('UTF-8'))
                        pdf_files.append((filename, file_data))
                    else:
                        data = body.get('data')
                        if data:
                            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                            pdf_files.append((filename, file_data))
                if 'parts' in part:
                    find_pdfs(part['parts'])
        payload = message.get('payload', {})
        if 'parts' in payload:
            find_pdfs(payload['parts'])
        return pdf_files

    def upload_to_drive(self, filename, file_data):
        temp_path = f'temp_{filename}'
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        file_metadata = {
            'name': filename,
            'parents': [self.drive_folder_id]
        }
        media = MediaFileUpload(temp_path, mimetype=self.pdf_mime)
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        os.remove(temp_path)
        return file.get('id')
