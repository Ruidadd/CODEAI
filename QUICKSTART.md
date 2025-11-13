# Quick Start Guide

Get up and running with the Paper Reading Tool in 5 minutes!

## Step 1: Clone and Setup Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run backend server
python run.py
```

Backend will be running at `http://localhost:8000`

## Step 2: Setup Frontend

Open a new terminal:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will open at `http://localhost:3000`

## Step 3: Start Using

1. **Upload a PDF**: Click the upload area in the sidebar
2. **View Paper**: Click on the uploaded paper to view it
3. **Generate Summary**: Click "Generate AI Summary" button
4. **Navigate**: Use Previous/Next buttons to browse pages

## Quick Tips

- Search papers using the search box
- All data is stored locally in SQLite
- API docs available at http://localhost:8000/docs
- Make sure your PDF files are text-based (not scanned images)

## Troubleshooting

**Backend won't start?**
- Check Python version (3.8+)
- Verify all dependencies installed
- Check port 8000 is available

**Frontend won't start?**
- Check Node version (16+)
- Run `npm install` again
- Check port 3000 is available

**AI Summary fails?**
- Verify ANTHROPIC_API_KEY is set in backend/.env
- Check API key is valid
- Ensure internet connection

## Next Steps

- Read the full README.md for detailed documentation
- Explore the API at http://localhost:8000/docs
- Try uploading different academic papers
- Experiment with annotations (API ready, extend UI)

Enjoy reading papers!
