from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict

from ..database import get_db
from ..models import Paper, Annotation, Highlight

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

class AnnotationCreate(BaseModel):
    paper_id: int
    page_number: int
    x_position: int
    y_position: int
    content: str

class HighlightCreate(BaseModel):
    paper_id: int
    page_number: int
    text: str
    color: Optional[str] = "#FFFF00"
    coordinates: Dict

@router.post("/annotation")
async def create_annotation(
    annotation: AnnotationCreate,
    db: Session = Depends(get_db)
):
    """Create a new annotation on a paper."""

    # Verify paper exists
    paper = db.query(Paper).filter(Paper.id == annotation.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    new_annotation = Annotation(
        paper_id=annotation.paper_id,
        page_number=annotation.page_number,
        x_position=annotation.x_position,
        y_position=annotation.y_position,
        content=annotation.content
    )

    db.add(new_annotation)
    db.commit()
    db.refresh(new_annotation)

    return {
        "id": new_annotation.id,
        "paper_id": new_annotation.paper_id,
        "page_number": new_annotation.page_number,
        "x_position": new_annotation.x_position,
        "y_position": new_annotation.y_position,
        "content": new_annotation.content,
        "created_at": new_annotation.created_at.isoformat()
    }

@router.get("/annotation/paper/{paper_id}")
async def get_annotations(paper_id: int, db: Session = Depends(get_db)):
    """Get all annotations for a specific paper."""

    annotations = db.query(Annotation).filter(
        Annotation.paper_id == paper_id
    ).order_by(Annotation.page_number, Annotation.created_at).all()

    return [
        {
            "id": ann.id,
            "paper_id": ann.paper_id,
            "page_number": ann.page_number,
            "x_position": ann.x_position,
            "y_position": ann.y_position,
            "content": ann.content,
            "created_at": ann.created_at.isoformat()
        }
        for ann in annotations
    ]

@router.delete("/annotation/{annotation_id}")
async def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """Delete an annotation."""

    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(annotation)
    db.commit()

    return {"message": "Annotation deleted successfully"}

@router.post("/highlight")
async def create_highlight(
    highlight: HighlightCreate,
    db: Session = Depends(get_db)
):
    """Create a new highlight on a paper."""

    # Verify paper exists
    paper = db.query(Paper).filter(Paper.id == highlight.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    new_highlight = Highlight(
        paper_id=highlight.paper_id,
        page_number=highlight.page_number,
        text=highlight.text,
        color=highlight.color,
        coordinates=highlight.coordinates
    )

    db.add(new_highlight)
    db.commit()
    db.refresh(new_highlight)

    return {
        "id": new_highlight.id,
        "paper_id": new_highlight.paper_id,
        "page_number": new_highlight.page_number,
        "text": new_highlight.text,
        "color": new_highlight.color,
        "coordinates": new_highlight.coordinates,
        "created_at": new_highlight.created_at.isoformat()
    }

@router.get("/highlight/paper/{paper_id}")
async def get_highlights(paper_id: int, db: Session = Depends(get_db)):
    """Get all highlights for a specific paper."""

    highlights = db.query(Highlight).filter(
        Highlight.paper_id == paper_id
    ).order_by(Highlight.page_number, Highlight.created_at).all()

    return [
        {
            "id": h.id,
            "paper_id": h.paper_id,
            "page_number": h.page_number,
            "text": h.text,
            "color": h.color,
            "coordinates": h.coordinates,
            "created_at": h.created_at.isoformat()
        }
        for h in highlights
    ]

@router.delete("/highlight/{highlight_id}")
async def delete_highlight(highlight_id: int, db: Session = Depends(get_db)):
    """Delete a highlight."""

    highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    db.delete(highlight)
    db.commit()

    return {"message": "Highlight deleted successfully"}
