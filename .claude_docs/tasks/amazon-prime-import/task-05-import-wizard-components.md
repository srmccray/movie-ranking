# Task 05: Import Wizard Components

**Feature:** amazon-prime-import
**Agent:** frontend-implementation
**Status:** Not Started
**Blocked By:** 04

---

## Objective

Create the multi-step import wizard UI with file upload, movie review, and completion summary steps. Integrate with Settings page.

---

## Context

The frontend API client and types are ready. This task creates the user-facing import experience: a modal wizard that guides users through uploading their CSV, reviewing matched movies one by one, and seeing a completion summary.

### Relevant FRD Sections
- FRD Section: "User Experience" - Complete workflow description
- FRD Section: "Frontend Changes" - Component structure

### Relevant Refinement Notes
- Use local component state for wizard (not global state)
- Follow existing Modal component pattern
- Reuse StarRating component for rating input

---

## Scope

### In Scope
- Create ImportWizard.tsx (modal container with step management)
- Create ImportFileUpload.tsx (file selection and upload step)
- Create ImportReview.tsx (movie-by-movie review with add/skip)
- Create ImportComplete.tsx (completion summary)
- Export components from index.ts
- Integrate ImportWizard into SettingsPage
- Add necessary CSS styles

### Out of Scope
- API client methods (task-04)
- Backend changes (tasks 01-03)

---

## Implementation Notes

### Key Files

| File | Action | Notes |
|------|--------|-------|
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx` | Create | Main wizard container |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportFileUpload.tsx` | Create | File upload step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx` | Create | Review step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportComplete.tsx` | Create | Completion step |
| `/Users/stephen/Projects/movie-ranking/frontend/src/components/index.ts` | Modify | Export new components |
| `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx` | Modify | Add import section |
| `/Users/stephen/Projects/movie-ranking/frontend/src/index.css` | Modify | Add import styles |

### Patterns to Follow

- Modal: See `/Users/stephen/Projects/movie-ranking/frontend/src/components/Modal.tsx`
- StarRating: See `/Users/stephen/Projects/movie-ranking/frontend/src/components/StarRating.tsx`
- Settings sections: See existing sections in SettingsPage.tsx

### Component Structure

```
ImportWizard (modal container)
  |-- step: 'upload' | 'review' | 'complete'
  |-- sessionId: string | null
  |-- sessionData: ImportSessionResponse | null
  |
  |-- ImportFileUpload (step === 'upload')
  |     |-- file: File | null
  |     |-- isUploading: boolean
  |     |-- error: string | null
  |     |-- onUploadComplete(session: ImportSessionResponse)
  |
  |-- ImportReview (step === 'review')
  |     |-- movies: MatchedMovieItem[]
  |     |-- currentIndex: number
  |     |-- onAdd(rating: number, ratedAt?: string)
  |     |-- onSkip()
  |     |-- onComplete()
  |
  |-- ImportComplete (step === 'complete')
        |-- addedCount: number
        |-- skippedCount: number
        |-- unmatchedTitles: string[]
        |-- onDone()
```

### ImportWizard.tsx

