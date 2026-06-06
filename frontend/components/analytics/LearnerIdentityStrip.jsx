'use client';

/**
 * LearnerIdentityStrip Component
 * A single horizontal bar displaying learner name and key stats.
 * Read-only — no edit controls, no links, no settings-like elements.
 */
export default function LearnerIdentityStrip({
  name = 'Learner',
  memberSince = '—',
  totalSessions = 0,
  currentStreak = 0,
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '32px',
        padding: '20px 24px',
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
      }}
    >
      {/* Name — displayed prominently */}
      <div
        style={{
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--navy)',
          fontFamily: "'DM Serif Display', serif",
          minWidth: '160px',
        }}
      >
        {name}
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        <StatItem label="Member Since" value={memberSince} />
        <StatItem label="Total Sessions" value={String(totalSessions)} />
        <StatItem label="Current Streak" value={`${currentStreak} days`} />
      </div>
    </div>
  );
}

function StatItem({ label, value }) {
  return (
    <div style={{ textAlign: 'center', minWidth: '80px' }}>
      <div
        style={{
          fontSize: '16px',
          fontWeight: 600,
          color: 'var(--teal)',
          marginBottom: '2px',
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: '11px',
          color: 'var(--muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        {label}
      </div>
    </div>
  );
}