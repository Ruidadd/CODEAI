import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PaperViewer from './components/PaperViewer';
import Sidebar from './components/Sidebar';
import './index.css';

const API_URL = 'http://localhost:8000/api';

function App() {
  const [papers, setPapers] = useState([]);
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPapers();
  }, []);

  const fetchPapers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/papers/`);
      setPapers(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch papers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      await axios.post(`${API_URL}/papers/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      await fetchPapers();
      setError(null);
    } catch (err) {
      setError('Failed to upload paper');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPaper = async (paperId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/papers/${paperId}`);
      setSelectedPaper(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load paper');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePaper = async (paperId) => {
    if (!window.confirm('Are you sure you want to delete this paper?')) {
      return;
    }

    try {
      setLoading(true);
      await axios.delete(`${API_URL}/papers/${paperId}`);
      await fetchPapers();
      if (selectedPaper && selectedPaper.id === paperId) {
        setSelectedPaper(null);
      }
      setError(null);
    } catch (err) {
      setError('Failed to delete paper');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query) => {
    if (!query.trim()) {
      fetchPapers();
      return;
    }

    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/papers/search/${query}`);
      setPapers(response.data);
      setError(null);
    } catch (err) {
      setError('Search failed');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        papers={papers}
        onUpload={handleUpload}
        onSelectPaper={handleSelectPaper}
        onDeletePaper={handleDeletePaper}
        onSearch={handleSearch}
        loading={loading}
      />
      <div className="main-content">
        {error && <div className="error">{error}</div>}
        {loading && <div className="loading">Loading...</div>}
        {!selectedPaper && !loading && (
          <div className="welcome-screen">
            <h2>Welcome to Paper Reading Tool</h2>
            <p>Upload a PDF paper to get started</p>
          </div>
        )}
        {selectedPaper && (
          <PaperViewer
            paper={selectedPaper}
            onRefresh={() => handleSelectPaper(selectedPaper.id)}
          />
        )}
      </div>
    </div>
  );
}

export default App;
