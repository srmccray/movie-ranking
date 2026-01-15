/**
 * Tests for GoogleSignInButton component.
 *
 * These tests verify:
 * - Button renders with correct text for each variant
 * - Loading state shows spinner
 * - Click handler is called
 * - Disabled state works correctly
 * - Accessibility attributes are present
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GoogleSignInButton } from './GoogleSignInButton';

describe('GoogleSignInButton', () => {
  describe('rendering', () => {
    it('should render with default signin text', () => {
      render(<GoogleSignInButton />);

      expect(screen.getByRole('button')).toHaveTextContent('Sign in with Google');
    });

    it('should render with signup text when variant is signup', () => {
      render(<GoogleSignInButton variant="signup" />);

      expect(screen.getByRole('button')).toHaveTextContent('Sign up with Google');
    });

    it('should render Google logo', () => {
      render(<GoogleSignInButton />);

      // Check for SVG element (Google logo)
      const svg = document.querySelector('.google-logo');
      expect(svg).toBeInTheDocument();
    });

    it('should have aria-label for accessibility', () => {
      render(<GoogleSignInButton />);

      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Sign in with Google');
    });

    it('should have correct aria-label for signup variant', () => {
      render(<GoogleSignInButton variant="signup" />);

      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Sign up with Google');
    });

    it('should apply custom className', () => {
      render(<GoogleSignInButton className="custom-class" />);

      expect(screen.getByRole('button')).toHaveClass('custom-class');
    });

    it('should apply btn-google class', () => {
      render(<GoogleSignInButton />);

      expect(screen.getByRole('button')).toHaveClass('btn-google');
    });
  });

  describe('loading state', () => {
    it('should show loading text when loading', () => {
      render(<GoogleSignInButton loading />);

      expect(screen.getByRole('button')).toHaveTextContent('Loading...');
    });

    it('should be disabled when loading', () => {
      render(<GoogleSignInButton loading />);

      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should not show Google logo when loading', () => {
      render(<GoogleSignInButton loading />);

      const svg = document.querySelector('.google-logo');
      expect(svg).not.toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('should be disabled when disabled prop is true', () => {
      render(<GoogleSignInButton disabled />);

      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should not call onClick when disabled', () => {
      const handleClick = vi.fn();
      render(<GoogleSignInButton disabled onClick={handleClick} />);

      fireEvent.click(screen.getByRole('button'));

      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('click handling', () => {
    it('should call onClick when clicked', () => {
      const handleClick = vi.fn();
      render(<GoogleSignInButton onClick={handleClick} />);

      fireEvent.click(screen.getByRole('button'));

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when loading', () => {
      const handleClick = vi.fn();
      render(<GoogleSignInButton loading onClick={handleClick} />);

      fireEvent.click(screen.getByRole('button'));

      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('fullWidth', () => {
    it('should apply btn-full class when fullWidth is true', () => {
      render(<GoogleSignInButton fullWidth />);

      expect(screen.getByRole('button')).toHaveClass('btn-full');
    });

    it('should not apply btn-full class when fullWidth is false', () => {
      render(<GoogleSignInButton fullWidth={false} />);

      expect(screen.getByRole('button')).not.toHaveClass('btn-full');
    });
  });
});
