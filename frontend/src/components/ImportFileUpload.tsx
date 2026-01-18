import { useState, useCallback, useRef } from 'react';
import { Button } from './Button';
import { apiClient, ApiClientError } from '../api/client';
import type { ImportSessionResponse } from '../types';

interface ImportFileUploadProps {
  onUploadComplete: (session: ImportSessionResponse) => void;
}

export function ImportFileUpload({ onUploadComplete }: ImportFileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
        setError('Please select a CSV file');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const session = await apiClient.uploadAmazonPrimeCSV(file);
      onUploadComplete(session);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to upload file. Please try again.');
      }
    } finally {
      setIsUploading(false);
    }
  }, [file, onUploadComplete]);

  const handleBrowseClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      if (!droppedFile.name.toLowerCase().endsWith('.csv')) {
        setError('Please select a CSV file');
        setFile(null);
        return;
      }
      setFile(droppedFile);
      setError(null);
    }
  }, []);

  return (
    <div className="import-file-upload">
      <div className="import-file-upload-info">
        <p className="import-file-upload-description">
          Upload your Amazon Prime Video watch history CSV file. You can export
          your watch history using browser extensions like "Amazon Video Watch History Export".
        </p>

        <details className="import-csv-example">
          <summary className="import-csv-example-toggle">
            View expected CSV format
          </summary>
          <div className="import-csv-example-content">
            <p className="import-csv-example-note">
              The CSV must have <strong>Type</strong> and <strong>Title</strong> columns.
              <strong>Date Watched</strong> and <strong>Image URL</strong> are optional.
            </p>
            <pre className="import-csv-example-code">
{`Type,Title,Date Watched,Image URL
Movie,The Matrix,2024-01-15,https://...
Movie,Inception,2024-02-20,https://...
TV Series,Breaking Bad,2024-03-01,https://...`}
            </pre>
            <p className="import-csv-example-note">
              TV Series entries will be automatically filtered out. Only movies will be imported.
            </p>
          </div>
        </details>
      </div>

      <div
        className="import-file-upload-dropzone"
        onClick={handleBrowseClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleBrowseClick();
          }
        }}
        aria-label="Select CSV file to upload"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="import-file-input"
          aria-label="Select CSV file"
        />
        {file ? (
          <div className="import-file-selected">
            <span className="import-file-name">{file.name}</span>
            <span className="import-file-size">
              ({(file.size / 1024).toFixed(1)} KB)
            </span>
          </div>
        ) : (
          <div className="import-file-placeholder">
            <svg
              className="import-file-upload-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Click to select a CSV file</span>
            <span className="import-file-hint">or drag and drop</span>
          </div>
        )}
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="import-file-upload-actions">
        <Button
          onClick={handleUpload}
          disabled={!file || isUploading}
          loading={isUploading}
        >
          {isUploading ? 'Uploading...' : 'Upload and Continue'}
        </Button>
      </div>
    </div>
  );
}
