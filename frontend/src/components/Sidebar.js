import React, { useState } from 'react';

function Sidebar({ papers, onUpload, onSelectPaper, onDeletePaper, onSearch, loading }) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
    }
  };

  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    onSearch(query);
  };

  return (
    <div className="sidebar">
      <h1>Paper Library</h1>

      <div className="sidebar-section">
        <h2>Upload</h2>
        <label className="upload-area">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={loading}
          />
          <div>
            <p>Click to upload PDF</p>
            <p style={{ fontSize: '12px', marginTop: '5px' }}>or drag and drop</p>
          </div>
        </label>
      </div>

      <div className="sidebar-section">
        <h2>Search</h2>
        <input
          type="text"
          className="search-box"
          placeholder="Search papers..."
          value={searchQuery}
          onChange={handleSearchChange}
          style={{ width: '100%' }}
        />
      </div>

      <div className="sidebar-section">
        <h2>Papers ({papers.length})</h2>
        <ul className="paper-list">
          {papers.map((paper) => (
            <li
              key={paper.id}
              className="paper-item"
              onClick={() => onSelectPaper(paper.id)}
            >
              <h3>{paper.title || 'Untitled Paper'}</h3>
              <p>{paper.authors || 'Unknown authors'}</p>
              <p style={{ fontSize: '11px', marginTop: '5px' }}>
                {new Date(paper.upload_date).toLocaleDateString()}
              </p>
            </li>
          ))}
          {papers.length === 0 && !loading && (
            <p style={{ color: '#95a5a6', fontSize: '14px' }}>No papers yet</p>
          )}
        </ul>
      </div>
    </div>
  );
}

export default Sidebar;
