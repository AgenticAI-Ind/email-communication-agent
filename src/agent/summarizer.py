"""
Email thread summarization
"""

import logging
from typing import Dict, List
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class EmailSummarizer:
    """Summarize email threads and conversations"""

    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)
        self.summary_prompt = PromptTemplate(
            input_variables=["thread_content", "num_points"],
            template="""Summarize this email conversation in exactly {num_points} key bullet points.

Email Thread:
{thread_content}

Provide {num_points} concise bullet points that capture:
1. Main topics discussed
2. Key decisions made
3. Action items or next steps

Format as:
• Point 1
• Point 2
• Point 3
"""
        )

    def summarize_thread(
        self,
        emails: List[Dict],
        num_points: int = 3
    ) -> Dict:
        """
        Summarize an email thread

        Args:
            emails: List of email dicts with subject, sender, body, timestamp
            num_points: Number of bullet points for summary

        Returns:
            Dict with summary and metadata
        """
        try:
            # Combine email thread
            thread_content = self._format_thread(emails)

            # Generate summary
            prompt = self.summary_prompt.format(
                thread_content=thread_content[:4000],  # Limit context
                num_points=num_points
            )

            response = self.llm.invoke(prompt)

            # Parse bullet points
            key_points = self._parse_bullet_points(response)

            # Extract action items
            action_items = self._extract_action_items(thread_content)

            logger.info(f"Summarized thread with {len(emails)} emails")

            return {
                "key_points": key_points,
                "action_items": action_items,
                "email_count": len(emails),
                "participants": self._get_participants(emails),
                "date_range": self._get_date_range(emails)
            }

        except Exception as e:
            logger.error(f"Error summarizing thread: {e}")
            return {
                "key_points": ["Error generating summary"],
                "action_items": [],
                "error": str(e)
            }

    def _format_thread(self, emails: List[Dict]) -> str:
        """Format email thread for summarization"""
        formatted = []

        for i, email in enumerate(emails, 1):
            formatted.append(f"""
Email {i}:
From: {email.get('sender', 'Unknown')}
Date: {email.get('timestamp', 'Unknown')}
Subject: {email.get('subject', 'No subject')}

{email.get('body', '')[:500]}
---
""")

        return '\n'.join(formatted)

    def _parse_bullet_points(self, response: str) -> List[str]:
        """Extract bullet points from LLM response"""
        lines = response.strip().split('\n')
        points = []

        for line in lines:
            line = line.strip()
            # Match bullets: •, -, *, or numbered
            if line and (line.startswith('•') or line.startswith('-') or
                        line.startswith('*') or line[0].isdigit()):
                # Clean bullet marker
                point = line.lstrip('•-*0123456789. ').strip()
                if point:
                    points.append(point)

        return points

    def _extract_action_items(self, thread_content: str) -> List[str]:
        """Extract action items from thread"""
        # Simple keyword-based extraction
        action_keywords = [
            'will', 'should', 'need to', 'must', 'action item',
            'todo', 'to do', 'task', 'deadline', 'due'
        ]

        sentences = thread_content.split('.')
        action_items = []

        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(keyword in sentence for keyword in action_keywords):
                # Limit length
                if len(sentence) < 200:
                    action_items.append(sentence.capitalize())

        return action_items[:5]  # Return top 5

    def _get_participants(self, emails: List[Dict]) -> List[str]:
        """Get unique participants in thread"""
        participants = set()
        for email in emails:
            sender = email.get('sender', '')
            if sender:
                participants.add(sender)

            # Add recipients if available
            recipients = email.get('recipients', [])
            participants.update(recipients)

        return sorted(list(participants))

    def _get_date_range(self, emails: List[Dict]) -> Dict:
        """Get date range of thread"""
        if not emails:
            return {"start": None, "end": None}

        timestamps = [
            email.get('timestamp') for email in emails
            if email.get('timestamp')
        ]

        if not timestamps:
            return {"start": None, "end": None}

        return {
            "start": min(timestamps),
            "end": max(timestamps)
        }

    def summarize_single_email(
        self,
        email_body: str,
        max_length: int = 100
    ) -> str:
        """
        Generate a brief summary of a single email

        Args:
            email_body: Email content
            max_length: Maximum summary length in words

        Returns:
            Summary string
        """
        try:
            prompt = f"""Summarize this email in {max_length} words or less:

{email_body[:2000]}

Summary:"""

            summary = self.llm.invoke(prompt)
            return summary.strip()

        except Exception as e:
            logger.error(f"Error summarizing single email: {e}")
            # Fallback: take first 100 words
            words = email_body.split()[:max_length]
            return ' '.join(words) + '...'

    def extract_main_topic(self, emails: List[Dict]) -> str:
        """Extract the main topic/theme of the thread"""
        try:
            thread_content = self._format_thread(emails)

            prompt = f"""What is the main topic of this email conversation? Answer in 5 words or less.

{thread_content[:1000]}

Main topic:"""

            topic = self.llm.invoke(prompt)
            return topic.strip()

        except Exception as e:
            logger.error(f"Error extracting topic: {e}")
            # Fallback to first email subject
            if emails and emails[0].get('subject'):
                return emails[0]['subject']
            return "Unknown topic"
