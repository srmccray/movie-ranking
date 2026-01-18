import { useState, useCallback } from 'react';
import { Modal } from './Modal';
import { ImportFileUpload } from './ImportFileUpload';
import { ImportReview } from './ImportReview';
import { ImportComplete } from './ImportComplete';
import { apiClient } from '../api/client';
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
  }, [sessionId, currentIndex, movies.length]);

  const handleSkip = useCallback(async () => {
    if (!sessionId) return;

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
  }, [sessionId, currentIndex, movies.length]);

  const handleComplete = useCallback(() => {
    setStep('complete');
  }, []);

  const handleMovieUpdated = useCallback((index: number, updatedMovie: MatchedMovieItem) => {
    setMovies(prev => prev.map((m, i) =>
      i === index ? updatedMovie : m
    ));
  }, []);

  const handleDone = useCallback(() => {
    onComplete?.();
    onClose();
  }, [onClose, onComplete]);

  const handleCancel = useCallback(async () => {
    if (sessionId) {
      try {
        await apiClient.cancelImportSession(sessionId);
      } catch {
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
    >
      <div className="import-wizard">
        {step === 'upload' && (
          <ImportFileUpload onUploadComplete={handleUploadComplete} />
        )}
        {step === 'review' && sessionId && (
          <ImportReview
            movies={movies}
            currentIndex={currentIndex}
            sessionId={sessionId}
            onAdd={handleAdd}
            onSkip={handleSkip}
            onComplete={handleComplete}
            onMovieUpdated={handleMovieUpdated}
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
