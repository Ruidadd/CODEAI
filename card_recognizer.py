"""
Business Card Recognition Service using Google Gemini API
"""
import json
import google.generativeai as genai
from PIL import Image
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class BusinessCardInfo:
    """Data class to store extracted business card information"""
    name: str = ""
    company: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    fax: str = ""
    address: str = ""
    website: str = ""
    linkedin: str = ""
    wechat: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        return all(value == "" for value in asdict(self).values())


class CardRecognizer:
    """Business card recognition using Google Gemini Vision API"""

    EXTRACTION_PROMPT = """
    Please analyze this business card image and extract all the information you can find.

    Return the information in the following JSON format (use empty string for fields not found):
    {
        "name": "Full name of the person",
        "company": "Company or organization name",
        "title": "Job title or position",
        "email": "Email address",
        "phone": "Office/landline phone number",
        "mobile": "Mobile/cell phone number",
        "fax": "Fax number",
        "address": "Full address",
        "website": "Website URL",
        "linkedin": "LinkedIn profile URL or username",
        "wechat": "WeChat ID",
        "notes": "Any other relevant information found on the card"
    }

    Important:
    - Extract text in its original language
    - If there are multiple phone numbers, put the main one in 'phone' and others in 'mobile' or 'notes'
    - Include country codes for phone numbers if visible
    - Return ONLY the JSON object, no additional text
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the card recognizer with Gemini API

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (default: gemini-2.0-flash)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def recognize(self, image: Image.Image) -> tuple[BusinessCardInfo, str]:
        """
        Recognize and extract information from a business card image

        Args:
            image: PIL Image object of the business card

        Returns:
            Tuple of (BusinessCardInfo object, raw response text)
        """
        try:
            # Send image to Gemini for analysis
            response = self.model.generate_content([self.EXTRACTION_PROMPT, image])
            raw_text = response.text.strip()

            # Parse the JSON response
            card_info = self._parse_response(raw_text)
            return card_info, raw_text

        except Exception as e:
            error_info = BusinessCardInfo(notes=f"Error: {str(e)}")
            return error_info, str(e)

    def _parse_response(self, response_text: str) -> BusinessCardInfo:
        """Parse the Gemini response into a BusinessCardInfo object"""
        try:
            # Clean up the response - remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # Parse JSON
            data = json.loads(text)

            return BusinessCardInfo(
                name=data.get("name", ""),
                company=data.get("company", ""),
                title=data.get("title", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                mobile=data.get("mobile", ""),
                fax=data.get("fax", ""),
                address=data.get("address", ""),
                website=data.get("website", ""),
                linkedin=data.get("linkedin", ""),
                wechat=data.get("wechat", ""),
                notes=data.get("notes", "")
            )
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract what we can
            return BusinessCardInfo(notes=f"Could not parse response: {response_text}")


def test_api_connection(api_key: str) -> tuple[bool, str]:
    """
    Test if the Gemini API key is valid

    Args:
        api_key: Google Gemini API key

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Say 'API connection successful' in exactly those words.")
        return True, "API connection successful"
    except Exception as e:
        return False, f"API connection failed: {str(e)}"
