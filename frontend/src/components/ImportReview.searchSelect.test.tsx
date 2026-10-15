/**
 * Characterization tests for ImportReview manual search: keyboard and mouse selection,
 * the PATCH match request, selection errors, closing, and reset when the movie changes.
 * Opening, debounce, results and loading/empty/error states: ImportReview.search.test.tsx.
 */

import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ImportReview } from './ImportReview';
import { server } from '../__tests__/mocks/server';
import { MOCK_TMDB_RESULTS } from '../__tests__/mocks/handlers';
import {
  SESSION_ID,
  advance,
  makeCallbacks,
  makeMovies,
  recordSearches,
  useFakeSearchTimers,
} from '../__tests__/helpers/importReview';
import { ReviewHost } from '../__tests__/helpers/ReviewHost';
import type { MatchedMovieItem } from '../types';

const DEBOUNCE = 300;
const MATCH_URL = `/api/v1/import/amazon-prime/session/${SESSION_ID}/movie/:index/match/`;

interface CapturedPatch {
  url: string;
  body: Record<string, unknown>;
}

/** Overrides the PATCH match endpoint, recording requests; `reply` decides the response. */
function recordMatchPatches(
  reply: (body: Record<string, unknown>) => Response = (body) =>
    HttpResponse.json({
      parsed: { title: 'Unknown Movie 2024', watch_date: null, prime_image_url: null },
      tmdb_match: body,
      confidence: 1,
      alternatives: [],
      status: 'pending',
    })
) {
  const patches: CapturedPatch[] = [];
  server.use(
    http.patch(MATCH_URL, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      patches.push({ url: new URL(request.url).pathname, body });
      return reply(body);
    })
  );
  return patches;
}

const searchInput = () => screen.getByRole('textbox', { name: 'Search movies' });

/** Renders the review at `index`, opens search and waits for the default Matrix results. */
async function openWithResults(index = 0, onMovieUpdated = vi.fn()) {
  const user = userEvent.setup({ delay: null });
  const utils = render(<ReviewHost initialMovies={makeMovies()} currentIndex={index} onMovieUpdated={onMovieUpdated} />);
  await user.click(
    screen.getByRole('button', { name: index === 2 ? 'Search for this movie' : 'Search for different movie' })
  );
  if (index === 2) {
    // The unmatched title finds nothing in the default handler; search for something real.
    fireEvent.change(searchInput(), { target: { value: 'The Matrix' } });
  }
  await advance(DEBOUNCE);
  await screen.findByRole('listbox');
  return { user, onMovieUpdated, ...utils };
}

const selectedStates = () => screen.getAllByRole('option').map((o) => o.getAttribute('aria-selected'));

