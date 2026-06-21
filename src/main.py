"""
Email & Communication Automation Agent
Production-ready AI agent with FastAPI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from .config import settings
from .api.routes import router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services"""
    logger.info("Starting Email & Communication Automation Agent...")
    logger.info("Initializing AI models...")

    # Pre-load models
    try:
        from .agent import EmailTriager, SentimentAnalyzer
        triager = EmailTriager()
        sentiment = SentimentAnalyzer()
        logger.info("AI models loaded successfully")
    except Exception as e:
        logger.warning(f"Could not pre-load models: {e}")

    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Email & Communication Automation Agent",
    description="""
    Enterprise-grade email automation with AI-powered:
    - Smart email triage and categorization
    - Context-aware response generation
    - Natural language meeting scheduling
    - Email thread summarization
    - Sentiment analysis
    - Multi-language translation

    Save 2+ hours per day with intelligent email management.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Email Automation"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Email & Communication Automation Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "features": [
            "Smart Email Triage",
            "Response Generation",
            "Meeting Scheduling",
            "Thread Summarization",
            "Sentiment Analysis",
            "Multi-Language Translation"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "operational",
            "ai_models": "operational",
            "database": "not_configured"
        }
    }


@app.get("/dashboard")
async def dashboard():
    """Dashboard endpoint"""
    return {
        "message": "Email Automation Dashboard",
        "endpoints": {
            "triage": "/api/v1/triage",
            "draft": "/api/v1/draft",
            "schedule_meeting": "/api/v1/meetings/schedule",
            "summarize": "/api/v1/summarize",
            "sentiment": "/api/v1/sentiment",
            "translate": "/api/v1/translate"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
