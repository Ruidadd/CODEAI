import fitz  # PyMuPDF
import re
from typing import Dict, List, Optional

class PDFProcessor:
    """Process PDF files to extract title, abstract, sections, and content."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def extract_text(self) -> str:
        """Extract all text from the PDF."""
        text = ""
        for page in self.doc:
            text += page.get_text()
        return text

    def extract_title(self, text: str) -> str:
        """Extract paper title (usually the first large text on page 1)."""
        # Try to get first page with larger font
        first_page = self.doc[0]
        blocks = first_page.get_text("dict")["blocks"]

        # Find text with largest font size (likely title)
        max_size = 0
        title = ""

        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > max_size and len(span["text"].strip()) > 10:
                            max_size = span["size"]
                            title = span["text"].strip()

        # Fallback: use first non-empty line
        if not title:
            lines = text.split('\n')
            for line in lines:
                if len(line.strip()) > 10:
                    title = line.strip()
                    break

        return title

    def extract_authors(self, text: str) -> str:
        """Extract authors (heuristic: text after title, before abstract)."""
        lines = text.split('\n')
        authors = []

        # Look for common author patterns in first few lines
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            # Skip empty lines and very long lines (likely not authors)
            if not line or len(line) > 200:
                continue

            # Look for email patterns or common author indicators
            if '@' in line or re.search(r'\b(University|Institute|Department)\b', line):
                # Previous line might be author name
                if i > 0 and lines[i-1].strip():
                    authors.append(lines[i-1].strip())

        return ", ".join(authors) if authors else "Unknown"

    def extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract section."""
        # Look for abstract section
        abstract_pattern = r'(?i)abstract\s*[:\-]?\s*(.*?)(?=\n\n|\nintroduction|\n1\.|\nkeywords)'
        match = re.search(abstract_pattern, text, re.DOTALL)

        if match:
            abstract = match.group(1).strip()
            # Clean up
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract

        return None

    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extract paper sections (Introduction, Methods, Results, etc.)."""
        sections = []

        # Common section headers in academic papers
        section_patterns = [
            r'\n\s*(\d+\.?\s+)?(Introduction|Background|Related Work|Methodology|Methods|'
            r'Approach|Experiments|Results|Discussion|Conclusion|References|'
            r'Future Work|Acknowledgments)\s*\n'
        ]

        for pattern in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                section_name = match.group(2) if match.group(2) else match.group(0).strip()
                start_pos = match.end()

                # Find next section or end of document
                next_match = re.search(pattern, text[start_pos:], re.IGNORECASE)
                end_pos = start_pos + next_match.start() if next_match else len(text)

                section_content = text[start_pos:end_pos].strip()

                # Clean up content
                section_content = re.sub(r'\s+', ' ', section_content)

                if len(section_content) > 50:  # Only include substantial sections
                    sections.append({
                        "title": section_name,
                        "content": section_content[:500]  # Preview only
                    })

        return sections

    def get_page_count(self) -> int:
        """Get total number of pages."""
        return len(self.doc)

    def process(self) -> Dict:
        """Process PDF and extract all information."""
        text = self.extract_text()

        return {
            "title": self.extract_title(text),
            "authors": self.extract_authors(text),
            "abstract": self.extract_abstract(text),
            "sections": self.extract_sections(text),
            "page_count": self.get_page_count(),
            "full_text": text[:1000]  # Preview
        }

    def close(self):
        """Close the PDF document."""
        self.doc.close()
