'use client';

/**
 * ScoreGauge Component
 * Simple CSS circular progress display for Cognitive Stability Score.
 * No D3 or new chart library — pure CSS arc.
 */
export default function ScoreGauge({ score = 0 }) {
  // Clamp score to 0–100
  const clamped = Math.max(0, Math.min(100, score ?? 0));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  // Color: red < 40, amber 40-60, teal 60-80, green > 80
  let color = 'var(--teal)';
  if (clamped < 40) color = '#c0392b';
  else if (clamped < 60) color = '#e67e22';
  else if (clamped > 80) color = '#27ae60';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '20px',
      }}
    >
      <svg width="130" height="130" viewBox="0 0 130 130">
        {/* Background circle */}
        <circle
          cx="65"
          cy="65"
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth="10"
        />
        {/* Score arc */}
        <circle
          cx="65"
          cy="65"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 65 65)"
          style={{ transition: 'stroke-dashoffset 500ms ease' }}
        />
        {/* Score text */}
        <text
          x="65"
          y="65"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="28"
          fontWeight="700"
          fill="var(--navy)"
          fontFamily="'DM Serif Display', serif"
        >
          {clamped}
        </text>
      </svg>
      <div
        style={{
          fontSize: '11px',
          color: 'var(--muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginTop: '8px',
        }}
      >
        CSS Score
      </div>
    </div>
  );
}