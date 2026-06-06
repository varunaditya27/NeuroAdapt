'use client';

/**
 * ModalityBar Component
 * Plain CSS-width horizontal bar for a single modality.
 * No D3 or new chart library.
 */
export default function ModalityBar({ modality, count, share, totalEvents }) {
  const sharePercent = Math.round((share ?? 0) * 100);

  const modalityLabels = {
    standard: 'Standard',
    simplified_text: 'Simplified Text',
    video: 'Video',
    audio: 'Audio',
    quiz: 'Quiz',
    sensory_break: 'Sensory Break',
  };

  const label = modalityLabels[modality] || modality;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '6px 0',
      }}
    >
      {/* Modality label */}
      <div
        style={{
          minWidth: '130px',
          fontSize: '13px',
          fontWeight: 500,
          color: 'var(--text)',
        }}
      >
        {label}
      </div>

      {/* Bar track */}
      <div
        style={{
          flex: 1,
          height: '20px',
          backgroundColor: 'var(--bg)',
          borderRadius: '4px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Bar fill */}
        <div
          style={{
            height: '100%',
            width: `${sharePercent}%`,
            backgroundColor: 'var(--teal)',
            borderRadius: '4px',
            transition: 'width 300ms ease',
            minWidth: sharePercent > 0 ? '4px' : '0',
          }}
        />
      </div>

      {/* Share percentage and count */}
      <div
        style={{
          minWidth: '100px',
          textAlign: 'right',
          fontSize: '12px',
          color: 'var(--muted)',
        }}
      >
        <span style={{ fontWeight: 600, color: 'var(--navy)' }}>{sharePercent}%</span>
        <span style={{ marginLeft: '4px' }}>({count})</span>
      </div>
    </div>
  );
}