```tsx
import { useState, useCallback } from 'react';
import { Modal } from './Modal';
import { ImportFileUpload } from './ImportFileUpload';
import { ImportReview } from './ImportReview';
import { ImportComplete } from './ImportComplete';
import { apiClient, ApiClientError } from '../api/client';
import type { ImportSessionResponse, MatchedMovieItem } from '../types';

interface ImportWizardProps {
  onClose: () => void;
  onComplete?: () => void;
}

type WizardStep = 'upload' | 'review' | 'complete';

export function ImportWizard({ onClose, onComplete }: ImportWizardProps) {
  const [step, setStep] = useState<WizardStep>('upload');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [movies, setMovies] = useState<MatchedMovieItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [addedCount, setAddedCount] = useState(0);
  const [skippedCount, setSkippedCount] = useState(0);

  const handleUploadComplete = useCallback((session: ImportSessionResponse) => {
    setSessionId(session.session_id);
    setMovies(session.movies);
    setCurrentIndex(0);
    setAddedCount(0);
    setSkippedCount(0);

    if (session.movies.length === 0) {
      // No movies to review, go straight to completion
      setStep('complete');
    } else {
      setStep('review');
    }
  }, []);

  const handleAdd = useCallback(async (rating: number, ratedAt?: string) => {
    if (!sessionId) return;

    try {
      await apiClient.addImportMovie(sessionId, currentIndex, rating, ratedAt);
      setMovies(prev => prev.map((m, i) =>
        i === currentIndex ? { ...m, status: 'added' as const } : m
      ));
      setAddedCount(prev => prev + 1);

      // Move to next movie or complete
      if (currentIndex >= movies.length - 1) {
        setStep('complete');
      } else {
        setCurrentIndex(prev => prev + 1);
      }
    } catch (err) {
      // Error handling in child component
      throw err;
    }
  }, [sessionId, currentIndex, movies.length]);

  const handleSkip = useCallback(async () => {
    if (!sessionId) return;

    try {
      await apiClient.skipImportMovie(sessionId, currentIndex);
      setMovies(prev => prev.map((m, i) =>
        i === currentIndex ? { ...m, status: 'skipped' as const } : m
      ));
      setSkippedCount(prev => prev + 1);

      // Move to next movie or complete
      if (currentIndex >= movies.length - 1) {
        setStep('complete');
      } else {
        setCurrentIndex(prev => prev + 1);
      }
    } catch (err) {
      throw err;
    }
  }, [sessionId, currentIndex, movies.length]);

  const handleComplete = useCallback(() => {
    setStep('complete');
  }, []);

  const handleDone = useCallback(() => {
    onComplete?.();
    onClose();
  }, [onClose, onComplete]);

  const handleCancel = useCallback(async () => {
    if (sessionId) {
      try {
        await apiClient.cancelImportSession(sessionId);
      } catch (err) {
        // Ignore errors on cancel
      }
    }
    onClose();
  }, [sessionId, onClose]);

  // Get unmatched titles for completion summary
  const unmatchedTitles = movies
    .filter(m => m.tmdb_match === null)
    .map(m => m.parsed.title);

  const stepTitles: Record<WizardStep, string> = {
    upload: 'Import from Amazon Prime',
    review: 'Review Movies',
    complete: 'Import Complete',
  };

  return (
    <Modal
      isOpen={true}
      onClose={handleCancel}
      title={stepTitles[step]}
      size="large"
    >
      <div className="import-wizard">
        {step === 'upload' && (
          <ImportFileUpload onUploadComplete={handleUploadComplete} />
        )}
        {step === 'review' && (
          <ImportReview
            movies={movies}
            currentIndex={currentIndex}
            onAdd={handleAdd}
            onSkip={handleSkip}
            onComplete={handleComplete}
          />
        )}
        {step === 'complete' && (
          <ImportComplete
            addedCount={addedCount}
            skippedCount={skippedCount}
            unmatchedTitles={unmatchedTitles}
            onDone={handleDone}
          />
        )}
      </div>
    </Modal>
  );
}
```

### ImportFileUpload.tsx

```tsx
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

  return (
    <div className="import-file-upload">
      <div className="import-file-upload-info">
        <p className="import-file-upload-description">
          Upload your Amazon Prime Video watch history CSV file. You can export
          your watch history using browser extensions like "Watch History Exporter
          for Amazon Prime Video".
        </p>
      </div>

      <div className="import-file-upload-dropzone" onClick={handleBrowseClick}>
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
```

### ImportReview.tsx

