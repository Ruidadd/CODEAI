#!/usr/bin/env python3
"""
Paper Reading Tool Backend Server
Run this script to start the FastAPI server
"""

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
