from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime

from ..database import get_db
from ..models import Paper, Annotation, Highlight
from ..pdf_processor import PDFProcessor
from ..ai_summarizer import AISummarizer

router = APIRouter(prefix="/api/papers", tags=["papers"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a PDF paper and process it."""

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process PDF
    try:
        processor = PDFProcessor(filepath)
        extracted_data = processor.process()
        processor.close()

        # Create paper record
        paper = Paper(
            title=extracted_data["title"],
            authors=extracted_data["authors"],
            abstract=extracted_data["abstract"],
            filename=safe_filename,
            filepath=filepath,
            sections=extracted_data["sections"]
        )

        db.add(paper)
        db.commit()
        db.refresh(paper)

        return {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "filename": paper.filename,
            "page_count": extracted_data["page_count"],
            "sections": extracted_data["sections"]
        }

    except Exception as e:
        # Clean up file if processing fails
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@router.get("/")
async def get_papers(db: Session = Depends(get_db)):
    """Get all papers in the library."""
    papers = db.query(Paper).order_by(Paper.upload_date.desc()).all()

    return [
        {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "filename": paper.filename,
            "upload_date": paper.upload_date.isoformat(),
            "has_summary": paper.summary is not None
        }
        for paper in papers
    ]

@router.get("/{paper_id}")
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Get a specific paper by ID."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "filename": paper.filename,
        "filepath": paper.filepath,
        "upload_date": paper.upload_date.isoformat(),
        "summary": paper.summary,
        "sections": paper.sections
    }

@router.post("/{paper_id}/summarize")
async def summarize_paper(paper_id: int, db: Session = Depends(get_db)):
    """Generate AI summary for a paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if paper.summary:
        return {"summary": paper.summary}

    try:
        # Process PDF to get full text if needed
        processor = PDFProcessor(paper.filepath)
        full_text = processor.extract_text()
        processor.close()

        # Generate summary
        summarizer = AISummarizer()
        summary = summarizer.summarize_paper(
            paper.title,
            paper.abstract or "",
            full_text[:3000]
        )

        # Save summary
        paper.summary = summary
        db.commit()

        return {"summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@router.delete("/{paper_id}")
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """Delete a paper from the library."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete file
    if os.path.exists(paper.filepath):
        os.remove(paper.filepath)

    # Delete database record
    db.delete(paper)
    db.commit()

    return {"message": "Paper deleted successfully"}

@router.get("/search/{query}")
async def search_papers(query: str, db: Session = Depends(get_db)):
    """Search papers by title, authors, or abstract."""
    papers = db.query(Paper).filter(
        (Paper.title.ilike(f"%{query}%")) |
        (Paper.authors.ilike(f"%{query}%")) |
        (Paper.abstract.ilike(f"%{query}%"))
    ).all()

    return [
        {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "filename": paper.filename
        }
        for paper in papers
    ]