```tsx
import { useState, useCallback } from 'react';
import { Button } from './Button';
import { StarRating } from './StarRating';
import { ApiClientError } from '../api/client';
import type { MatchedMovieItem } from '../types';

interface ImportReviewProps {
  movies: MatchedMovieItem[];
  currentIndex: number;
  onAdd: (rating: number, ratedAt?: string) => Promise<void>;
  onSkip: () => Promise<void>;
  onComplete: () => void;
}

export function ImportReview({
  movies,
  currentIndex,
  onAdd,
  onSkip,
  onComplete,
}: ImportReviewProps) {
  const [rating, setRating] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentMovie = movies[currentIndex];
  const pendingMovies = movies.filter(m => m.status === 'pending');
  const progress = ((movies.length - pendingMovies.length) / movies.length) * 100;

  const handleAdd = useCallback(async () => {
    if (rating === 0) {
      setError('Please select a rating');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Use watch_date from CSV as rated_at if available
      const ratedAt = currentMovie.parsed.watch_date || undefined;
      await onAdd(rating, ratedAt);
      setRating(0);  // Reset for next movie
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to add movie');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [rating, currentMovie, onAdd]);

  const handleSkip = useCallback(async () => {
    setIsProcessing(true);
    setError(null);

    try {
      await onSkip();
      setRating(0);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('Failed to skip movie');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [onSkip]);

  if (!currentMovie) {
    return (
      <div className="import-review-empty">
        <p>No more movies to review.</p>
        <Button onClick={onComplete}>Finish Import</Button>
      </div>
    );
  }

  const movie = currentMovie.tmdb_match;
  const isUnmatched = movie === null;
  const confidenceLabel = currentMovie.confidence >= 0.7 ? 'High' :
                          currentMovie.confidence >= 0.5 ? 'Medium' : 'Low';

  return (
    <div className="import-review">
      {/* Progress Bar */}
      <div className="import-review-progress">
        <div className="import-review-progress-bar">
          <div
            className="import-review-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="import-review-progress-text">
          {currentIndex + 1} of {movies.length}
        </span>
      </div>

      {/* Movie Card */}
      <div className="import-review-card">
        {isUnmatched ? (
          <div className="import-review-unmatched">
            <div className="import-review-unmatched-title">
              No match found for:
            </div>
            <div className="import-review-unmatched-name">
              {currentMovie.parsed.title}
            </div>
            <p className="import-review-unmatched-hint">
              You can search for this movie manually after completing the import.
            </p>
          </div>
        ) : (
          <>
            <div className="import-review-poster">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={`${movie.title} poster`}
                  className="import-review-poster-image"
                />
              ) : (
                <div className="import-review-poster-placeholder">
                  No Poster
                </div>
              )}
            </div>
            <div className="import-review-info">
              <h3 className="import-review-title">{movie.title}</h3>
              {movie.year && (
                <span className="import-review-year">{movie.year}</span>
              )}
              {movie.overview && (
                <p className="import-review-overview">{movie.overview}</p>
              )}
              <div className="import-review-confidence">
                <span className={`import-review-confidence-badge confidence-${confidenceLabel.toLowerCase()}`}>
                  {confidenceLabel} confidence match
                </span>
              </div>
              {currentMovie.parsed.watch_date && (
                <div className="import-review-watch-date">
                  Watched: {new Date(currentMovie.parsed.watch_date).toLocaleDateString()}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Rating Input */}
      {!isUnmatched && (
        <div className="import-review-rating">
          <label className="import-review-rating-label">Your Rating:</label>
          <StarRating
            rating={rating}
            onChange={setRating}
            size="large"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="import-review-actions">
        <Button
          variant="ghost"
          onClick={handleSkip}
          disabled={isProcessing}
        >
          Skip
        </Button>
        {!isUnmatched && (
          <Button
            onClick={handleAdd}
            disabled={isProcessing || rating === 0}
            loading={isProcessing}
          >
            Add to My Movies
          </Button>
        )}
      </div>
    </div>
  );
}
```

### ImportComplete.tsx

