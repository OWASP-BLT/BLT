import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class SpamDetection:
    """
    A simple spam detection using gemini api and returns the spam score.

    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("GEMINI_API_KEY not set. Spam detection will be disabled.")
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
                 'spam_score': int (0-100),
                 'reason': str
             }
        """
        if not self.api_key:
            return {"is_spam": False, "spam_score": 0, "reason": "Spam detection not available"}
        try:
            prompt = self._get_system_prompt(title, description, url)
            response = self.get_gemini_response(prompt)
            return response
        except Exception as e:
            print("Error parsing Gemini response:", e)
            return {"is_spam": False, "spam_score": 0, "reason": "Error parsing spam detection response"}

    def _get_system_prompt(self, title, desc, url) -> str:
        return f"""
            You are a spam detector for a bug bounty platform. 
            Analyze this bug report.

            0 = Definitely legitimate bug report
            100 = Definitely spam

            You have to be smart and understand that the bug report could be well-written with high detials but still be spammy (e.g., fake reports, irrelevant content, etc.).
            Use your judgment: the report may be very detailed but could still be fake, irrelevant, or promotional.  

            Bug Report Details:
            Title: {title}
            Description: {desc}
            URL: {url or 'N/A'}

            Be accurate and precise in your reasoning.
            return a JSON object with the following fields:
                - **spam_score**: integer from 0 to 100 (0 = definitely legitimate, 100 = definitely spam)  
                - **is_spam**: boolean, whether the report is considered spam given the score  
                - **reason**:  string explanation for the spamminess (or lack of) 
            """

    def get_gemini_response(self, prompt: str) -> str:

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": Spam.model_json_schema(),
            },
        )
        return response.parsed


class Spam(BaseModel):
    spam_score: int = Field(ge=0, le=100, description="Spam score from 0-100")
    is_spam: bool = Field(description="Whether it's considered spam")
    reason: str = Field(description="Reason for spam classification")
