"""
Gmail API integration client
"""

import logging
import base64
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client for email operations"""

    def __init__(self, credentials_path: str = "credentials.json"):
        """
        Initialize Gmail client

        Args:
            credentials_path: Path to OAuth2 credentials file
        """
        self.credentials_path = credentials_path
        self.service = None
        self.user_id = "me"

    def authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import os.path
            import pickle

            SCOPES = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/calendar'
            ]

            creds = None

            # Check for saved credentials
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)

            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            # Build service
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail authentication successful")

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            raise

    def get_inbox(
        self,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None,
        query: str = ""
    ) -> List[Dict]:
        """
        Fetch emails from inbox

        Args:
            max_results: Maximum number of emails to fetch
            label_ids: Filter by label IDs (e.g., ['INBOX', 'UNREAD'])
            query: Gmail search query

        Returns:
            List of email dicts
        """
        try:
            if not self.service:
                raise ValueError("Not authenticated. Call authenticate() first.")

            # Default to inbox
            if not label_ids:
                label_ids = ['INBOX']

            # List messages
            results = self.service.users().messages().list(
                userId=self.user_id,
                labelIds=label_ids,
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            # Fetch full message details
            emails = []
            for message in messages:
                email = self._get_message_detail(message['id'])
                if email:
                    emails.append(email)

            logger.info(f"Fetched {len(emails)} emails from Gmail")
            return emails

        except Exception as e:
            logger.error(f"Error fetching inbox: {e}")
            return []

    def _get_message_detail(self, message_id: str) -> Optional[Dict]:
        """Fetch detailed message information"""
        try:
            message = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format='full'
            ).execute()

            # Parse headers
            headers = message['payload']['headers']
            subject = self._get_header_value(headers, 'Subject')
            sender = self._get_header_value(headers, 'From')
            date = self._get_header_value(headers, 'Date')
            to = self._get_header_value(headers, 'To')

            # Get body
            body = self._get_message_body(message['payload'])

            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': subject,
                'sender': sender,
                'recipients': [to] if to else [],
                'timestamp': date,
                'body': body,
                'labels': message.get('labelIds', []),
                'snippet': message.get('snippet', '')
            }

        except Exception as e:
            logger.error(f"Error getting message detail: {e}")
            return None

    def _get_header_value(self, headers: List[Dict], name: str) -> str:
        """Extract header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ""

    def _get_message_body(self, payload: Dict) -> str:
        """Extract message body from payload"""
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            # Simple message
            data = payload['body'].get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

        return ""

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict:
        """
        Send an email

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            Dict with send status and message ID
        """
        try:
            if not self.service:
                raise ValueError("Not authenticated")

            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)

            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send
            sent_message = self.service.users().messages().send(
                userId=self.user_id,
                body={'raw': raw}
            ).execute()

            logger.info(f"Email sent to {to}: {sent_message['id']}")

            return {
                "status": "sent",
                "message_id": sent_message['id'],
                "to": to,
                "subject": subject
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def reply_to_email(
        self,
        message_id: str,
        reply_body: str
    ) -> Dict:
        """Reply to an existing email"""
        try:
            # Get original message
            original = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id
            ).execute()

            headers = original['payload']['headers']
            subject = self._get_header_value(headers, 'Subject')
            to = self._get_header_value(headers, 'From')
            thread_id = original['threadId']

            # Prepare reply
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"

            message = MIMEText(reply_body)
            message['to'] = to
            message['subject'] = subject
            message['In-Reply-To'] = message_id
            message['References'] = message_id

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send as part of thread
            sent = self.service.users().messages().send(
                userId=self.user_id,
                body={
                    'raw': raw,
                    'threadId': thread_id
                }
            ).execute()

            logger.info(f"Replied to message {message_id}")

            return {
                "status": "sent",
                "message_id": sent['id'],
                "thread_id": thread_id
            }

        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            return {"status": "failed", "error": str(e)}

    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return False

    def add_label(self, message_id: str, label_id: str) -> bool:
        """Add label to email"""
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding label: {e}")
            return False
