/**
 * Characterization tests for the ImportReview manual search panel:
 * opening, focus, debounce, results, loading / empty / error states, and ARIA.
 * Keyboard, selection and reset behavior: ImportReview.searchSelect.test.tsx.
 *
 * Timers are faked deliberately (setTimeout/clearTimeout only) so the 300ms debounce is
 * asserted exactly; network I/O goes through real fetch + MSW.
 */

import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ImportReview } from './ImportReview';
import { server } from '../__tests__/mocks/server';
import { MOCK_TMDB_RESULTS } from '../__tests__/mocks/handlers';
import {
  SESSION_ID,
  makeCallbacks,
  makeMovies,
  advance,
  makeSearchResults,
  recordSearches,
  useFakeSearchTimers,
} from '../__tests__/helpers/importReview';

const DEBOUNCE = 300;

function renderReview(currentIndex = 0) {
  const callbacks = makeCallbacks();
  const utils = render(
    <ImportReview movies={makeMovies()} currentIndex={currentIndex} sessionId={SESSION_ID} {...callbacks} />
  );
  return { ...utils, ...callbacks };
}

const searchInput = () => screen.getByRole('textbox', { name: 'Search movies' });

describe('ImportReview search panel', () => {
  useFakeSearchTimers();

  async function openSearch(label = 'Search for different movie') {
    const user = userEvent.setup({ delay: null });
    renderReview(label === 'Search for this movie' ? 2 : 0);
    await user.click(screen.getByRole('button', { name: label }));
    return user;
  }

  describe('opening', () => {
    it('replaces the card with the search panel, prefilled with the parsed title', async () => {
      await openSearch();

      expect(screen.getByText('Search for:')).toBeInTheDocument();
      expect(searchInput()).toHaveValue('The Matrix');
      expect(screen.queryByRole('heading', { name: 'The Matrix' })).not.toBeInTheDocument();
      expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Skip' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Add to My Movies' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
    });

    it('opens from the unmatched state via "Search for this movie"', async () => {
      await openSearch('Search for this movie');

      expect(searchInput()).toHaveValue('Unknown Movie 2024');
      expect(screen.queryByText('No match found for:')).not.toBeInTheDocument();
    });

    it('focuses the search input on open', async () => {
      await openSearch();
      expect(searchInput()).toHaveFocus();
    });

    it('exposes combobox-style ARIA attributes on the input', async () => {
      await openSearch();

      const input = searchInput();
      expect(input).toHaveAttribute('aria-autocomplete', 'list');
      expect(input).toHaveAttribute('aria-controls', 'import-search-results');
      expect(input).toHaveAttribute('aria-expanded', 'false');
      expect(input).toHaveAttribute('placeholder', 'Search for a movie...');
    });
  });

  describe('debounce', () => {
    it('sends no request before the delay and exactly one after it', async () => {
      const queries = recordSearches();
      await openSearch();

      await advance(DEBOUNCE - 1);
      expect(queries).toHaveLength(0);

      await advance(1);
      await screen.findByText('No movies found for "The Matrix"');
      expect(queries).toEqual(['The Matrix']);

      await advance(2000);
      expect(queries).toHaveLength(1);
    });

    it('restarts the delay on every keystroke and searches only the final text', async () => {
      const queries = recordSearches();
      await openSearch();

      fireEvent.change(searchInput(), { target: { value: 'Mat' } });
      await advance(200);
      fireEvent.change(searchInput(), { target: { value: 'Matr' } });
      await advance(200);
      fireEvent.change(searchInput(), { target: { value: 'Matrix' } });
      await advance(DEBOUNCE - 1);
      expect(queries).toHaveLength(0);

      await advance(1);
      await screen.findByText('No movies found for "Matrix"');
      expect(queries).toEqual(['Matrix']);
    });

    it('trims the query sent to the API', async () => {
      const queries = recordSearches();
      await openSearch();

      fireEvent.change(searchInput(), { target: { value: '  Heat  ' } });
      await advance(DEBOUNCE);
      await screen.findByText(/No movies found for/);

      expect(queries).toEqual(['Heat']);
    });

    it('does not search a blank query and shows no result message', async () => {
      const queries = recordSearches();
      await openSearch();

      fireEvent.change(searchInput(), { target: { value: '   ' } });
      await advance(DEBOUNCE * 3);

      expect(queries).toHaveLength(0);
      expect(screen.queryByText(/No movies found/)).not.toBeInTheDocument();
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });
  });

  describe('results', () => {
    it('lists results from the API with title and year as options in a labelled listbox', async () => {
      await openSearch();
      await advance(DEBOUNCE);

      const listbox = await screen.findByRole('listbox', { name: 'Search results' });
      expect(listbox).toHaveAttribute('id', 'import-search-results');
      const options = screen.getAllByRole('option');
      expect(options).toHaveLength(MOCK_TMDB_RESULTS.length);
      expect(options[0]).toHaveTextContent('The Matrix');
      expect(options[0]).toHaveTextContent('1999');
      expect(options[1]).toHaveTextContent('The Matrix Reloaded');
      expect(options[1]).toHaveTextContent('2003');
      options.forEach((o) => expect(o).toHaveAttribute('aria-selected', 'false'));
    });

    it('sets aria-expanded true on the input while results are shown', async () => {
      await openSearch();
      await advance(DEBOUNCE);
      await screen.findByRole('listbox');

      expect(searchInput()).toHaveAttribute('aria-expanded', 'true');
    });

    it('renders poster images when present and a placeholder without one', async () => {
      const [withPoster, withoutPoster] = makeSearchResults(2);
      recordSearches(() => [{ ...withPoster, poster_url: 'https://img.example/p.jpg' }, withoutPoster]);
      await openSearch();
      await advance(DEBOUNCE);

      const options = await screen.findAllByRole('option');
      expect(options[0].querySelector('img')).toHaveAttribute('src', 'https://img.example/p.jpg');
      expect(options[0].querySelector('img')).toHaveAttribute('alt', ''); // decorative
      expect(options[1].querySelector('img')).toBeNull();
    });

    it('omits the year for results without one', async () => {
      const [first] = makeSearchResults(1);
      recordSearches(() => [{ ...first, year: null }]);
      await openSearch();
      await advance(DEBOUNCE);

      const option = await screen.findByRole('option');
      expect(option).toHaveTextContent('Result 1');
      expect(option.textContent).not.toMatch(/\d{4}/);
    });

    it('caps the list at 10 results', async () => {
      recordSearches(() => makeSearchResults(15));
      await openSearch();
      await advance(DEBOUNCE);

      const options = await screen.findAllByRole('option');
      expect(options).toHaveLength(10);
      expect(options[9]).toHaveTextContent('Result 10');
      expect(screen.queryByText('Result 11')).not.toBeInTheDocument();
    });
  });

  describe('loading, empty and error states', () => {
    it('shows a spinner while the request is in flight and removes it afterwards', async () => {
      let release!: () => void;
      const gate = new Promise<void>((r) => { release = r; });
      server.use(
        http.get('/api/v1/movies/search/', async () => {
          await gate;
          return HttpResponse.json({ results: [], query: 'x', year: null });
        })
      );
      const { container } = (await openSearchWithContainer());

      await advance(DEBOUNCE);
      expect(container.querySelector('.import-search-spinner')).toBeInTheDocument();
      expect(screen.queryByText(/No movies found/)).not.toBeInTheDocument();

      release();
      await screen.findByText(/No movies found/);
      expect(container.querySelector('.import-search-spinner')).not.toBeInTheDocument();
    });

    it('shows a no-results message quoting the typed query', async () => {
      await openSearch();

      fireEvent.change(searchInput(), { target: { value: 'zzzz' } });
      await advance(DEBOUNCE);

      expect(await screen.findByText('No movies found for "zzzz"')).toBeInTheDocument();
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('shows the API error detail in an alert and no results', async () => {
      server.use(
        http.get('/api/v1/movies/search/', () =>
          HttpResponse.json({ detail: 'TMDB rate limit exceeded. Please try again later.' }, { status: 503 })
        )
      );
      await openSearch();
      await advance(DEBOUNCE);

      expect(await screen.findByRole('alert')).toHaveTextContent('TMDB rate limit exceeded. Please try again later.');
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      expect(screen.queryByText(/No movies found/)).not.toBeInTheDocument();
    });

    it('shows a generic message when the request fails at the network level', async () => {
      server.use(http.get('/api/v1/movies/search/', () => HttpResponse.error()));
      await openSearch();
      await advance(DEBOUNCE);

      expect(await screen.findByRole('alert')).toHaveTextContent('Failed to search movies');
    });

    it('clears a search error when a later search succeeds', async () => {
      server.use(
        http.get('/api/v1/movies/search/', () => HttpResponse.json({ detail: 'nope' }, { status: 500 }), { once: true })
      );
      await openSearch();
      await advance(DEBOUNCE);
      await screen.findByRole('alert');

      fireEvent.change(searchInput(), { target: { value: 'Matrix' } });
      await advance(DEBOUNCE);

      await screen.findByRole('listbox');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  async function openSearchWithContainer() {
    const user = userEvent.setup({ delay: null });
    const utils = renderReview();
    await user.click(screen.getByRole('button', { name: 'Search for different movie' }));
    return utils;
  }
});
