"""
Microsoft Teams integration client
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class TeamsClient:
    """Microsoft Teams webhook client"""

    def __init__(self, webhook_url: str):
        """
        Initialize Teams client

        Args:
            webhook_url: Incoming webhook URL for Teams channel
        """
        self.webhook_url = webhook_url

    def send_message(
        self,
        text: str,
        title: Optional[str] = None,
        color: str = "0078D4"
    ) -> Dict:
        """
        Send a message to Teams channel

        Args:
            text: Message text
            title: Optional message title
            color: Hex color for message card

        Returns:
            Dict with send status
        """
        try:
            import requests

            # Create adaptive card
            card = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "themeColor": color,
                "text": text
            }

            if title:
                card["title"] = title

            response = requests.post(
                self.webhook_url,
                json=card
            )

            response.raise_for_status()

            logger.info("Message sent to Teams")

            return {
                "status": "sent",
                "text": text
            }

        except Exception as e:
            logger.error(f"Error sending Teams message: {e}")
            return {"status": "failed", "error": str(e)}

    def send_adaptive_card(
        self,
        card_json: Dict
    ) -> Dict:
        """
        Send a custom adaptive card

        Args:
            card_json: Adaptive card JSON

        Returns:
            Dict with send status
        """
        try:
            import requests

            response = requests.post(
                self.webhook_url,
                json=card_json
            )

            response.raise_for_status()

            logger.info("Adaptive card sent to Teams")

            return {"status": "sent"}

        except Exception as e:
            logger.error(f"Error sending adaptive card: {e}")
            return {"status": "failed", "error": str(e)}