describe('ImportReview search keyboard navigation', () => {
  useFakeSearchTimers();

  it('ArrowDown highlights the first result, then moves down and stops at the last', async () => {
    const { user } = await openWithResults();
    expect(selectedStates()).toEqual(['false', 'false', 'false']);

    await user.keyboard('{ArrowDown}');
    expect(selectedStates()).toEqual(['true', 'false', 'false']);

    await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}');
    expect(selectedStates()).toEqual(['false', 'false', 'true']);
  });

  it('ArrowUp moves the highlight up and clears it when pressed on the first result', async () => {
    const { user } = await openWithResults();

    await user.keyboard('{ArrowDown}{ArrowDown}{ArrowUp}');
    expect(selectedStates()).toEqual(['true', 'false', 'false']);

    await user.keyboard('{ArrowUp}');
    expect(selectedStates()).toEqual(['false', 'false', 'false']);
  });

  it('scrolls the highlighted option into view', async () => {
    const { user } = await openWithResults();

    await user.keyboard('{ArrowDown}');

    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });

  it('Enter with nothing highlighted sends no request and keeps the panel open', async () => {
    const patches = recordMatchPatches();
    const { user } = await openWithResults();

    await user.keyboard('{Enter}');
    await advance(DEBOUNCE);

    expect(patches).toHaveLength(0);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('Enter on the highlighted result selects it', async () => {
    const patches = recordMatchPatches();
    const { user } = await openWithResults();

    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

    await waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0].body).toMatchObject({ tmdb_id: MOCK_TMDB_RESULTS[1].tmdb_id, title: 'The Matrix Reloaded' });
  });

  it('Escape closes the panel and restores the movie card', async () => {
    const { user } = await openWithResults();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('textbox', { name: 'Search movies' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'The Matrix' })).toBeInTheDocument();
  });

  it('Escape closes the panel even before any results have arrived', async () => {
    const user = userEvent.setup({ delay: null });
    render(<ReviewHost initialMovies={makeMovies()} />);
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('textbox', { name: 'Search movies' })).not.toBeInTheDocument();
  });

  it('ignores arrow keys and Enter when there are no results', async () => {
    const patches = recordMatchPatches();
    const user = userEvent.setup({ delay: null });
    render(<ReviewHost initialMovies={makeMovies()} />);
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));

    await user.keyboard('{ArrowDown}{ArrowUp}{Enter}');

    expect(searchInput()).toBeInTheDocument();
    expect(patches).toHaveLength(0);
  });

  it('clears the highlight when a new search returns results', async () => {
    const { user } = await openWithResults();
    await user.keyboard('{ArrowDown}');
    expect(selectedStates()[0]).toBe('true');

    fireEvent.change(searchInput(), { target: { value: 'Matrix R' } });
    await advance(DEBOUNCE);
    await waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(2));

    expect(selectedStates()).toEqual(['false', 'false']);
  });
});

describe('ImportReview search selection', () => {
  useFakeSearchTimers();

  it('highlights an option on mouse hover', async () => {
    const { user } = await openWithResults();

    await user.hover(screen.getAllByRole('option')[1]);

    expect(selectedStates()).toEqual(['false', 'true', 'false']);
  });

  it('PATCHes the chosen result to this session and movie index when clicked', async () => {
    const patches = recordMatchPatches();
    const { user } = await openWithResults(2);

    await user.click(screen.getAllByRole('option')[0]);

    await waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0].url).toBe(`/api/v1/import/amazon-prime/session/${SESSION_ID}/movie/2/match/`);
    expect(patches[0].body).toEqual({
      tmdb_id: 603,
      title: 'The Matrix',
      year: 1999,
      poster_url: 'https://image.tmdb.org/t/p/w185/abc123.jpg',
      overview: 'A computer hacker learns about the true nature of reality.',
      genre_ids: [28, 878],
      vote_average: 8.7,
      vote_count: 24000,
      release_date: '1999-03-30',
      original_language: 'en',
    });
  });

  it('reports the updated movie via onMovieUpdated, closes the panel and shows the new match', async () => {
    recordMatchPatches();
    const { user, onMovieUpdated } = await openWithResults(2);
    await user.click(screen.getByRole('option', { name: /The Matrix Reloaded/ }));

    expect(await screen.findByRole('heading', { name: 'The Matrix Reloaded' })).toBeInTheDocument();
    expect(onMovieUpdated).toHaveBeenCalledTimes(1);
    const [index, updated] = onMovieUpdated.mock.calls[0] as [number, MatchedMovieItem];
    expect(index).toBe(2);
    expect(updated.tmdb_match?.tmdb_id).toBe(604);
    expect(screen.queryByRole('textbox', { name: 'Search movies' })).not.toBeInTheDocument();
    // Once matched, the movie can be rated and added; confidence reflects the user's choice.
    expect(screen.getByText('High confidence match')).toBeInTheDocument();
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    expect(screen.queryByText('No match found for:')).not.toBeInTheDocument();
  });

  it('disables the input and Cancel while the match request is in flight', async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => { release = r; });
    server.use(
      http.patch(MATCH_URL, async () => {
        await gate;
        return HttpResponse.json({ detail: 'late' }, { status: 500 });
      })
    );
    const { user } = await openWithResults();

    await user.click(screen.getAllByRole('option')[0]);

    expect(searchInput()).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    release();
    await waitFor(() => expect(searchInput()).toBeEnabled());
  });

  it('shows the API error, keeps the panel and results open, and does not update the movie', async () => {
    recordMatchPatches(() => HttpResponse.json({ detail: 'Import session not found or expired' }, { status: 404 }));
    const { user, onMovieUpdated } = await openWithResults();

    await user.click(screen.getAllByRole('option')[0]);

    expect(await screen.findByRole('alert')).toHaveTextContent('Import session not found or expired');
    expect(onMovieUpdated).not.toHaveBeenCalled();
    expect(screen.getAllByRole('option')).toHaveLength(3);
    expect(searchInput()).toBeEnabled();
  });

  it('shows a generic message when the match request fails at the network level', async () => {
    recordMatchPatches(() => HttpResponse.error());
    const { user } = await openWithResults();

    await user.click(screen.getAllByRole('option')[0]);

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to update movie match');
  });

  it('clears a previous selection error on the next attempt', async () => {
    let calls = 0;
    recordMatchPatches((body) => {
      calls += 1;
      return calls === 1
        ? HttpResponse.json({ detail: 'try again' }, { status: 500 })
        : HttpResponse.json({ parsed: { title: 'The Matrix', watch_date: null, prime_image_url: null }, tmdb_match: body, confidence: 1, alternatives: [], status: 'pending' });
    });
    const { user } = await openWithResults();

    await user.click(screen.getAllByRole('option')[0]);
    await screen.findByRole('alert');
    await user.click(screen.getAllByRole('option')[0]);

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(calls).toBe(2);
  });
});

