import base64
import os

import google.auth.exceptions
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from googleapiclient.errors import HttpError

class EmailDraft:
    """
    This class represents gmail draft functionality
    """

    def __init__(self, path_to_client_secret_json: str, save_token_to_file: str = 'token.json'):
        self.path_to_client_secret = path_to_client_secret_json
        self.token_file = save_token_to_file
        self.scopes = ['https://mail.google.com/']

        self.credentials = None

    def _write_token_file(self) -> None:
        with open(self.token_file, 'w') as file:
            file.write(self.credentials.to_json())

    def _credential_not_valid_or_expired(self) -> bool:
        if not self.credentials:
            return True

        try:
            return self.credentials.expired or not self.credentials.valid
        except google.auth.exceptions.DefaultCredentialsError:
            return True

    def _is_authenticated(self):
        return not self._credential_not_valid_or_expired()

    def _auth(self) -> None:
        flow = InstalledAppFlow.from_client_secrets_file(self.path_to_client_secret, self.scopes)
        self.credentials = flow.run_local_server(port=0)

    def auth(self) -> None:
        if os.path.exists(self.token_file):
            self.credentials = Credentials.from_authorized_user_file(self.token_file, scopes=self.scopes)
            return

        if self._credential_not_valid_or_expired():
            self.credentials.refresh(Request())
        else:
            self._auth()
            self._write_token_file()

    def draft(self, to_email: str, subject: str, content: str, attached_files_paths: list[str] = None) -> None:
        if not self._is_authenticated():
            raise ValueError("First you need to auth, use auth() method")

        service_gmail = build('gmail', 'v1', credentials=self.credentials)

        mime_message = MIMEMultipart()
        mime_message['to'] = to_email
        mime_message['subject'] = subject
        msg_body = content

        mime_message.attach(MIMEText(msg_body, 'plain'))

        for attached_file in attached_files_paths:
            with open(attached_file, 'rb') as file:
                file_part = MIMEBase('application', 'octet-stream')
                file_part.set_payload(file.read())
                file_part.add_header('Content-Disposition',
                                     'attachment; filename="{0}"'.format(os.path.basename(attached_file)))
                file_part.add_header('Content-Transfer-Encoding', 'base64')

                mime_message.attach(file_part)

        raw_string = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        request_body = {
            'message': {
                'raw': raw_string
            }
        }

        try:
            response = service_gmail.users().drafts().create(userId='me', body=request_body).execute()
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))

        print("Message successfully drafted")


if __name__ == '__main__':
    CLIENT_FILE = './user_data.json'

    account = EmailDraft(CLIENT_FILE)
    account.auth()
    account.draft('redpyl6@gmail.com',
                  'TESTING',
                  'Text content',
                  attached_files_paths=['./token.json'])
