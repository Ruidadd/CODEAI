import React, { useState } from 'react';
import axios from 'axios';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const API_URL = 'http://localhost:8000/api';

function PaperViewer({ paper, onRefresh }) {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [summary, setSummary] = useState(paper.summary);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [annotations, setAnnotations] = useState([]);
  const [highlights, setHighlights] = useState([]);

  const pdfUrl = `${API_URL.replace('/api', '')}/api/pdf/${paper.filename}`;

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    fetchAnnotations();
    fetchHighlights();
  };

  const fetchAnnotations = async () => {
    try {
      const response = await axios.get(`${API_URL}/annotations/annotation/paper/${paper.id}`);
      setAnnotations(response.data);
    } catch (err) {
      console.error('Failed to fetch annotations', err);
    }
  };

  const fetchHighlights = async () => {
    try {
      const response = await axios.get(`${API_URL}/annotations/highlight/paper/${paper.id}`);
      setHighlights(response.data);
    } catch (err) {
      console.error('Failed to fetch highlights', err);
    }
  };

  const handleGenerateSummary = async () => {
    try {
      setLoadingSummary(true);
      const response = await axios.post(`${API_URL}/papers/${paper.id}/summarize`);
      setSummary(response.data.summary);
    } catch (err) {
      console.error('Failed to generate summary', err);
      alert('Failed to generate summary. Make sure ANTHROPIC_API_KEY is set.');
    } finally {
      setLoadingSummary(false);
    }
  };

  const changePage = (offset) => {
    setPageNumber(prevPageNumber => prevPageNumber + offset);
  };

  const previousPage = () => changePage(-1);
  const nextPage = () => changePage(1);

  return (
    <>
      <div className="toolbar">
        <button
          className="btn btn-primary"
          onClick={previousPage}
          disabled={pageNumber <= 1}
        >
          Previous
        </button>
        <span>
          Page {pageNumber} of {numPages || '?'}
        </span>
        <button
          className="btn btn-primary"
          onClick={nextPage}
          disabled={pageNumber >= numPages}
        >
          Next
        </button>
        <button
          className="btn btn-success"
          onClick={handleGenerateSummary}
          disabled={loadingSummary || summary}
        >
          {loadingSummary ? 'Generating...' : summary ? 'Summary Generated' : 'Generate AI Summary'}
        </button>
      </div>

      <div className="viewer-container">
        <div className="pdf-viewer">
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            loading={<div>Loading PDF...</div>}
            error={<div>Failed to load PDF</div>}
          >
            <Page
              pageNumber={pageNumber}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>
        </div>

        <div className="info-panel">
          <h2>{paper.title || 'Untitled Paper'}</h2>

          <div className="info-section">
            <h3>Authors</h3>
            <p>{paper.authors || 'Unknown'}</p>
          </div>

          {paper.abstract && (
            <div className="info-section">
              <h3>Abstract</h3>
              <p>{paper.abstract}</p>
            </div>
          )}

          {summary && (
            <div className="info-section">
              <h3>AI Summary</h3>
              <p style={{ whiteSpace: 'pre-line' }}>{summary}</p>
            </div>
          )}

          {paper.sections && paper.sections.length > 0 && (
            <div className="info-section">
              <h3>Sections</h3>
              <ul>
                {paper.sections.map((section, idx) => (
                  <li key={idx} style={{ marginBottom: '10px' }}>
                    <strong>{section.title}</strong>
                    <p style={{ fontSize: '13px', color: '#666' }}>
                      {section.content.substring(0, 100)}...
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {annotations.length > 0 && (
            <div className="info-section annotations-list">
              <h3>Annotations ({annotations.length})</h3>
              {annotations.map((ann) => (
                <div key={ann.id} className="annotation-item">
                  <p><strong>Page {ann.page_number}</strong></p>
                  <p>{ann.content}</p>
                  <p style={{ fontSize: '11px', color: '#666' }}>
                    {new Date(ann.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}

          {highlights.length > 0 && (
            <div className="info-section">
              <h3>Highlights ({highlights.length})</h3>
              {highlights.map((highlight) => (
                <div key={highlight.id} className="highlight-item">
                  <p><strong>Page {highlight.page_number}</strong></p>
                  <p>{highlight.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default PaperViewer;