describe('ImportReview search closing and reset', () => {
  useFakeSearchTimers();

  it('Cancel closes the panel and restores the card without any match request', async () => {
    const patches = recordMatchPatches();
    const { user } = await openWithResults();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('textbox', { name: 'Search movies' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'The Matrix' })).toBeInTheDocument();
    expect(patches).toHaveLength(0);
  });

  it('stops searching once closed', async () => {
    const queries = recordSearches();
    const user = userEvent.setup({ delay: null });
    render(<ReviewHost initialMovies={makeMovies()} />);
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    await advance(DEBOUNCE * 3);

    expect(queries).toHaveLength(0);
  });

  it('reopening resets the query to the parsed title and drops old results and errors', async () => {
    const { user } = await openWithResults();
    fireEvent.change(searchInput(), { target: { value: 'something else' } });
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));

    expect(searchInput()).toHaveValue('The Matrix');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(searchInput()).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes the panel and drops its results when the current movie changes', async () => {
    const user = userEvent.setup({ delay: null });
    const callbacks = makeCallbacks();
    const movies = makeMovies();
    const { rerender } = render(
      <ImportReview movies={movies} currentIndex={0} sessionId={SESSION_ID} {...callbacks} />
    );
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));
    await advance(DEBOUNCE);
    await screen.findByRole('listbox');

    rerender(<ImportReview movies={movies} currentIndex={1} sessionId={SESSION_ID} {...callbacks} />);

    expect(screen.queryByRole('textbox', { name: 'Search movies' })).not.toBeInTheDocument();
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Inception' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));
    expect(searchInput()).toHaveValue('Inception');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows a search error only until the movie changes', async () => {
    server.use(http.get('/api/v1/movies/search/', () => HttpResponse.json({ detail: 'down' }, { status: 500 })));
    const user = userEvent.setup({ delay: null });
    const callbacks = makeCallbacks();
    const movies = makeMovies();
    const { rerender } = render(
      <ImportReview movies={movies} currentIndex={0} sessionId={SESSION_ID} {...callbacks} />
    );
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));
    await advance(DEBOUNCE);
    await screen.findByRole('alert');

    rerender(<ImportReview movies={movies} currentIndex={1} sessionId={SESSION_ID} {...callbacks} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
