import logging
from django.config import setting
from openai import OpenAI
from website.constants import OPENAI_MODEL_GPT4
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FlaggedContent(BaseModel):
    is_spam: bool
    confidence: float
    reason : str
    category: str

class AISpamDetectionService:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = None
        if hasattr(setting, "OPENAI_API_KEY") and setting.OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=setting.OPENAI_API_KEY)
            except Exception as e:
                logger.error("Failed to create openai client: {e} ")
                
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
        if not self.client:
            logger.warning("OpenAI client not available, skipping spam detection")
            return {
                "is_spam": False,
                "confidence": 0.0,
                "reason" : "AI service unavailable",
                "category": None
            }
        
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
            
            response = self.client.response.parse(
                model = OPENAI_MODEL_GPT4,
                message = [
                    {"role": "system", "content": "You are a spam detection system for a bug bounty platform. Be strict but fair."},
                    {"role": "user", "content": prompt}
                ],
                text_format=FlaggedContent,
                temperature=0.3,
                max_tokens=200
            )

            logger.info(f"Spam detection for {content_type}: is_spam={response['is_spam']}, confidence={response['confidence']}")
            return {
                "is_spam": response['is_spam'],
                "confidence": response['confidence'],
                "reason" : response['reason'],
                "category": response['category']
            }
        except Exception as e:
            logger.error("[Service Error]: Failed during spam detection : {e}")