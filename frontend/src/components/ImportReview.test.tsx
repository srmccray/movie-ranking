/**
 * Characterization tests for ImportReview: card rendering, add flow, skip flow, empty state.
 * Search panel behavior lives in ImportReview.search.test.tsx and ImportReview.searchSelect.test.tsx.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ImportReview } from './ImportReview';
import { ApiClientError } from '../api/client';
import {
  SESSION_ID,
  makeCallbacks,
  makeMatch,
  makeMovie,
  makeMovies,
} from '../__tests__/helpers/importReview';
import type { MatchedMovieItem } from '../types';

function renderReview(movies: MatchedMovieItem[], currentIndex = 0) {
  const callbacks = makeCallbacks();
  const utils = render(
    <ImportReview movies={movies} currentIndex={currentIndex} sessionId={SESSION_ID} {...callbacks} />
  );
  return { ...utils, ...callbacks };
}

/** A promise the test resolves/rejects by hand, to observe in-flight UI. */
function deferred() {
  let resolve!: () => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('ImportReview rendering', () => {
  it('shows title, year, overview and poster of the current matched movie', () => {
    renderReview(makeMovies());

    expect(screen.getByRole('heading', { name: 'The Matrix' })).toBeInTheDocument();
    expect(screen.getByText('1999')).toBeInTheDocument();
    expect(screen.getByText(/computer hacker learns/)).toBeInTheDocument();
    expect(screen.getByAltText('The Matrix poster')).toHaveAttribute(
      'src',
      'https://image.tmdb.org/t/p/w185/matrix.jpg'
    );
  });

  it('shows a No Poster placeholder and omits missing year and overview', () => {
    const movie = makeMovie({ tmdb_match: makeMatch({ poster_url: null, year: null, overview: null }) });
    renderReview([movie]);

    expect(screen.getByText('No Poster')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.queryByText('1999')).not.toBeInTheDocument();
    expect(screen.queryByText(/computer hacker/)).not.toBeInTheDocument();
  });

  it('shows the watch date formatted in UTC, and omits it when absent', () => {
    const { unmount } = renderReview([makeMovie()]);
    expect(screen.getByText('Watched: 1/15/2024')).toBeInTheDocument();
    unmount();

    renderReview([makeMovie({ parsed: { title: 'The Matrix', watch_date: null, prime_image_url: null } })]);
    expect(screen.queryByText(/Watched:/)).not.toBeInTheDocument();
  });

  it.each([
    [0.95, 'High'],
    [0.7, 'High'],
    [0.69, 'Medium'],
    [0.5, 'Medium'],
    [0.49, 'Low'],
    [0, 'Low'],
  ])('labels confidence %s as %s', (confidence, label) => {
    renderReview([makeMovie({ confidence })]);
    expect(screen.getByText(`${label} confidence match`)).toBeInTheDocument();
  });

  it('shows position as "<n> of <total>" using currentIndex', () => {
    renderReview(makeMovies(), 1);
    expect(screen.getByText('2 of 3')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Inception' })).toBeInTheDocument();
  });

  it('fills the progress bar by the share of non-pending movies', () => {
    const movies = [makeMovie({ status: 'added' }), makeMovie(), makeMovie(), makeMovie()];
    const { container } = renderReview(movies, 1);
    expect(container.querySelector('.import-review-progress-fill')).toHaveStyle({ width: '25%' });
  });

  it('shows the unmatched state with the parsed title, search button and Skip but no rating or Add', () => {
    renderReview(makeMovies(), 2);

    expect(screen.getByText('No match found for:')).toBeInTheDocument();
    expect(screen.getByText('Unknown Movie 2024')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Search for this movie' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Add to My Movies' })).not.toBeInTheDocument();
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    expect(screen.queryByText(/confidence match/)).not.toBeInTheDocument();
  });

  it('offers a star rating radiogroup with five unselected stars and a disabled Add button', () => {
    renderReview([makeMovie()]);

    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    const stars = screen.getAllByRole('radio');
    expect(stars).toHaveLength(5);
    stars.forEach((s) => expect(s).toHaveAttribute('aria-checked', 'false'));
    expect(screen.getByRole('button', { name: 'Add to My Movies' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Search for different movie' })).toBeEnabled();
  });
});

describe('ImportReview add flow', () => {
  it('enables Add once a rating is chosen and marks that star checked', async () => {
    const user = userEvent.setup();
    renderReview([makeMovie()]);

    await user.click(screen.getByRole('radio', { name: '4 stars' }));

    expect(screen.getByRole('radio', { name: '4 stars' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('button', { name: 'Add to My Movies' })).toBeEnabled();
  });

  it('calls onAdd with the rating and the CSV watch date, then resets the rating', async () => {
    const user = userEvent.setup();
    const { onAdd } = renderReview([makeMovie()]);

    await user.click(screen.getByRole('radio', { name: '4 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledTimes(1));
    expect(onAdd).toHaveBeenCalledWith(4, '2024-01-15T00:00:00Z');
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: '4 stars' })).toHaveAttribute('aria-checked', 'false')
    );
    expect(screen.getByRole('button', { name: 'Add to My Movies' })).toBeDisabled();
  });

  it('passes undefined as the date when the CSV had none', async () => {
    const user = userEvent.setup();
    const { onAdd } = renderReview(makeMovies(), 1);

    await user.click(screen.getByRole('radio', { name: '2 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(2, undefined));
  });

  it('shows the API error message and keeps the rating when onAdd rejects with an ApiClientError', async () => {
    const user = userEvent.setup();
    const { onAdd } = renderReview([makeMovie()]);
    onAdd.mockRejectedValueOnce(new ApiClientError(409, { detail: 'Movie has already been processed' }));

    await user.click(screen.getByRole('radio', { name: '5 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Movie has already been processed');
    expect(screen.getByRole('radio', { name: '5 stars' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('button', { name: 'Add to My Movies' })).toBeEnabled();
  });

  it('shows a generic message when onAdd rejects with another error', async () => {
    const user = userEvent.setup();
    const { onAdd } = renderReview([makeMovie()]);
    onAdd.mockRejectedValueOnce(new Error('boom'));

    await user.click(screen.getByRole('radio', { name: '3 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to add movie');
  });

  it('clears a previous error when the add is retried', async () => {
    const user = userEvent.setup();
    const { onAdd } = renderReview([makeMovie()]);
    onAdd.mockRejectedValueOnce(new Error('boom'));

    await user.click(screen.getByRole('radio', { name: '3 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));
    await screen.findByRole('alert');

    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(onAdd).toHaveBeenCalledTimes(2);
  });

  it('disables actions and shows a loading label while the add is in flight', async () => {
    const user = userEvent.setup();
    const pending = deferred();
    const { onAdd } = renderReview([makeMovie()]);
    onAdd.mockReturnValueOnce(pending.promise);

    await user.click(screen.getByRole('radio', { name: '4 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    expect(await screen.findByRole('button', { name: 'Loading...' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Add to My Movies' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Skip' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Search for different movie' })).toBeDisabled();

    pending.resolve();
    expect(await screen.findByRole('button', { name: 'Skip' })).toBeEnabled();
  });
});

describe('ImportReview skip flow', () => {
  it('calls onSkip when Skip is clicked, with no rating required', async () => {
    const user = userEvent.setup();
    const { onSkip, onAdd } = renderReview([makeMovie()]);

    await user.click(screen.getByRole('button', { name: 'Skip' }));

    await waitFor(() => expect(onSkip).toHaveBeenCalledTimes(1));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('can skip an unmatched movie', async () => {
    const user = userEvent.setup();
    const { onSkip } = renderReview(makeMovies(), 2);

    await user.click(screen.getByRole('button', { name: 'Skip' }));

    await waitFor(() => expect(onSkip).toHaveBeenCalledTimes(1));
  });

  it('resets the chosen rating after a successful skip', async () => {
    const user = userEvent.setup();
    const { onSkip } = renderReview([makeMovie()]);

    await user.click(screen.getByRole('radio', { name: '5 stars' }));
    await user.click(screen.getByRole('button', { name: 'Skip' }));

    await waitFor(() => expect(onSkip).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: '5 stars' })).toHaveAttribute('aria-checked', 'false')
    );
  });

  it('shows the API error message when onSkip rejects with an ApiClientError', async () => {
    const user = userEvent.setup();
    const { onSkip } = renderReview([makeMovie()]);
    onSkip.mockRejectedValueOnce(new ApiClientError(404, { detail: 'Import session not found or expired' }));

    await user.click(screen.getByRole('button', { name: 'Skip' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Import session not found or expired');
  });

  it('shows a generic message when onSkip rejects with another error', async () => {
    const user = userEvent.setup();
    const { onSkip } = renderReview([makeMovie()]);
    onSkip.mockRejectedValueOnce(new Error('boom'));

    await user.click(screen.getByRole('button', { name: 'Skip' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to skip movie');
  });

  it('disables Skip while the skip is in flight', async () => {
    const user = userEvent.setup();
    const pending = deferred();
    const { onSkip } = renderReview([makeMovie()]);
    onSkip.mockReturnValueOnce(pending.promise);

    await user.click(screen.getByRole('button', { name: 'Skip' }));

    expect(screen.getByRole('button', { name: 'Skip' })).toBeDisabled();
    pending.resolve();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled());
  });
});

describe('ImportReview finished state', () => {
  it('shows the empty message and Finish Import when there are no movies', async () => {
    const user = userEvent.setup();
    const { onComplete } = renderReview([]);

    expect(screen.getByText('No more movies to review.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Skip' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Finish Import' }));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('shows the empty message when currentIndex is past the end of the list', () => {
    renderReview(makeMovies(), 3);
    expect(screen.getByText('No more movies to review.')).toBeInTheDocument();
    expect(screen.queryByText(/ of 3/)).not.toBeInTheDocument();
  });
});
