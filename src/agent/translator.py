"""
Multi-language email translation
"""

import logging
from typing import Dict, Optional
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class Translator:
    """Translate emails between languages"""

    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)
        self.translation_prompt = PromptTemplate(
            input_variables=["text", "source_lang", "target_lang"],
            template="""Translate the following text from {source_lang} to {target_lang}.

Maintain:
- Professional tone
- Formatting and structure
- Intent and meaning

Text to translate:
{text}

Translation:"""
        )

        self.detect_prompt = PromptTemplate(
            input_variables=["text"],
            template="""Detect the language of this text. Respond with ONLY the language name (e.g., English, Spanish, French).

Text:
{text}

Language:"""
        )

        # Supported languages
        self.supported_languages = [
            'English', 'Spanish', 'French', 'German', 'Italian',
            'Portuguese', 'Russian', 'Japanese', 'Chinese', 'Korean',
            'Arabic', 'Hindi', 'Dutch', 'Swedish', 'Polish',
            'Turkish', 'Vietnamese', 'Thai', 'Indonesian', 'Hebrew'
        ]

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> Dict:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_language: Target language name
            source_language: Source language (auto-detected if not provided)

        Returns:
            Dict with translated text and metadata
        """
        try:
            # Detect source language if not provided
            if not source_language:
                source_language = self.detect_language(text)

            # Skip if already in target language
            if source_language.lower() == target_language.lower():
                return {
                    "translated_text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "skipped": True
                }

            # Translate
            prompt = self.translation_prompt.format(
                text=text[:2000],  # Limit length
                source_lang=source_language,
                target_lang=target_language
            )

            translated = self.llm.invoke(prompt)

            logger.info(f"Translated from {source_language} to {target_language}")

            return {
                "translated_text": translated.strip(),
                "source_language": source_language,
                "target_language": target_language,
                "character_count": len(translated),
                "skipped": False
            }

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {
                "translated_text": text,  # Return original on error
                "source_language": source_language or "unknown",
                "target_language": target_language,
                "error": str(e)
            }

    def detect_language(self, text: str) -> str:
        """
        Detect the language of text

        Args:
            text: Text to analyze

        Returns:
            Language name
        """
        try:
            prompt = self.detect_prompt.format(text=text[:500])
            response = self.llm.invoke(prompt)

            detected = response.strip()

            # Validate against supported languages
            for lang in self.supported_languages:
                if lang.lower() in detected.lower():
                    return lang

            logger.warning(f"Unknown language detected: {detected}")
            return detected

        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return "English"  # Default fallback

    def translate_email(
        self,
        email: Dict,
        target_language: str
    ) -> Dict:
        """
        Translate an entire email

        Args:
            email: Email dict with subject and body
            target_language: Target language

        Returns:
            Translated email dict
        """
        try:
            # Translate subject
            subject_translation = self.translate(
                text=email.get('subject', ''),
                target_language=target_language
            )

            # Translate body
            body_translation = self.translate(
                text=email.get('body', ''),
                target_language=target_language
            )

            return {
                "subject": subject_translation['translated_text'],
                "body": body_translation['translated_text'],
                "source_language": body_translation['source_language'],
                "target_language": target_language,
                "original_subject": email.get('subject'),
                "original_body": email.get('body')
            }

        except Exception as e:
            logger.error(f"Error translating email: {e}")
            return email  # Return original

    def is_supported_language(self, language: str) -> bool:
        """Check if language is supported"""
        return any(
            lang.lower() == language.lower()
            for lang in self.supported_languages
        )

    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return self.supported_languages.copy()

    def auto_respond_in_sender_language(
        self,
        original_email: str,
        response_text: str
    ) -> Dict:
        """
        Automatically respond in the sender's language

        Args:
            original_email: Original email text (to detect language)
            response_text: Response in English

        Returns:
            Dict with response in appropriate language
        """
        # Detect sender's language
        sender_language = self.detect_language(original_email)

        # If not English, translate response
        if sender_language.lower() != 'english':
            return self.translate(
                text=response_text,
                target_language=sender_language,
                source_language='English'
            )
        else:
            return {
                "translated_text": response_text,
                "source_language": "English",
                "target_language": "English",
                "skipped": True
            }
