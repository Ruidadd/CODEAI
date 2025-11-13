from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    authors = Column(String)
    abstract = Column(Text)
    filename = Column(String, unique=True)
    filepath = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)  # Store extracted sections as JSON

    annotations = relationship("Annotation", back_populates="paper", cascade="all, delete-orphan")
    highlights = relationship("Highlight", back_populates="paper", cascade="all, delete-orphan")

class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    page_number = Column(Integer)
    x_position = Column(Integer)
    y_position = Column(Integer)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="annotations")

class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    page_number = Column(Integer)
    text = Column(Text)
    color = Column(String, default="#FFFF00")
    coordinates = Column(JSON)  # Store highlight coordinates as JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="highlights")
