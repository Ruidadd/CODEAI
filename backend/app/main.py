from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import engine, Base
from .routes import papers, annotations

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Paper Reading Tool API",
    description="API for managing and reading academic papers",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router)
app.include_router(annotations.router)

# Serve uploaded PDFs
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/api/pdf/{filename}")
async def serve_pdf(filename: str):
    """Serve PDF files."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": "File not found"}
    return FileResponse(filepath, media_type="application/pdf")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Paper Reading Tool API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
