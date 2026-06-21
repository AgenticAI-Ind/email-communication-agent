"""
Smart email triage and categorization
"""

import logging
from typing import Dict, List
from enum import Enum
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class EmailCategory(str, Enum):
    URGENT = "urgent"
    FOLLOW_UP = "follow-up"
    FYI = "fyi"
    SPAM = "spam"


class EmailPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmailTriager:
    """Intelligently categorize and prioritize emails"""

    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)
        self.triage_prompt = PromptTemplate(
            input_variables=["subject", "sender", "body", "context"],
            template="""You are an intelligent email triage assistant.

Email Details:
Subject: {subject}
Sender: {sender}
Body: {body}
Context: {context}

Analyze this email and provide:
1. Category: urgent, follow-up, fyi, or spam
2. Priority: high, medium, or low
3. Reason: Brief explanation (max 50 words)
4. Action Required: Yes/No
5. Suggested Action: What should be done (if applicable)

Respond in this exact format:
CATEGORY: [category]
PRIORITY: [priority]
REASON: [reason]
ACTION_REQUIRED: [yes/no]
SUGGESTED_ACTION: [action or N/A]
"""
        )

    def triage_email(
        self,
        subject: str,
        sender: str,
        body: str,
        context: str = ""
    ) -> Dict:
        """
        Triage a single email

        Args:
            subject: Email subject line
            sender: Email sender address
            body: Email body content
            context: Additional context about sender or conversation

        Returns:
            Dict with category, priority, reason, and suggested action
        """
        try:
            prompt = self.triage_prompt.format(
                subject=subject,
                sender=sender,
                body=body[:1000],  # Limit body length
                context=context or "No prior context"
            )

            response = self.llm.invoke(prompt)

            # Parse response
            result = self._parse_triage_response(response)

            logger.info(f"Triaged email from {sender}: {result['category']}/{result['priority']}")

            return result

        except Exception as e:
            logger.error(f"Error triaging email: {e}")
            return {
                "category": EmailCategory.FYI,
                "priority": EmailPriority.MEDIUM,
                "reason": "Error during triage",
                "action_required": False,
                "suggested_action": "Manual review required"
            }

    def _parse_triage_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        lines = response.strip().split('\n')
        result = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if key == 'category':
                    result['category'] = value.lower()
                elif key == 'priority':
                    result['priority'] = value.lower()
                elif key == 'reason':
                    result['reason'] = value
                elif key == 'action_required':
                    result['action_required'] = value.lower() in ['yes', 'true']
                elif key == 'suggested_action':
                    result['suggested_action'] = value if value != 'N/A' else None

        return result

    def batch_triage(self, emails: List[Dict]) -> List[Dict]:
        """
        Triage multiple emails

        Args:
            emails: List of email dicts with subject, sender, body

        Returns:
            List of triaged email results
        """
        results = []
        for email in emails:
            result = self.triage_email(
                subject=email.get('subject', ''),
                sender=email.get('sender', ''),
                body=email.get('body', ''),
                context=email.get('context', '')
            )
            result['email_id'] = email.get('id')
            results.append(result)

        return results

    def get_urgent_emails(self, triaged_emails: List[Dict]) -> List[Dict]:
        """Filter for urgent emails only"""
        return [
            email for email in triaged_emails
            if email.get('category') == EmailCategory.URGENT
            or email.get('priority') == EmailPriority.HIGH
        ]
