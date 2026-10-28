/**
 * Characterization tests for ImportWizard: upload -> review -> complete, driven through the
 * rendered UI against the shared MSW import handlers (real ImportReview, no mocked children).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ImportWizard } from './ImportWizard';
import { server } from '../__tests__/mocks/server';
import { setMockSession, createMockImportSession, resetMockData } from '../__tests__/mocks/handlers';
import { importSessions } from '../__tests__/mocks/handlers/import';

type User = ReturnType<typeof userEvent.setup>;

function renderWizard() {
  const onClose = vi.fn();
  const onComplete = vi.fn();
  const user = userEvent.setup();
  render(<ImportWizard onClose={onClose} onComplete={onComplete} />);
  return { user, onClose, onComplete };
}

async function uploadCsv(user: User) {
  const file = new File(['Type,Title\nMovie,The Matrix'], 'watch-history.csv', { type: 'text/csv' });
  await user.upload(screen.getByLabelText('Select CSV file'), file);
  await user.click(screen.getByRole('button', { name: 'Upload and Continue' }));
  await screen.findByRole('heading', { name: 'Review Movies' });
}

const stat = (label: string) => screen.getByText(label).previousElementSibling;

describe('ImportWizard', () => {
  beforeEach(() => {
    resetMockData();
    setMockSession(true);
    Element.prototype.scrollIntoView = vi.fn(); // not implemented by jsdom
    // jsdom's FormData is not understood by Node's fetch (it throws while serializing the body),
    // so drop FormData bodies; the upload handler below does not read the body anyway.
    const realFetch = globalThis.fetch;
    vi.stubGlobal('fetch', (input: RequestInfo | URL, init?: RequestInit) =>
      realFetch(input, init?.body instanceof FormData ? { ...init, body: undefined } : init)
    );
    // The shared upload handler rejects any request whose Content-Type is not multipart/form-data,
    // but under jsdom fetch() does not serialize FormData as multipart, so it always answers 422.
    // Replace only that upload endpoint; every later import call uses the shared handlers.
    server.use(
      http.post('/api/v1/import/amazon-prime/upload/', () => {
        const session = importSessions.get(createMockImportSession())!;
        return HttpResponse.json({
          session_id: session.session_id,
          total_entries: session.total_entries,
          movies_found: session.movies_found,
          tv_shows_filtered: session.tv_shows_filtered,
          already_ranked: session.already_ranked,
          ready_for_review: session.movies.length,
          movies: session.movies,
        });
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setMockSession(false);
  });

  it('starts on the upload step with Upload disabled until a file is chosen', () => {
    renderWizard();

    expect(screen.getByRole('heading', { name: 'Import from Amazon Prime' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload and Continue' })).toBeDisabled();
  });

  it('moves from upload to the first movie of the review step', async () => {
    const { user } = renderWizard();

    await uploadCsv(user);

    expect(screen.getByRole('heading', { name: 'The Matrix' })).toBeInTheDocument();
    expect(screen.getByText('1 of 3')).toBeInTheDocument();
  });

  it('reviews every movie (add, skip, re-match an unmatched one) through to the summary', async () => {
    const { user, onComplete, onClose } = renderWizard();
    await uploadCsv(user);

    // 1/3: rate and add The Matrix
    await user.click(screen.getByRole('radio', { name: '5 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    // 2/3: skip Inception
    expect(await screen.findByRole('heading', { name: 'Inception' })).toBeInTheDocument();
    expect(screen.getByText('2 of 3')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '5 stars' })).toHaveAttribute('aria-checked', 'false');
    await user.click(screen.getByRole('button', { name: 'Skip' }));

    // 3/3: unmatched -> search, pick a match, rate and add it
    expect(await screen.findByText('No match found for:')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Search for this movie' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Search movies' }), { target: { value: 'Reloaded' } });
    await user.click(await screen.findByRole('option', { name: /The Matrix Reloaded/ }));
    expect(await screen.findByRole('heading', { name: 'The Matrix Reloaded' })).toBeInTheDocument();
    await user.click(screen.getByRole('radio', { name: '3 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    // Summary
    expect(await screen.findByRole('heading', { name: 'Import Complete' })).toBeInTheDocument();
    expect(stat('Movies Added')).toHaveTextContent('2');
    expect(stat('Movies Skipped')).toHaveTextContent('1');
    expect(screen.queryByText(/Unmatched Titles/)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Done' }));
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('lists still-unmatched titles on the summary when everything is skipped', async () => {
    const { user } = renderWizard();
    await uploadCsv(user);

    await user.click(screen.getByRole('button', { name: 'Skip' }));
    await screen.findByRole('heading', { name: 'Inception' });
    await user.click(screen.getByRole('button', { name: 'Skip' }));
    await screen.findByText('No match found for:');
    await user.click(screen.getByRole('button', { name: 'Skip' }));

    expect(await screen.findByRole('heading', { name: 'Import Complete' })).toBeInTheDocument();
    expect(stat('Movies Added')).toHaveTextContent('0');
    expect(stat('Movies Skipped')).toHaveTextContent('3');
    expect(screen.getByRole('heading', { name: 'Unmatched Titles (1)' })).toBeInTheDocument();
    expect(within(screen.getByRole('list')).getByText('Unknown Movie 2024')).toBeInTheDocument();
  });

  it('sends the rating and CSV watch date to the add endpoint', async () => {
    let body: unknown;
    server.use(
      http.post('/api/v1/import/amazon-prime/session/:sessionId/movie/:index/add/', async ({ request, params }) => {
        body = { ...(await request.json() as object), index: params.index };
        return HttpResponse.json({ id: 'r1' }, { status: 201 });
      })
    );
    const { user } = renderWizard();
    await uploadCsv(user);

    await user.click(screen.getByRole('radio', { name: '4 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    await screen.findByRole('heading', { name: 'Inception' });
    expect(body).toEqual({ rating: 4, rated_at: '2024-01-15T00:00:00Z', index: '0' });
  });

  it('stays on the same movie and shows the API error when adding fails', async () => {
    server.use(
      http.post('/api/v1/import/amazon-prime/session/:sessionId/movie/:index/add/', () =>
        HttpResponse.json({ detail: 'Movie has already been processed' }, { status: 409 })
      )
    );
    const { user } = renderWizard();
    await uploadCsv(user);

    await user.click(screen.getByRole('radio', { name: '4 stars' }));
    await user.click(screen.getByRole('button', { name: 'Add to My Movies' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Movie has already been processed');
    expect(screen.getByText('1 of 3')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Review Movies' })).toBeInTheDocument();
  });

  it('goes straight to the summary when the upload contains no movies', async () => {
    server.use(
      http.post('/api/v1/import/amazon-prime/upload/', () =>
        HttpResponse.json({
          session_id: 'empty-session',
          total_entries: 0,
          movies_found: 0,
          tv_shows_filtered: 0,
          already_ranked: 0,
          ready_for_review: 0,
          movies: [],
        })
      )
    );
    const { user } = renderWizard();

    const file = new File(['Type,Title\n'], 'empty.csv', { type: 'text/csv' });
    await user.upload(screen.getByLabelText('Select CSV file'), file);
    await user.click(screen.getByRole('button', { name: 'Upload and Continue' }));

    expect(await screen.findByRole('heading', { name: 'Import Complete' })).toBeInTheDocument();
    expect(stat('Movies Added')).toHaveTextContent('0');
    expect(stat('Movies Skipped')).toHaveTextContent('0');
  });

  it('cancels the server session and closes when the modal is dismissed during review', async () => {
    const deleted: string[] = [];
    server.use(
      http.delete('/api/v1/import/amazon-prime/session/:sessionId/', ({ params }) => {
        deleted.push(params.sessionId as string);
        return new HttpResponse(null, { status: 204 });
      })
    );
    const { user, onClose, onComplete } = renderWizard();
    await uploadCsv(user);

    await user.click(screen.getByRole('button', { name: 'Close modal' }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(deleted).toHaveLength(1);
    expect(deleted[0]).toMatch(/^test-session-/);
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('closes without a cancel request when dismissed before uploading', async () => {
    const deleted: string[] = [];
    server.use(
      http.delete('/api/v1/import/amazon-prime/session/:sessionId/', ({ params }) => {
        deleted.push(params.sessionId as string);
        return new HttpResponse(null, { status: 204 });
      })
    );
    const { user, onClose } = renderWizard();

    await user.click(screen.getByRole('button', { name: 'Close modal' }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(deleted).toHaveLength(0);
  });
});