```tsx
import { Button } from './Button';

interface ImportCompleteProps {
  addedCount: number;
  skippedCount: number;
  unmatchedTitles: string[];
  onDone: () => void;
}

export function ImportComplete({
  addedCount,
  skippedCount,
  unmatchedTitles,
  onDone,
}: ImportCompleteProps) {
  return (
    <div className="import-complete">
      <div className="import-complete-summary">
        <h3 className="import-complete-heading">Import Summary</h3>

        <div className="import-complete-stats">
          <div className="import-complete-stat">
            <span className="import-complete-stat-value">{addedCount}</span>
            <span className="import-complete-stat-label">Movies Added</span>
          </div>
          <div className="import-complete-stat">
            <span className="import-complete-stat-value">{skippedCount}</span>
            <span className="import-complete-stat-label">Movies Skipped</span>
          </div>
        </div>
      </div>

      {unmatchedTitles.length > 0 && (
        <div className="import-complete-unmatched">
          <h4 className="import-complete-unmatched-heading">
            Unmatched Titles ({unmatchedTitles.length})
          </h4>
          <p className="import-complete-unmatched-hint">
            These movies couldn't be matched automatically. You can search for them manually.
          </p>
          <ul className="import-complete-unmatched-list">
            {unmatchedTitles.slice(0, 10).map((title, index) => (
              <li key={index}>{title}</li>
            ))}
            {unmatchedTitles.length > 10 && (
              <li className="import-complete-unmatched-more">
                ...and {unmatchedTitles.length - 10} more
              </li>
            )}
          </ul>
        </div>
      )}

      <div className="import-complete-actions">
        <Button onClick={onDone}>Done</Button>
      </div>
    </div>
  );
}
```

### SettingsPage Integration

Add to SettingsPage.tsx after "Login Methods" section:

```tsx
const [showImportWizard, setShowImportWizard] = useState(false);

const handleImportComplete = useCallback(() => {
  // Optionally refresh rankings data or show success message
}, []);

// In the JSX, after the Login Methods section:
{/* Import Watch History Section */}
<section className="settings-section">
  <h2 className="settings-section-title">Import Watch History</h2>
  <div className="settings-card">
    <div className="settings-row settings-row-action">
      <div className="settings-row-info">
        <div className="settings-label">Amazon Prime Video</div>
        <div className="settings-description">
          Import your watch history from Amazon Prime Video using a CSV export.
        </div>
      </div>
      <div className="settings-row-action-button">
        <Button onClick={() => setShowImportWizard(true)}>
          Import
        </Button>
      </div>
    </div>
  </div>
</section>

{/* Import Wizard Modal */}
{showImportWizard && (
  <ImportWizard
    onClose={() => setShowImportWizard(false)}
    onComplete={handleImportComplete}
  />
)}
```

### CSS Styles

Add to index.css:

