'use client';

import OverloadSpikeCount from './OverloadSpikeCount';

/**
 * CognitiveOverloadPanel Component
 * Displays overload spike stats with positive framing (zero-spike sessions are prominent).
 */
export default function CognitiveOverloadPanel({ data }) {
  if (!data) {
    return (
      <PanelWrapper title="Cognitive Overload">
        <div style={{ color: 'var(--muted)', fontSize: '14px', fontStyle: 'italic', textAlign: 'center', padding: '24px' }}>
          No overload data available yet.
        </div>
      </PanelWrapper>
    );
  }

  return (
    <PanelWrapper title="Cognitive Overload">
      <OverloadSpikeCount
        thisWeek={data.spikes_this_week}
        lastWeek={data.spikes_last_week}
        delta={data.weekly_delta}
      />

      {/* Zero-spike stat — most prominent element, always green */}
      <div
        style={{
          marginTop: '16px',
          padding: '16px',
          backgroundColor: 'rgba(42, 157, 143, 0.08)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--teal)',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontSize: '28px',
            fontWeight: 700,
            color: 'var(--teal)',
            lineHeight: 1,
          }}
        >
          {data.sessions_with_zero_spikes}
        </div>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--teal)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginTop: '4px',
            fontWeight: 500,
          }}
        >
          Sessions with no overload moments
        </div>
      </div>

      <OverloadExplanationText />
    </PanelWrapper>
  );
}

function PanelWrapper({ title, children }) {
  return (
    <div
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '24px',
        marginBottom: '16px',
      }}
    >
      <h2
        style={{
          fontSize: '16px',
          fontWeight: 600,
          color: 'var(--navy)',
          marginBottom: '16px',
          fontFamily: "'DM Serif Display', serif",
        }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}

function OverloadExplanationText() {
  return (
    <div
      style={{
        marginTop: '16px',
        padding: '12px 16px',
        backgroundColor: 'var(--bg)',
        borderRadius: 'var(--radius)',
        fontSize: '12px',
        color: 'var(--muted)',
        lineHeight: 1.5,
      }}
    >
      Overload spikes occur when both interaction irregularity and stall duration
      peak simultaneously. Fewer spikes indicate smoother, more sustained engagement.
    </div>
  );
}