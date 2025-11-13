# Paper Reading Tool

A comprehensive web application for reading, managing, and analyzing academic papers. Built with FastAPI (Python) backend and React frontend.

## Features

### Core Functionality
- **PDF Upload & Processing**: Upload academic papers in PDF format
- **Intelligent Parsing**: Automatically extracts title, authors, abstract, and sections
- **AI Summarization**: Generate comprehensive summaries using Claude AI
- **Library Management**: Organize and search your collection of papers
- **PDF Viewing**: Built-in PDF viewer with page navigation
- **Annotations & Highlights**: Add notes and highlights to papers (backend ready, UI extensible)

### Technical Features
- RESTful API with FastAPI
- SQLite database for persistence
- React frontend with PDF.js integration
- Real-time search across papers
- Responsive design

## Project Structure

```
CODEAI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Database models
│   │   ├── database.py          # Database configuration
│   │   ├── pdf_processor.py    # PDF parsing logic
│   │   ├── ai_summarizer.py    # AI summarization
│   │   └── routes/
│   │       ├── papers.py        # Paper management endpoints
│   │       └── annotations.py  # Annotation endpoints
│   ├── requirements.txt
│   ├── run.py                   # Server entry point
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.js
│   │   │   └── PaperViewer.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
└── README.md
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn
- Anthropic API key (for AI summarization)

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

5. **Run the server:**
   ```bash
   python run.py
   ```
   The API will be available at `http://localhost:8000`
   API documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```
   The application will open at `http://localhost:3000`

## Usage

### Uploading Papers
1. Click the upload area in the sidebar
2. Select a PDF file
3. The tool will automatically extract metadata and content

### Viewing Papers
1. Click on any paper in the sidebar to view it
2. Use Previous/Next buttons to navigate pages
3. View extracted information in the info panel

### Generating AI Summaries
1. Open a paper
2. Click "Generate AI Summary" button
3. Wait for Claude to analyze and summarize the paper

### Searching Papers
1. Use the search box in the sidebar
2. Search by title, authors, or abstract content

### Managing Your Library
- Papers are automatically saved to the database
- Delete papers by implementing the delete button
- All annotations and highlights are preserved

## API Endpoints

### Papers
- `POST /api/papers/upload` - Upload a new paper
- `GET /api/papers/` - Get all papers
- `GET /api/papers/{id}` - Get specific paper
- `POST /api/papers/{id}/summarize` - Generate AI summary
- `DELETE /api/papers/{id}` - Delete paper
- `GET /api/papers/search/{query}` - Search papers

### Annotations
- `POST /api/annotations/annotation` - Create annotation
- `GET /api/annotations/annotation/paper/{id}` - Get annotations
- `DELETE /api/annotations/annotation/{id}` - Delete annotation
- `POST /api/annotations/highlight` - Create highlight
- `GET /api/annotations/highlight/paper/{id}` - Get highlights
- `DELETE /api/annotations/highlight/{id}` - Delete highlight

### PDF Access
- `GET /api/pdf/{filename}` - Serve PDF file

## Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **PyMuPDF (fitz)**: PDF processing and text extraction
- **Anthropic SDK**: Claude AI integration
- **Uvicorn**: ASGI server

### Frontend
- **React**: UI library
- **react-pdf**: PDF rendering component
- **PDF.js**: Mozilla's PDF viewer
- **Axios**: HTTP client

## Configuration

### Environment Variables

Backend (`.env`):
```env
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./papers.db
HOST=0.0.0.0
PORT=8000
```

### Database

The application uses SQLite by default. The database file (`papers.db`) is created automatically on first run.

**Models:**
- **Paper**: Stores paper metadata and content
- **Annotation**: Text annotations on papers
- **Highlight**: Highlighted text with coordinates

## Future Enhancements

- [ ] Interactive highlighting in PDF viewer
- [ ] Click-to-annotate functionality
- [ ] Export annotations as notes
- [ ] Citation extraction and management
- [ ] Full-text search within PDFs
- [ ] Tags and categories
- [ ] Multi-user support with authentication
- [ ] Cloud storage integration
- [ ] Mobile responsive improvements
- [ ] Dark mode

## Troubleshooting

### Backend Issues

**PDF processing fails:**
- Ensure PyMuPDF is properly installed
- Check PDF file is not corrupted
- Verify sufficient disk space

**AI summarization fails:**
- Verify ANTHROPIC_API_KEY is set correctly
- Check API key has sufficient credits
- Ensure internet connection

### Frontend Issues

**PDF not displaying:**
- Check backend is running on port 8000
- Verify CORS settings in backend
- Check browser console for errors

**Upload fails:**
- Verify file is a valid PDF
- Check backend logs for errors
- Ensure uploads directory exists

## Contributing

Contributions are welcome! Areas for contribution:
- Enhanced PDF parsing algorithms
- Better section detection
- Interactive annotation UI
- Additional export formats
- Performance optimizations

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Support

For issues and questions:
- Check the API documentation at `/docs`
- Review backend logs
- Check browser console for frontend errors

## Credits

Built with modern web technologies and AI capabilities to enhance academic research and paper reading experience