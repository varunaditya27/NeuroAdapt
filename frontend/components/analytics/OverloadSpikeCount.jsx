'use client';

/**
 * OverloadSpikeCount Component
 * Displays this week vs last week spike counts with delta badge.
 * Positive delta (more spikes) in muted red, negative delta (fewer spikes) in green.
 */
export default function OverloadSpikeCount({ thisWeek = 0, lastWeek = 0, delta = 0 }) {
  const isImprovement = delta < 0;
  const isWorsening = delta > 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '32px',
        padding: '16px',
      }}
    >
      {/* This Week */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            fontSize: '36px',
            fontWeight: 700,
            color: isWorsening ? '#c0392b' : 'var(--teal)',
            lineHeight: 1,
          }}
        >
          {thisWeek}
        </div>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginTop: '4px',
          }}
        >
          This Week
        </div>
      </div>

      {/* Divider */}
      <div
        style={{
          width: '1px',
          height: '40px',
          backgroundColor: 'var(--border)',
        }}
      />

      {/* Last Week */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            fontSize: '36px',
            fontWeight: 700,
            color: 'var(--navy)',
            lineHeight: 1,
          }}
        >
          {lastWeek}
        </div>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginTop: '4px',
          }}
        >
          Last Week
        </div>
      </div>

      {/* Delta Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '6px 12px',
          borderRadius: '9999px',
          backgroundColor: isImprovement ? 'rgba(42, 157, 143, 0.08)' : isWorsening ? 'rgba(192, 57, 43, 0.08)' : 'var(--bg)',
          border: `1px solid ${isImprovement ? 'var(--teal)' : isWorsening ? '#c0392b' : 'var(--border)'}`,
          fontSize: '14px',
          fontWeight: 600,
          color: isImprovement ? 'var(--teal)' : isWorsening ? '#c0392b' : 'var(--muted)',
        }}
      >
        {isImprovement ? '▼' : isWorsening ? '▲' : '—'}
        {delta !== 0 ? ` ${delta > 0 ? '+' : ''}${delta}` : ' 0'}
      </div>
    </div>
  );
}