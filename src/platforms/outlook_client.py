"""
Microsoft Outlook/Graph API integration client
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OutlookClient:
    """Outlook/Microsoft Graph API client"""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str = "common"):
        """
        Initialize Outlook client

        Args:
            client_id: Azure App Client ID
            client_secret: Azure App Client Secret
            tenant_id: Azure Tenant ID (default: 'common' for multi-tenant)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"

    def authenticate(self):
        """Authenticate with Microsoft Graph API"""
        try:
            import msal

            # Create MSAL app
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )

            # Get token
            scopes = [
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Mail.Send",
                "https://graph.microsoft.com/Calendars.ReadWrite"
            ]

            result = app.acquire_token_for_client(scopes=scopes)

            if "access_token" in result:
                self.access_token = result['access_token']
                logger.info("Outlook authentication successful")
            else:
                raise Exception(f"Authentication failed: {result.get('error_description')}")

        except Exception as e:
            logger.error(f"Outlook authentication failed: {e}")
            raise

    def _get_headers(self) -> Dict:
        """Get authorization headers"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")

        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def get_inbox(
        self,
        max_results: int = 10,
        folder: str = "inbox",
        filter_query: str = ""
    ) -> List[Dict]:
        """
        Fetch emails from Outlook inbox

        Args:
            max_results: Maximum number of emails
            folder: Mail folder (inbox, sent, drafts)
            filter_query: OData filter query

        Returns:
            List of email dicts
        """
        try:
            import requests

            url = f"{self.graph_endpoint}/me/mailFolders/{folder}/messages"
            params = {
                '$top': max_results,
                '$orderby': 'receivedDateTime DESC'
            }

            if filter_query:
                params['$filter'] = filter_query

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params
            )

            response.raise_for_status()
            data = response.json()

            emails = []
            for message in data.get('value', []):
                emails.append(self._parse_message(message))

            logger.info(f"Fetched {len(emails)} emails from Outlook")
            return emails

        except Exception as e:
            logger.error(f"Error fetching Outlook inbox: {e}")
            return []

    def _parse_message(self, message: Dict) -> Dict:
        """Parse Outlook message format"""
        return {
            'id': message.get('id'),
            'thread_id': message.get('conversationId'),
            'subject': message.get('subject', ''),
            'sender': message.get('from', {}).get('emailAddress', {}).get('address', ''),
            'recipients': [
                recipient['emailAddress']['address']
                for recipient in message.get('toRecipients', [])
            ],
            'timestamp': message.get('receivedDateTime'),
            'body': message.get('body', {}).get('content', ''),
            'body_type': message.get('body', {}).get('contentType', 'text'),
            'is_read': message.get('isRead', False),
            'importance': message.get('importance', 'normal')
        }

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        importance: str = "normal"
    ) -> Dict:
        """
        Send an email via Outlook

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (HTML or text)
            cc: CC recipients
            bcc: BCC recipients
            importance: low, normal, high

        Returns:
            Dict with send status
        """
        try:
            import requests

            # Prepare recipients
            to_recipients = [{"emailAddress": {"address": to}}]

            cc_recipients = [
                {"emailAddress": {"address": addr}} for addr in (cc or [])
            ]

            bcc_recipients = [
                {"emailAddress": {"address": addr}} for addr in (bcc or [])
            ]

            # Create message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": body
                    },
                    "toRecipients": to_recipients,
                    "ccRecipients": cc_recipients,
                    "bccRecipients": bcc_recipients,
                    "importance": importance
                },
                "saveToSentItems": True
            }

            # Send
            url = f"{self.graph_endpoint}/me/sendMail"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=message
            )

            response.raise_for_status()

            logger.info(f"Email sent to {to} via Outlook")

            return {
                "status": "sent",
                "to": to,
                "subject": subject
            }

        except Exception as e:
            logger.error(f"Error sending Outlook email: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def reply_to_email(
        self,
        message_id: str,
        reply_body: str
    ) -> Dict:
        """Reply to an Outlook email"""
        try:
            import requests

            url = f"{self.graph_endpoint}/me/messages/{message_id}/reply"

            reply_data = {
                "comment": reply_body
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json=reply_data
            )

            response.raise_for_status()

            logger.info(f"Replied to Outlook message {message_id}")

            return {
                "status": "sent",
                "message_id": message_id
            }

        except Exception as e:
            logger.error(f"Error replying to Outlook email: {e}")
            return {"status": "failed", "error": str(e)}

    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        try:
            import requests

            url = f"{self.graph_endpoint}/me/messages/{message_id}"

            response = requests.patch(
                url,
                headers=self._get_headers(),
                json={"isRead": True}
            )

            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return False

    def create_calendar_event(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        location: str = ""
    ) -> Dict:
        """Create a calendar event"""
        try:
            import requests

            event = {
                "subject": subject,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC"
                },
                "location": {
                    "displayName": location
                },
                "attendees": [
                    {
                        "emailAddress": {"address": email},
                        "type": "required"
                    }
                    for email in attendees
                ]
            }

            url = f"{self.graph_endpoint}/me/events"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=event
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Created calendar event: {subject}")

            return {
                "status": "created",
                "event_id": data.get('id'),
                "subject": subject,
                "start_time": start_time,
                "end_time": end_time
            }

        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {"status": "failed", "error": str(e)}
