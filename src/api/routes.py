"""
API routes for email automation agent
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from ..agent import (
    EmailTriager,
    ResponseGenerator,
    MeetingScheduler,
    EmailSummarizer,
    SentimentAnalyzer,
    Translator
)

router = APIRouter()

# Initialize agents
triager = EmailTriager()
response_gen = ResponseGenerator()
meeting_scheduler = MeetingScheduler()
summarizer = EmailSummarizer()
sentiment_analyzer = SentimentAnalyzer()
translator = Translator()


# Request/Response Models
class EmailRequest(BaseModel):
    subject: str
    sender: EmailStr
    body: str
    context: Optional[str] = ""


class TriageResponse(BaseModel):
    category: str
    priority: str
    reason: str
    action_required: bool
    suggested_action: Optional[str]


class DraftRequest(BaseModel):
    email_id: str
    email_body: str
    sender: EmailStr
    tone: str = "professional"
    style: str = "concise"


class MeetingRequest(BaseModel):
    prompt: str
    organizer_email: EmailStr


class TranslationRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = None


# Routes
@router.post("/triage", response_model=TriageResponse)
async def triage_email(email: EmailRequest):
    """Triage and categorize an email"""
    try:
        result = triager.triage_email(
            subject=email.subject,
            sender=email.sender,
            body=email.body,
            context=email.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft")
async def draft_response(request: DraftRequest):
    """Generate a draft email response"""
    try:
        draft = response_gen.draft_response(
            email_body=request.email_body,
            sender=request.sender,
            tone=request.tone,
            style=request.style
        )
        return draft
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meetings/schedule")
async def schedule_meeting(request: MeetingRequest):
    """Schedule a meeting from natural language"""
    try:
        meeting = meeting_scheduler.schedule_meeting(
            prompt=request.prompt,
            organizer_email=request.organizer_email
        )
        return meeting
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_thread(emails: List[EmailRequest]):
    """Summarize an email thread"""
    try:
        email_dicts = [
            {
                'subject': e.subject,
                'sender': e.sender,
                'body': e.body,
                'timestamp': datetime.now().isoformat()
            }
            for e in emails
        ]

        summary = summarizer.summarize_thread(email_dicts)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment")
async def analyze_sentiment(email: EmailRequest):
    """Analyze email sentiment"""
    try:
        sentiment = sentiment_analyzer.analyze_sentiment(email.body)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate")
async def translate_text(request: TranslationRequest):
    """Translate text to target language"""
    try:
        translation = translator.translate(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        )
        return translation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inbox")
async def get_inbox(
    category: Optional[str] = None,
    limit: int = 10
):
    """Get inbox with smart triage"""
    # Placeholder - would integrate with Gmail/Outlook client
    return {
        "message": "Inbox endpoint - integrate with Gmail/Outlook clients",
        "category": category,
        "limit": limit
    }


@router.get("/analytics")
async def get_analytics(timeframe: str = "last_7_days"):
    """Get email analytics"""
    # Placeholder for analytics
    return {
        "timeframe": timeframe,
        "received": 0,
        "sent": 0,
        "response_rate": 0,
        "avg_response_time": 0,
        "time_saved": 0
    }
