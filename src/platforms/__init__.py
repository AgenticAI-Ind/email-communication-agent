"""
Platform integration clients for Gmail, Outlook, Slack, Teams
"""

from .gmail_client import GmailClient
from .outlook_client import OutlookClient
from .slack_client import SlackClient
from .teams_client import TeamsClient

__all__ = [
    'GmailClient',
    'OutlookClient',
    'SlackClient',
    'TeamsClient'
]
