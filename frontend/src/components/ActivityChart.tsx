import { useMemo, useState } from 'react';

interface ActivityDay {
  date: string;
  count: number;
}

interface ActivityChartProps {
  activity: ActivityDay[];
  startDate: string;
  endDate: string;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function getActivityLevel(count: number): number {
  if (count === 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  return 3; // 3+ movies
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function ActivityChart({ activity, startDate, endDate }: ActivityChartProps) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; date: string; count: number; isFuture: boolean } | null>(null);

  // Build a map of date -> count for quick lookup
  const activityMap = useMemo(() => {
    const map = new Map<string, number>();
    activity.forEach((day) => {
      map.set(day.date, day.count);
    });
    return map;
  }, [activity]);

  // Get today's date string for comparison
  const todayStr = useMemo(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }, []);

  // Generate all weeks and days for the chart
  const { weeks, monthLabels } = useMemo(() => {
    const weeks: { date: Date; dateStr: string; count: number; isFuture: boolean }[][] = [];

    const start = new Date(startDate + 'T00:00:00');
    const end = new Date(endDate + 'T00:00:00');

    // Adjust start to the beginning of its week (Sunday)
    const adjustedStart = new Date(start);
    adjustedStart.setDate(adjustedStart.getDate() - adjustedStart.getDay());

    let currentDate = new Date(adjustedStart);
    let currentWeek: { date: Date; dateStr: string; count: number; isFuture: boolean }[] = [];

    while (currentDate <= end || currentWeek.length > 0) {
      const dayOfWeek = currentDate.getDay();

      // Start a new week on Sunday
      if (dayOfWeek === 0 && currentWeek.length > 0) {
        weeks.push(currentWeek);
        currentWeek = [];
      }

      // Only include dates within our range
      if (currentDate >= start && currentDate <= end) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const isFuture = dateStr > todayStr;
        currentWeek.push({
          date: new Date(currentDate),
          dateStr,
          count: isFuture ? 0 : (activityMap.get(dateStr) || 0),
          isFuture,
        });
      } else if (currentDate < start) {
        // Placeholder for days before start
        currentWeek.push({
          date: new Date(currentDate),
          dateStr: '',
          count: -1, // Marker for empty
          isFuture: false,
        });
      }

      currentDate.setDate(currentDate.getDate() + 1);

      // Stop after we've passed the end date and completed the week
      if (currentDate > end && dayOfWeek === 6) {
        if (currentWeek.length > 0) {
          weeks.push(currentWeek);
        }
        break;
      }
    }

    // Compute month labels after all weeks are built
    // First collect all month transitions
    const allMonthLabels: { month: string; weekIndex: number }[] = [];
    let lastMonth = -1;

    weeks.forEach((week, weekIndex) => {
      const firstValidDay = week.find(day => day.dateStr !== '');
      if (firstValidDay) {
        const month = firstValidDay.date.getMonth();
        if (month !== lastMonth) {
          allMonthLabels.push({ month: MONTHS[month], weekIndex });
          lastMonth = month;
        }
      }
    });

    // Filter out earlier months that are too close to later ones
    // (keep later month, hide earlier month when overlapping)
    const monthLabels = allMonthLabels.filter((label, i) => {
      const nextLabel = allMonthLabels[i + 1];
      if (nextLabel && nextLabel.weekIndex - label.weekIndex < 4) {
        return false; // Skip this label, it's too close to the next one
      }
      return true;
    });

    return { weeks, monthLabels };
  }, [startDate, endDate, activityMap, todayStr]);

  const handleMouseEnter = (
    e: React.MouseEvent<HTMLDivElement>,
    dateStr: string,
    count: number,
    isFuture: boolean
  ) => {
    if (!dateStr || count < 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      x: rect.left + rect.width / 2,
      y: rect.top,
      date: dateStr,
      count,
      isFuture,
    });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  const totalCount = useMemo(() => {
    return activity.reduce((sum, d) => sum + d.count, 0);
  }, [activity]);

  return (
    <div className="activity-chart">
      <div className="activity-chart-header">
        <h3 className="activity-chart-title">Activity</h3>
        <span className="activity-chart-total">
          {totalCount} movie{totalCount !== 1 ? 's' : ''} rated in the last year
        </span>
      </div>

      <div className="activity-chart-container">
        {/* Month labels */}
        <div className="activity-chart-months">
          {monthLabels.map((label, i) => (
            <div
              key={`${label.month}-${i}`}
              className="activity-chart-month"
              style={{ left: label.weekIndex * 13 }}
            >
              {label.month}
            </div>
          ))}
        </div>

        <div className="activity-chart-grid-wrapper">
          {/* Day labels */}
          <div className="activity-chart-day-labels">
            <span></span>
            <span>Mon</span>
            <span></span>
            <span>Wed</span>
            <span></span>
            <span>Fri</span>
            <span></span>
          </div>

          {/* Grid */}
          <div className="activity-chart-grid">
            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="activity-chart-week">
                {week.map((day, dayIndex) => (
                  <div
                    key={`${weekIndex}-${dayIndex}`}
                    className={`activity-chart-day ${
                      day.count < 0
                        ? 'activity-empty'
                        : day.isFuture
                        ? 'activity-future'
                        : `activity-level-${getActivityLevel(day.count)}`
                    }`}
                    onMouseEnter={(e) => handleMouseEnter(e, day.dateStr, day.count, day.isFuture)}
                    onMouseLeave={handleMouseLeave}
                    aria-label={
                      day.dateStr && day.count >= 0
                        ? day.isFuture
                          ? `${formatDate(day.dateStr)} (future)`
                          : `${day.count} movie${day.count !== 1 ? 's' : ''} on ${formatDate(day.dateStr)}`
                        : undefined
                    }
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="activity-chart-legend">
        <span className="activity-chart-legend-label">Less</span>
        <div className="activity-chart-day activity-level-0" />
        <div className="activity-chart-day activity-level-1" />
        <div className="activity-chart-day activity-level-2" />
        <div className="activity-chart-day activity-level-3" />
        <span className="activity-chart-legend-label">More</span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="activity-chart-tooltip"
          style={{
            left: tooltip.x,
            top: tooltip.y,
          }}
        >
          {tooltip.isFuture ? (
            <span>{formatDate(tooltip.date)}</span>
          ) : (
            <>
              <strong>{tooltip.count} movie{tooltip.count !== 1 ? 's' : ''}</strong>
              <span>{formatDate(tooltip.date)}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
