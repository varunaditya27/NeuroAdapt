'use client';

import ModalityBar from './ModalityBar';

/**
 * ModalitiesPanel Component
 * Displays learner modality preference breakdown with horizontal bar charts.
 */
export default function ModalitiesPanel({ data }) {
  if (!data) {
    return (
      <PanelWrapper title="Learning Modalities">
        <div style={{ color: 'var(--muted)', fontSize: '14px', fontStyle: 'italic', textAlign: 'center', padding: '24px' }}>
          No modality data available yet.
        </div>
      </PanelWrapper>
    );
  }

  const { modalities, total_events, no_data } = data;

  if (no_data || !modalities) {
    return (
      <PanelWrapper title="Learning Modalities">
        <div style={{ color: 'var(--muted)', fontSize: '14px', fontStyle: 'italic', textAlign: 'center', padding: '24px' }}>
          No modality preference data yet. Preferences are recorded as you interact with different content formats.
        </div>
      </PanelWrapper>
    );
  }

  return (
    <PanelWrapper title="Learning Modalities">
      <div
        style={{
          fontSize: '12px',
          color: 'var(--muted)',
          marginBottom: '12px',
        }}
      >
        Based on {total_events} preference event{total_events !== 1 ? 's' : ''} (last 30 days)
      </div>

      {Object.entries(modalities).map(([modality, info]) => (
        <ModalityBar
          key={modality}
          modality={modality}
          count={info.count}
          share={info.share}
          totalEvents={total_events}
        />
      ))}
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