'use client';

/**
 * TrendRow Component
 * Displays daily/weekly/monthly delta badges with ▲/▼ indicators.
 * Green for positive delta, muted red for negative, grey for insufficient data.
 */
export default function TrendRow({ daily, weekly, monthly }) {
  const trends = [
    { label: 'Daily', data: daily },
    { label: 'Weekly', data: weekly },
    { label: 'Monthly', data: monthly },
  ];

  return (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center', padding: '8px 0' }}>
      {trends.map(({ label, data }) => (
        <TrendBadge key={label} label={label} data={data} />
      ))}
    </div>
  );
}

function TrendBadge({ label, data }) {
  if (!data || !data.sufficient_data || data.mean === null) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '9999px',
          backgroundColor: 'var(--bg)',
          border: '1px solid var(--border)',
          fontSize: '12px',
          color: 'var(--muted)',
        }}
      >
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span>—</span>
        <span style={{ fontSize: '10px' }}>Not enough data</span>
      </div>
    );
  }

  const delta = data.delta;
  const isPositive = delta > 0;
  const isNegative = delta < 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderRadius: '9999px',
        backgroundColor: isPositive ? 'rgba(42, 157, 143, 0.08)' : isNegative ? 'rgba(192, 57, 43, 0.08)' : 'var(--bg)',
        border: `1px solid ${isPositive ? 'var(--teal)' : isNegative ? '#c0392b' : 'var(--border)'}`,
        fontSize: '12px',
        color: isPositive ? 'var(--teal)' : isNegative ? '#c0392b' : 'var(--muted)',
      }}
    >
      <span style={{ fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: '14px', fontWeight: 600 }}>
        {isPositive ? '▲' : isNegative ? '▼' : '—'}
        {delta !== null && delta !== undefined ? ` ${delta > 0 ? '+' : ''}${delta.toFixed(1)}` : ''}
      </span>
      <span style={{ fontSize: '10px', opacity: 0.7 }}>
        mean {data.mean.toFixed(1)}
      </span>
    </div>
  );
}