```css
/* Import Wizard */
.import-wizard {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* File Upload Step */
.import-file-upload {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.import-file-upload-description {
  color: var(--color-neutral-600);
  line-height: 1.5;
}

.import-file-upload-dropzone {
  border: 2px dashed var(--color-neutral-300);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.import-file-upload-dropzone:hover {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
}

.import-file-input {
  display: none;
}

.import-file-selected {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.import-file-name {
  font-weight: 600;
  color: var(--color-neutral-900);
}

.import-file-size {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}

.import-file-placeholder {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  color: var(--color-neutral-600);
}

.import-file-hint {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}

.import-file-upload-actions {
  display: flex;
  justify-content: flex-end;
}

/* Review Step */
.import-review {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.import-review-progress {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.import-review-progress-bar {
  flex: 1;
  height: 8px;
  background-color: var(--color-neutral-200);
  border-radius: 4px;
  overflow: hidden;
}

.import-review-progress-fill {
  height: 100%;
  background-color: var(--color-primary-500);
  transition: width 0.3s ease;
}

.import-review-progress-text {
  font-size: 0.875rem;
  color: var(--color-neutral-600);
  white-space: nowrap;
}

.import-review-card {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

.import-review-poster {
  flex-shrink: 0;
  width: 120px;
}

.import-review-poster-image {
  width: 100%;
  border-radius: var(--radius-md);
}

.import-review-poster-placeholder {
  width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-neutral-200);
  border-radius: var(--radius-md);
  color: var(--color-neutral-500);
  font-size: 0.875rem;
}

.import-review-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.import-review-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-neutral-900);
  margin: 0;
}

.import-review-year {
  font-size: 0.875rem;
  color: var(--color-neutral-600);
}

.import-review-overview {
  font-size: 0.875rem;
  color: var(--color-neutral-600);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.import-review-confidence {
  margin-top: var(--space-2);
}

.import-review-confidence-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
}

.confidence-high {
  background-color: var(--color-success-100);
  color: var(--color-success-700);
}

.confidence-medium {
  background-color: var(--color-warning-100);
  color: var(--color-warning-700);
}

.confidence-low {
  background-color: var(--color-error-100);
  color: var(--color-error-700);
}

.import-review-watch-date {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}

.import-review-unmatched {
  text-align: center;
  padding: var(--space-6);
}

.import-review-unmatched-title {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
  margin-bottom: var(--space-2);
}

.import-review-unmatched-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-neutral-900);
  margin-bottom: var(--space-4);
}

.import-review-unmatched-hint {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
}

.import-review-rating {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.import-review-rating-label {
  font-weight: 500;
  color: var(--color-neutral-700);
}

.import-review-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

/* Complete Step */
.import-complete {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.import-complete-summary {
  text-align: center;
}

.import-complete-heading {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-neutral-900);
  margin-bottom: var(--space-4);
}

.import-complete-stats {
  display: flex;
  justify-content: center;
  gap: var(--space-8);
}

.import-complete-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.import-complete-stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-primary-600);
}

.import-complete-stat-label {
  font-size: 0.875rem;
  color: var(--color-neutral-600);
}

.import-complete-unmatched {
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.import-complete-unmatched-heading {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-900);
  margin-bottom: var(--space-2);
}

.import-complete-unmatched-hint {
  font-size: 0.875rem;
  color: var(--color-neutral-500);
  margin-bottom: var(--space-3);
}

.import-complete-unmatched-list {
  list-style: disc;
  padding-left: var(--space-4);
  color: var(--color-neutral-700);
}

.import-complete-unmatched-list li {
  margin-bottom: var(--space-1);
}

.import-complete-unmatched-more {
  font-style: italic;
  color: var(--color-neutral-500);
}

.import-complete-actions {
  display: flex;
  justify-content: center;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .import-review-card {
    flex-direction: column;
  }

  .import-review-poster {
    width: 100%;
    max-width: 200px;
    margin: 0 auto;
  }

  .import-complete-stats {
    gap: var(--space-4);
  }
}
```

---

## Acceptance Criteria

- [ ] ImportWizard opens as modal from Settings page
- [ ] ImportWizard manages step state (upload -> review -> complete)
- [ ] ImportFileUpload accepts CSV files only
- [ ] ImportFileUpload shows selected file name and size
- [ ] ImportFileUpload uploads file and transitions to review
- [ ] ImportReview shows progress bar with current position
- [ ] ImportReview displays movie poster, title, year, and overview
- [ ] ImportReview shows confidence badge (High/Medium/Low)
- [ ] ImportReview shows watch date from CSV
- [ ] ImportReview allows star rating selection (1-5)
- [ ] ImportReview "Add to My Movies" creates ranking
- [ ] ImportReview "Skip" marks movie as skipped
- [ ] ImportReview handles unmatched movies gracefully
- [ ] ImportComplete shows added and skipped counts
- [ ] ImportComplete lists unmatched titles
- [ ] Wizard can be cancelled at any step
- [ ] All components follow existing style patterns
- [ ] All components are exported from index.ts

---

## Testing Requirements

- [ ] Test ImportWizard step transitions
- [ ] Test ImportFileUpload file validation
- [ ] Test ImportReview add/skip actions
- [ ] Test ImportReview error handling
- [ ] Test ImportComplete summary display
- [ ] Test SettingsPage integration

---

## Handoff Notes

### For Next Task (task-06)
- Feature is now user-testable from Settings page
- All components are functional and styled
- Ready for backend integration tests

### Artifacts Produced
- `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportWizard.tsx`
- `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportFileUpload.tsx`
- `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportReview.tsx`
- `/Users/stephen/Projects/movie-ranking/frontend/src/components/ImportComplete.tsx`
- Modified `/Users/stephen/Projects/movie-ranking/frontend/src/components/index.ts`
- Modified `/Users/stephen/Projects/movie-ranking/frontend/src/pages/SettingsPage.tsx`
- Modified `/Users/stephen/Projects/movie-ranking/frontend/src/index.css`
