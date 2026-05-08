'use client';

import { useEffect, useState } from 'react';
import { getLastStateVector } from '@/components/Observer';

export default function Dashboard() {
  const [stats, setStats] = useState({
    sessionId: 'test-session-001',
    slidesCompleted: '1 / 5',
    avgDwell: '—',
    lastFlush: '—',
  });

  const [stateVector, setStateVector] = useState({
    dwell: 0,
    jitter: 0,
    focus: 0,
    stall: 0,
    pref_delta: 0,
  });

  const [lastSentPrefDelta, setLastSentPrefDelta] = useState({
    value: null,
    timestamp: null,
    choice: null,
  });

  useEffect(() => {
    // Read last state vector immediately on mount
    const lastVector = getLastStateVector();
    setStateVector({
      dwell: lastVector[0],
      jitter: lastVector[1],
      focus: lastVector[2],
      stall: lastVector[3],
      pref_delta: lastVector[4],
    });

    setStats((prev) => ({
      ...prev,
      avgDwell: lastVector[0].toFixed(2),
    }));

    // Read last sent prefDelta from localStorage
    try {
      const stored = localStorage.getItem('lastSentPrefDelta');
      if (stored) {
        setLastSentPrefDelta(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to read lastSentPrefDelta from localStorage:', e);
    }

    // Wire up the global flush callback for future updates
    window.__onObserverFlush = (data) => {
      setStats((prev) => ({
        ...prev,
        avgDwell: parseFloat(data.dwell).toFixed(2),
        lastFlush: data.timestamp,
      }));

      setStateVector({
        dwell: parseFloat(data.dwell),
        jitter: parseFloat(data.jitter),
        focus: parseFloat(data.focus),
        stall: parseFloat(data.stall),
        pref_delta: parseFloat(data.pref_delta),
      });
    };

    // Listen for prefDelta changes from other tabs/storage events
    const handleStorageChange = () => {
      try {
        const stored = localStorage.getItem('lastSentPrefDelta');
        if (stored) {
          setLastSentPrefDelta(JSON.parse(stored));
        }
      } catch (e) {
        console.error('Failed to update lastSentPrefDelta:', e);
      }
    };
    window.addEventListener('storage', handleStorageChange);

    return () => {
      delete window.__onObserverFlush;
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const StatCard = ({ title, value, subtext }) => (
    <div
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '24px',
        transition: 'all 200ms ease',
        cursor: 'default',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '8px', fontWeight: 500 }}>
        {title}
      </div>
      <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--navy)', marginBottom: '4px' }}>
        {value}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{subtext}</div>
    </div>
  );

  const SignalBar = ({ label, value }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
      <div style={{ minWidth: '90px', fontSize: '13px', color: 'var(--text)', fontWeight: 500 }}>
        {label}
      </div>
      <div
        style={{
          flex: 1,
          height: '8px',
          backgroundColor: 'var(--border)',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${value * 100}%`,
            backgroundColor: 'var(--teal)',
            borderRadius: '4px',
            transition: 'width 200ms ease',
          }}
        />
      </div>
      <div style={{ minWidth: '50px', textAlign: 'right', fontSize: '13px', fontWeight: 500 }}>
        {value.toFixed(2)}
      </div>
    </div>
  );

  return (
    <div style={{ paddingTop: '56px', minHeight: '100vh', backgroundColor: 'var(--bg)' }}>
      <div style={{ padding: '40px 48px' }}>
        {/* Page Heading */}
        <div style={{ marginBottom: '48px' }}>
          <h1
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: '32px',
              fontWeight: 400,
              color: 'var(--navy)',
              marginBottom: '8px',
            }}
          >
            Dashboard
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--muted)' }}>
            Session overview & Observer telemetry
          </p>
        </div>

        {/* Stats Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '16px',
            marginBottom: '48px',
          }}
        >
          <StatCard
            title="Active Session"
            value={stats.sessionId}
            subtext="Session ID"
          />
          <StatCard
            title="Slides Completed"
            value={stats.slidesCompleted}
            subtext="Current module"
          />
          <StatCard
            title="Avg Dwell Ratio"
            value={stats.avgDwell}
            subtext="Awaiting data"
          />
          <StatCard
            title="Last Flush"
            value={stats.lastFlush === '—' ? '—' : stats.lastFlush.split(' ')[0]}
            subtext="Awaiting flush"
          />
        </div>

        {/* State Vector Panel */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '24px',
            marginBottom: '48px',
          }}
        >
          <h2
            style={{
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--navy)',
              marginBottom: '24px',
            }}
          >
            Latest State Vector
          </h2>
          <SignalBar label="Dwell Ratio" value={stateVector.dwell} />
          <SignalBar label="Jitter" value={stateVector.jitter} />
          <SignalBar label="Focus" value={stateVector.focus} />
          <SignalBar label="Stall Duration" value={stateVector.stall} />
          <SignalBar label="Preference Δ" value={stateVector.pref_delta} />
        </div>

        {/* Last Sent Preference Delta */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '24px',
            marginTop: '24px',
          }}
        >
          <h2
            style={{
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--navy)',
              marginBottom: '16px',
            }}
          >
            Last Preference Δ Sent to Backend
          </h2>
          {lastSentPrefDelta.value !== null ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                  Value
                </div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--teal)' }}>
                  {lastSentPrefDelta.value === 1 ? '✓ 1' : lastSentPrefDelta.value === 0 ? '✗ 0' : '≈ 0.5'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                  User Choice
                </div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>
                  {lastSentPrefDelta.choice === 'accept'
                    ? '👍 Accepted'
                    : lastSentPrefDelta.choice === 'reject'
                    ? '👎 Rejected'
                    : lastSentPrefDelta.choice === 'alternative'
                    ? '🔄 Alternative'
                    : 'Unknown'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '6px' }}>
                  Sent At
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text)', fontFamily: 'monospace' }}>
                  {new Date(lastSentPrefDelta.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '14px', fontStyle: 'italic' }}>
              Awaiting first study mode choice...
            </div>
          )}
        </div>

        {/* Placeholder Sections */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '24px',
              minHeight: '200px',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <h3
              style={{
                fontSize: '16px',
                fontWeight: 600,
                color: 'var(--navy)',
                marginBottom: '16px',
              }}
            >
              Reward History
            </h3>
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--muted)',
                fontSize: '14px',
                textAlign: 'center',
              }}
            >
              Awaiting Orchestrator integration (Phase 2)
            </div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '24px',
              minHeight: '200px',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <h3
              style={{
                fontSize: '16px',
                fontWeight: 600,
                color: 'var(--navy)',
                marginBottom: '16px',
              }}
            >
              Action Log
            </h3>
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--muted)',
                fontSize: '14px',
                textAlign: 'center',
              }}
            >
              Awaiting Orchestrator integration (Phase 2)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
