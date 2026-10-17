/**
 * Interaction tests for MovieSearch component.
 *
 * These tests verify:
 * - Keyboard navigation works (arrow keys, enter, escape)
 * - Mouse interaction works (hover, click)
 * - Error messages are displayed
 * - ARIA state updates
 *
 * Rendering, search behavior and result display tests live in MovieSearch.test.tsx.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MovieSearch } from './MovieSearch';
import {
  resetMockData,
  setTmdbServiceError,
  setMockSession,
} from '../__tests__/mocks/handlers';

// Mock scrollIntoView which is not available in JSDOM
Element.prototype.scrollIntoView = vi.fn();

// Helper to render MovieSearch with auth set up
function renderMovieSearch(onSelect = vi.fn()) {
  // Set up authenticated state
  setMockSession(true);

  return {
    ...render(<MovieSearch onSelect={onSelect} />),
    onSelect,
  };
}

describe('MovieSearch', () => {
  beforeEach(() => {
    resetMockData();
    setMockSession(false);
    // Use fake timers for debounce testing
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('keyboard navigation', () => {
    it('should highlight next result on ArrowDown', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}');

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });

    it('should highlight previous result on ArrowUp', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      // Navigate down twice, then up once
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowUp}');

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });

    it('should select highlighted result on Enter', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const onSelect = vi.fn();
      renderMovieSearch(onSelect);

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}');
      await user.keyboard('{Enter}');

      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'The Matrix',
        })
      );
    });

    it('should clear results on Escape', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{Escape}');

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('should not go below last result on ArrowDown', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      const options = screen.getAllByRole('option');
      const numOptions = options.length;

      // Press ArrowDown more times than there are results
      for (let i = 0; i < numOptions + 5; i++) {
        await user.keyboard('{ArrowDown}');
      }

      // Last option should be selected
      expect(options[numOptions - 1]).toHaveAttribute('aria-selected', 'true');
    });

    it('should go back to no selection on ArrowUp from first item', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowUp}');

      const options = screen.getAllByRole('option');
      options.forEach((option) => {
        expect(option).toHaveAttribute('aria-selected', 'false');
      });
    });
  });

  describe('mouse interaction', () => {
    it('should highlight result on mouse enter', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      const options = screen.getAllByRole('option');
      await user.hover(options[1]);

      expect(options[1]).toHaveClass('highlighted');
    });

    it('should call onSelect on click', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const onSelect = vi.fn();
      renderMovieSearch(onSelect);

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      const options = screen.getAllByRole('option');
      await user.click(options[0]);

      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'The Matrix',
        })
      );
    });
  });

  describe('error handling', () => {
    it('should show error message on rate limit', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      setTmdbServiceError('rate_limit');
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
      });
    });

    it('should show error message on API error', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      setTmdbServiceError('api_error');
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
      });
    });

    it('should show error message on service unavailable', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      setTmdbServiceError('unavailable');
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
      });
    });
  });

  describe('ARIA state updates', () => {
    it('should set aria-expanded to true when results are shown', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      expect(input).toHaveAttribute('aria-expanded', 'false');

      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-expanded', 'true');
      });
    });

    it('should set aria-expanded to false when results are hidden', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderMovieSearch();

      const input = screen.getByRole('textbox', { name: /search movies/i });
      await user.type(input, 'matrix');

      await vi.advanceTimersByTimeAsync(350);

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-expanded', 'true');
      });

      await user.keyboard('{Escape}');

      expect(input).toHaveAttribute('aria-expanded', 'false');
    });
  });
});
