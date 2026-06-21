"""
Context-aware email response generation
"""

import logging
from typing import Dict, List, Optional
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate contextual email responses"""

    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)
        self.response_prompt = PromptTemplate(
            input_variables=["email_body", "sender", "context", "tone", "style"],
            template="""You are a professional email response assistant.

Original Email:
From: {sender}
{email_body}

Context: {context}

Write a {tone} email response in a {style} style.

Requirements:
- Be professional and courteous
- Address the sender's points directly
- Keep response focused and clear
- Match the requested tone and style
- Include appropriate greeting and closing

Email Response:
"""
        )

    def draft_response(
        self,
        email_body: str,
        sender: str,
        context: str = "",
        tone: str = "professional",
        style: str = "concise",
        template_name: Optional[str] = None
    ) -> Dict:
        """
        Draft an email response

        Args:
            email_body: Content of the email to respond to
            sender: Email sender
            context: Additional context about the conversation
            tone: Response tone (professional, friendly, formal)
            style: Response style (concise, detailed)
            template_name: Optional template to use

        Returns:
            Dict with drafted response and metadata
        """
        try:
            if template_name:
                response_text = self._apply_template(
                    template_name,
                    sender=sender,
                    email_body=email_body
                )
            else:
                prompt = self.response_prompt.format(
                    email_body=email_body[:2000],
                    sender=sender,
                    context=context or "No prior context",
                    tone=tone,
                    style=style
                )

                response_text = self.llm.invoke(prompt)

            # Post-process response
            response_text = self._post_process_response(response_text)

            logger.info(f"Generated response for email from {sender}")

            return {
                "text": response_text,
                "tone": tone,
                "style": style,
                "word_count": len(response_text.split()),
                "template_used": template_name
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "text": "Thank you for your email. I will review and respond shortly.",
                "tone": tone,
                "style": "concise",
                "error": str(e)
            }

    def _apply_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """Apply a response template with personalization"""
        templates = {
            "meeting_confirmation": """Dear {sender},

Thank you for your email. I confirm our meeting as discussed.

I look forward to speaking with you.

Best regards""",

            "out_of_office": """Thank you for your email.

I am currently out of the office and will return on [DATE]. I will respond to your message when I return.

For urgent matters, please contact [CONTACT].

Best regards""",

            "acknowledgment": """Dear {sender},

Thank you for reaching out. I have received your email and will review it carefully.

I will get back to you within [TIMEFRAME].

Best regards""",

            "follow_up": """Dear {sender},

Following up on my previous email regarding [TOPIC].

I wanted to check if you had any questions or needed additional information.

Looking forward to your response.

Best regards"""
        }

        template = templates.get(template_name, templates["acknowledgment"])
        return template.format(**kwargs)

    def _post_process_response(self, response: str) -> str:
        """Clean up and format the response"""
        # Remove any system prompts or artifacts
        response = response.strip()

        # Ensure proper spacing
        lines = response.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        return '\n\n'.join(cleaned_lines)

    def generate_multiple_drafts(
        self,
        email_body: str,
        sender: str,
        num_drafts: int = 3
    ) -> List[Dict]:
        """
        Generate multiple response options

        Args:
            email_body: Original email content
            sender: Email sender
            num_drafts: Number of drafts to generate

        Returns:
            List of draft responses with different tones/styles
        """
        styles = [
            ("professional", "concise"),
            ("friendly", "detailed"),
            ("formal", "concise")
        ]

        drafts = []
        for i, (tone, style) in enumerate(styles[:num_drafts]):
            draft = self.draft_response(
                email_body=email_body,
                sender=sender,
                tone=tone,
                style=style
            )
            draft['option'] = i + 1
            drafts.append(draft)

        return drafts

    def personalize_response(
        self,
        draft: str,
        sender_name: str,
        sender_history: Optional[Dict] = None
    ) -> str:
        """
        Personalize a draft response based on sender history

        Args:
            draft: Base draft text
            sender_name: Name of recipient
            sender_history: Previous interactions with sender

        Returns:
            Personalized response text
        """
        # Add personal greeting if name is available
        if sender_name and not draft.startswith("Dear"):
            draft = f"Dear {sender_name},\n\n{draft}"

        # Add context from history if available
        if sender_history and sender_history.get('last_topic'):
            topic = sender_history['last_topic']
            context_line = f"\n\nRegarding our previous discussion about {topic},"
            # Insert after greeting
            lines = draft.split('\n')
            lines.insert(2, context_line)
            draft = '\n'.join(lines)

        return draft
