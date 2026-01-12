import { useState } from 'react';

interface StarRatingProps {
  value: number;
  onChange?: (value: number) => void;
  readonly?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth={filled ? 0 : 2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
      />
    </svg>
  );
}

export function StarRating({
  value,
  onChange,
  readonly = false,
  size = 'md',
}: StarRatingProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);

  const displayValue = hoverValue ?? value;
  const isInteractive = !readonly && onChange;

  const handleClick = (rating: number) => {
    if (isInteractive) {
      onChange(rating);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, rating: number) => {
    if (!isInteractive) return;

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onChange(rating);
    } else if (e.key === 'ArrowRight' && rating < 5) {
      e.preventDefault();
      onChange(rating + 1);
    } else if (e.key === 'ArrowLeft' && rating > 1) {
      e.preventDefault();
      onChange(rating - 1);
    }
  };

  return (
    <div
      className={`star-rating ${size}`}
      role={isInteractive ? 'radiogroup' : 'img'}
      aria-label={`Rating: ${value} out of 5 stars`}
    >
      {[1, 2, 3, 4, 5].map((rating) => (
        <span
          key={rating}
          className={`star ${readonly ? 'readonly' : ''} ${
            rating <= displayValue ? 'star-filled' : 'star-empty'
          }`}
          onClick={() => handleClick(rating)}
          onMouseEnter={() => isInteractive && setHoverValue(rating)}
          onMouseLeave={() => isInteractive && setHoverValue(null)}
          onKeyDown={(e) => handleKeyDown(e, rating)}
          tabIndex={isInteractive ? 0 : -1}
          role={isInteractive ? 'radio' : undefined}
          aria-checked={isInteractive ? rating === value : undefined}
          aria-label={`${rating} star${rating !== 1 ? 's' : ''}`}
        >
          <StarIcon filled={rating <= displayValue} />
        </span>
      ))}
    </div>
  );
}
