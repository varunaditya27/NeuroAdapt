'use client';

import ScoreGauge from './ScoreGauge';
import TrendRow from './TrendRow';

/**
 * CognitiveStabilityPanel Component
 * Displays CSS score and daily/weekly/monthly trends.
 */
export default function CognitiveStabilityPanel({ data }) {
  if (!data) {
    return (
      <PanelWrapper title="Cognitive Stability">
        <div style={{ color: 'var(--muted)', fontSize: '14px', fontStyle: 'italic', textAlign: 'center', padding: '24px' }}>
          No stability data available yet.
        </div>
      </PanelWrapper>
    );
  }

  return (
    <PanelWrapper title="Cognitive Stability">
      <ScoreGauge score={data.current_score} />
      <TrendRow
        daily={data.daily}
        weekly={data.weekly}
        monthly={data.monthly}
      />
      <ScoreExplanationText />
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

function ScoreExplanationText() {
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
      Your Cognitive Stability Score reflects your reading engagement, attention
      persistence, and interaction consistency during learning sessions.
    </div>
  );
}