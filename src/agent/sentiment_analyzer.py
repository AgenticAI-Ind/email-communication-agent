"""
Email sentiment analysis for emotion detection
"""

import logging
from typing import Dict, List
from transformers import pipeline
import re

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment and emotion in emails"""

    def __init__(self):
        """Initialize sentiment analysis pipeline"""
        try:
            # Use lightweight sentiment model
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english"
            )
            self.emotion_keywords = self._load_emotion_keywords()
            logger.info("Sentiment analyzer initialized")
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
            self.sentiment_pipeline = None

    def analyze_sentiment(self, email_body: str) -> Dict:
        """
        Analyze sentiment of email

        Args:
            email_body: Email content to analyze

        Returns:
            Dict with sentiment, confidence, emotion, and urgency
        """
        try:
            # Clean text
            cleaned_text = self._preprocess_text(email_body)

            # Get sentiment from transformer model
            if self.sentiment_pipeline:
                result = self.sentiment_pipeline(cleaned_text[:512])[0]
                sentiment = result['label'].lower()
                confidence = result['score']
            else:
                # Fallback to keyword-based
                sentiment, confidence = self._keyword_sentiment(cleaned_text)

            # Detect specific emotions
            emotions = self._detect_emotions(cleaned_text)

            # Check urgency indicators
            urgency = self._detect_urgency(email_body)

            # Determine overall tone
            tone = self._determine_tone(sentiment, emotions, urgency)

            logger.debug(f"Analyzed sentiment: {sentiment} ({confidence:.2f})")

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "emotions": emotions,
                "urgency": urgency,
                "tone": tone,
                "requires_careful_response": self._needs_careful_response(
                    sentiment, emotions, urgency
                )
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": [],
                "urgency": "normal",
                "error": str(e)
            }

    def _preprocess_text(self, text: str) -> str:
        """Clean and prepare text for analysis"""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _keyword_sentiment(self, text: str) -> tuple:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()

        positive_words = [
            'thank', 'great', 'excellent', 'wonderful', 'appreciate',
            'happy', 'glad', 'pleased', 'perfect', 'awesome'
        ]

        negative_words = [
            'unfortunately', 'problem', 'issue', 'error', 'wrong',
            'frustrated', 'disappointed', 'concerned', 'urgent', 'critical'
        ]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            return 'positive', 0.6 + (pos_count * 0.1)
        elif neg_count > pos_count:
            return 'negative', 0.6 + (neg_count * 0.1)
        else:
            return 'neutral', 0.5

    def _detect_emotions(self, text: str) -> List[str]:
        """Detect specific emotions in text"""
        text_lower = text.lower()
        detected = []

        for emotion, keywords in self.emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected.append(emotion)

        return detected

    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level"""
        text_lower = text.lower()

        high_urgency = [
            'urgent', 'asap', 'immediately', 'critical', 'emergency',
            'right away', 'time sensitive', 'deadline'
        ]

        medium_urgency = [
            'soon', 'quickly', 'at your earliest', 'priority',
            'important', 'need to'
        ]

        # Check for exclamation marks
        exclamation_count = text.count('!')

        if any(word in text_lower for word in high_urgency) or exclamation_count >= 3:
            return 'high'
        elif any(word in text_lower for word in medium_urgency) or exclamation_count >= 1:
            return 'medium'
        else:
            return 'normal'

    def _determine_tone(
        self,
        sentiment: str,
        emotions: List[str],
        urgency: str
    ) -> str:
        """Determine overall tone of email"""
        if 'angry' in emotions or 'frustrated' in emotions:
            return 'angry'
        elif urgency == 'high':
            return 'urgent'
        elif sentiment == 'negative':
            return 'concerned'
        elif 'excited' in emotions:
            return 'enthusiastic'
        elif sentiment == 'positive':
            return 'friendly'
        else:
            return 'professional'

    def _needs_careful_response(
        self,
        sentiment: str,
        emotions: List[str],
        urgency: str
    ) -> bool:
        """Determine if email requires extra careful response"""
        # Flag for manual review
        risky_emotions = ['angry', 'frustrated', 'disappointed']
        has_risky_emotion = any(emotion in emotions for emotion in risky_emotions)

        return (
            sentiment == 'negative' or
            has_risky_emotion or
            urgency == 'high'
        )

    def _load_emotion_keywords(self) -> Dict[str, List[str]]:
        """Load emotion keyword mappings"""
        return {
            "angry": [
                "angry", "furious", "outraged", "mad", "unacceptable",
                "ridiculous", "terrible", "horrible", "worst"
            ],
            "frustrated": [
                "frustrated", "annoyed", "irritated", "bothered",
                "upset", "dissatisfied"
            ],
            "disappointed": [
                "disappointed", "let down", "expected better",
                "unfortunate", "regret"
            ],
            "worried": [
                "worried", "concerned", "anxious", "nervous",
                "uncertain", "unsure"
            ],
            "excited": [
                "excited", "thrilled", "eager", "looking forward",
                "can't wait", "enthusiastic"
            ],
            "happy": [
                "happy", "glad", "pleased", "delighted",
                "satisfied", "content"
            ],
            "grateful": [
                "thank", "grateful", "appreciate", "thankful",
                "gratitude"
            ]
        }

    def batch_analyze(self, emails: List[Dict]) -> List[Dict]:
        """
        Analyze sentiment for multiple emails

        Args:
            emails: List of email dicts with body content

        Returns:
            List of sentiment analysis results
        """
        results = []
        for email in emails:
            body = email.get('body', '')
            sentiment = self.analyze_sentiment(body)
            sentiment['email_id'] = email.get('id')
            results.append(sentiment)

        return results

    def get_negative_emails(self, analyzed_emails: List[Dict]) -> List[Dict]:
        """Filter for emails with negative sentiment"""
        return [
            email for email in analyzed_emails
            if email.get('sentiment') == 'negative'
            or email.get('requires_careful_response')
        ]
