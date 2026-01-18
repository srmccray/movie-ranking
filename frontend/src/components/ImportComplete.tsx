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
