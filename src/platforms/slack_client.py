"""
Slack integration client
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for messaging"""

    def __init__(self, bot_token: str):
        """
        Initialize Slack client

        Args:
            bot_token: Slack Bot User OAuth Token
        """
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"

    def _get_headers(self) -> Dict:
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.bot_token}',
            'Content-Type': 'application/json'
        }

    def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send a Slack message

        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Optional rich formatting blocks

        Returns:
            Dict with send status and timestamp
        """
        try:
            import requests

            payload = {
                'channel': channel,
                'text': text
            }

            if blocks:
                payload['blocks'] = blocks

            response = requests.post(
                f"{self.base_url}/chat.postMessage",
                headers=self._get_headers(),
                json=payload
            )

            data = response.json()

            if data.get('ok'):
                logger.info(f"Message sent to Slack channel {channel}")
                return {
                    "status": "sent",
                    "channel": channel,
                    "timestamp": data.get('ts')
                }
            else:
                raise Exception(data.get('error', 'Unknown error'))

        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return {"status": "failed", "error": str(e)}

    def get_channel_history(
        self,
        channel: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent messages from a channel

        Args:
            channel: Channel ID
            limit: Number of messages to fetch

        Returns:
            List of message dicts
        """
        try:
            import requests

            response = requests.get(
                f"{self.base_url}/conversations.history",
                headers=self._get_headers(),
                params={'channel': channel, 'limit': limit}
            )

            data = response.json()

            if data.get('ok'):
                messages = []
                for msg in data.get('messages', []):
                    messages.append({
                        'text': msg.get('text', ''),
                        'user': msg.get('user'),
                        'timestamp': msg.get('ts'),
                        'type': msg.get('type')
                    })

                logger.info(f"Fetched {len(messages)} messages from Slack")
                return messages
            else:
                raise Exception(data.get('error'))

        except Exception as e:
            logger.error(f"Error fetching Slack history: {e}")
            return []

    def reply_in_thread(
        self,
        channel: str,
        thread_ts: str,
        text: str
    ) -> Dict:
        """Reply to a thread"""
        try:
            import requests

            payload = {
                'channel': channel,
                'thread_ts': thread_ts,
                'text': text
            }

            response = requests.post(
                f"{self.base_url}/chat.postMessage",
                headers=self._get_headers(),
                json=payload
            )

            data = response.json()

            if data.get('ok'):
                return {"status": "sent", "timestamp": data.get('ts')}
            else:
                raise Exception(data.get('error'))

        except Exception as e:
            logger.error(f"Error replying in thread: {e}")
            return {"status": "failed", "error": str(e)}
