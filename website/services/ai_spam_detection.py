import json
import logging

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel

from website.views.constants import OPENAI_MODEL_GPT4

logger = logging.getLogger(__name__)


class FlaggedContent(BaseModel):
    is_spam: bool
    confidence: float
    reason: str
    category: str


class AISpamDetectionService:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = None
        if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to create OpenAI client: {e}")

    def detect_spam(self, content: str, content_type: str = "issue") -> dict:
        """
        Detect if content is spam using AI

        Args:
            content: The text content to analyze
            content_type: Type of content (issue, comment, organization, user_profile)

        Returns:
            dict: {
                'is_spam': bool,
                'confidence': float (0-1),
                'reason': str,
                'category': str  # promotional, malicious, low_quality, etc.
            }
        """
        # Check if spam detection is enabled
        if not getattr(settings, "SPAM_DETECTION_ENABLED", True):
            logger.info("Spam detection is disabled in settings")
            return {"is_spam": False, "confidence": 0.0, "reason": "Spam detection disabled", "category": None}

        if not self.client:
            logger.warning("OpenAI client not available, skipping spam detection")
            return {"is_spam": False, "confidence": 0.0, "reason": "AI service unavailable", "category": None}

        try:
            prompt = f"""
            Analyze the following {content_type} content for spam/malicious intent.
            
            Content: {content}
            
            Evaluation Criteria:
            1. Promotional/advertising spam
            2. Malicious links or phishing attempts
            3. Low-quality/irrelevant content
            4. Duplicate/template spam
            5. Social engineering attempts
            
            Return a JSON object with:
            - is_spam: boolean
            - confidence: float between 0 and 1
            - reason: brief explanation
            - category: one of [promotional, malicious, low_quality, duplicate, social_engineering, clean]
            """

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_GPT4,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a spam detection system for a bug bounty platform. Be strict but fair.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            # Parse AI response
            result = self._parse_response(response.choices[0].message.content)
            logger.info(
                f"Spam detection for {content_type}: is_spam={result['is_spam']}, confidence={result['confidence']}"
            )
            return result

        except Exception as e:
            logger.error(f"[Service Error]: Failed during spam detection: {e}")
            return {"is_spam": False, "confidence": 0.0, "reason": f"Detection error: {str(e)}", "category": None}

    def _parse_response(self, ai_response: str) -> dict:
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from response
            start = ai_response.find("{")
            end = ai_response.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(ai_response[start:end])
                return result
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")

        # Fallback parsing
        is_spam = "true" in ai_response.lower() or "spam" in ai_response.lower()
        return {"is_spam": is_spam, "confidence": 0.5, "reason": "Parsed from text analysis", "category": "unknown"}
