import logging
import os

from google import genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpamDetection:
    """
    A simple spam detection using gemini api and returns the spam score.

    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Spam detection will be disabled.")
            self.client = None
            return
        self.client = genai.Client(api_key=self.api_key)

    def check_bug_report(self, title, description, url) -> dict:
        """
        Check if a bug report is spam using Gemini API.

         Args:
             title: Bug title/short description
             description: Full bug description
             url: Domain URL associated with the bug report
         Returns:
             dict: {
                 'is_spam': bool,
                 'spam_score': int (0-10),
                 'reason': str
             }
        """
        if not self.client:
            return {"is_spam": False, "spam_score": 0, "reason": "Spam detection not available"}

        try:
            prompt = self._get_system_prompt(title, description, url)
            response = self.get_gemini_response(prompt)
        except Exception as e:
            logger.error("Error in spam detection: %s", e, exc_info=True)
            return {"is_spam": False, "spam_score": 0, "reason": "Error parsing spam detection response"}
        else:
            if response.get("spam_score") is None:
                return {"is_spam": False, "spam_score": 0, "reason": "Invalid spam detection response"}
            return response

    def _get_system_prompt(self, title, desc, url) -> str:
        return f"""
            You are a spam detector for a bug bounty platform. 
            Analyze this bug report.
            The spam score is an integer from 0 to 10, where:
            0 = Definitely legitimate bug report
            10 = Definitely spam
            
            The report may be considered spam for reasons such as:
            - Irrelevant content
            - Malicious links
            - Repetitive submissions
            - Incoherent or nonsensical text
            - Excessive use of promotional language
            - Known spam patterns

            Just because a report has a link does not automatically make it spam and vice versa. Also consider the context and content of the report.
            If the report seems legitimate, assign a low spam score and explain why. Also just because a report is short does not make it spam.
            Bug Report Details:
            Bug Title: {title}
            Bug Description: {desc}
            Domain URL: {url or 'N/A'}

            Be accurate and precise in your reasoning.
            return a JSON object with the following fields:
                - **spam_score**: integer from 0 to 10 (0 = definitely legitimate, 10 = definitely spam)  
                - **is_spam**: boolean, whether the report is considered spam given the score  
                - **reason**:  string explanation for the spamminess (or lack of) 
            """

    def get_gemini_response(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": Spam.model_json_schema(),
            },
        )
        return response.parsed


class Spam(BaseModel):
    spam_score: int = Field(ge=0, le=10, description="Spam score from 0-10")
    is_spam: bool = Field(description="Whether it's considered spam")
    reason: str = Field(description="Reason for spam classification")
