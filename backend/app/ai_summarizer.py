import os
from anthropic import Anthropic
from typing import Optional

class AISummarizer:
    """Use Claude AI to summarize academic papers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=self.api_key)

    def summarize_paper(self, title: str, abstract: str, full_text: str = None) -> str:
        """Generate a summary of the paper using Claude."""

        # Prepare the content to summarize
        content = f"Title: {title}\n\n"
        if abstract:
            content += f"Abstract: {abstract}\n\n"
        if full_text:
            # Limit text length to avoid token limits
            content += f"Full Text Preview: {full_text[:3000]}"

        prompt = f"""Please provide a comprehensive summary of this academic paper.

{content}

Please structure your summary as follows:
1. Main Contribution: What is the key contribution or finding?
2. Methodology: How did they approach the problem?
3. Key Results: What were the main results or findings?
4. Significance: Why is this work important?

Keep the summary concise but informative (around 200-300 words)."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def extract_key_points(self, text: str) -> list:
        """Extract key points from paper text."""

        prompt = f"""Please extract 5-7 key points from this academic paper text:

{text[:4000]}

Format as a bullet-point list."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse bullet points
            response_text = message.content[0].text
            key_points = [
                line.strip().lstrip('-•*').strip()
                for line in response_text.split('\n')
                if line.strip() and (line.strip().startswith('-') or
                                    line.strip().startswith('•') or
                                    line.strip().startswith('*'))
            ]

            return key_points

        except Exception as e:
            return [f"Error extracting key points: {str(e)}"]
