'use client';

import { useEffect, useState } from 'react';
import { init, destroy } from '@/components/Observer';

/**
 * Dev page for Observer telemetry signals
 * Shows live readout of all 5 signals updating every second
 */
export default function ObserverDevPage() {
  const [signals, setSignals] = useState({
    dwell: 0,
    jitter: 0,
    focus: 0,
    stall: 0,
    pref_delta: 0,
    timestamp: null,
  });

  const [observerActive, setObserverActive] = useState(false);

  useEffect(() => {
    // Initialize Observer
    init();
    setObserverActive(true);

    // Set global callback for flush events
    window.__onObserverFlush = (data) => {
      setSignals({
        dwell: parseFloat(data.dwell),
        jitter: parseFloat(data.jitter),
        focus: parseFloat(data.focus),
        stall: parseFloat(data.stall),
        pref_delta: parseFloat(data.pref_delta),
        timestamp: data.timestamp,
      });
    };

    return () => {
      destroy();
      delete window.__onObserverFlush;
      setObserverActive(false);
    };
  }, []);

  const SignalCard = ({ label, value }) => (
    <div
      style={{
        padding: '16px',
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        marginBottom: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '14px', color: 'var(--muted)' }}>{label}</span>
        <span
          style={{
            fontSize: '20px',
            fontWeight: 600,
            color: 'var(--navy)',
            fontFamily: 'monospace',
          }}
        >
          {value.toFixed(3)}
        </span>
      </div>

      {/* Visual bar */}
      <div
        style={{
          height: '8px',
          backgroundColor: 'var(--border)',
          borderRadius: '4px',
          overflow: 'hidden',
          marginTop: '8px',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${value * 100}%`,
            backgroundColor: 'var(--teal)',
            transition: 'width 200ms ease',
          }}
        />
      </div>
    </div>
  );

  return (
    <div style={{ padding: '56px 20px 40px 20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 500, color: 'var(--navy)', marginBottom: '8px' }}>
        Observer Telemetry
      </h1>

      <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '24px' }}>
        Live readout of 5 telemetry signals updating every 30 seconds
      </p>

      {/* Status */}
      <div
        style={{
          padding: '12px',
          backgroundColor: observerActive ? '#D4EDDA' : '#F8D7DA',
          border: `1px solid ${observerActive ? '#28A745' : '#DC3545'}`,
          borderRadius: 'var(--radius)',
          marginBottom: '24px',
          color: observerActive ? '#155724' : '#721C24',
          fontSize: '13px',
        }}
      >
        {observerActive ? '✓ Observer is running' : '✗ Observer is not running'}
      </div>

      {/* Last update timestamp */}
      {signals.timestamp && (
        <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '16px' }}>
          Last update: {signals.timestamp}
        </div>
      )}

      {/* Signals */}
      <div>
        <SignalCard label="Semantic Dwell Ratio" value={signals.dwell} />
        <SignalCard label="Interaction Jitter" value={signals.jitter} />
        <SignalCard label="Focus Persistence" value={signals.focus} />
        <SignalCard label="Stall Duration" value={signals.stall} />
        <SignalCard label="Preference Delta" value={signals.pref_delta} />
      </div>

      {/* Info */}
      <div
        style={{
          marginTop: '32px',
          padding: '16px',
          backgroundColor: 'var(--teal-soft)',
          borderRadius: 'var(--radius)',
          fontSize: '13px',
          color: 'var(--navy)',
          lineHeight: 1.6,
        }}
      >
        <p style={{ marginTop: 0 }}>
          <strong>All signals are normalized to [0, 1]:</strong>
        </p>
        <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
          <li>
            <strong>Dwell:</strong> Time spent on slide relative to expected reading time
          </li>
          <li>
            <strong>Jitter:</strong> Variability in mouse velocity (std dev / 2.0)
          </li>
          <li>
            <strong>Focus:</strong> Inverse of tab-switch count (1 = fully focused)
          </li>
          <li>
            <strong>Stall:</strong> Time since last interaction / 30s window
          </li>
          <li>
            <strong>Pref Delta:</strong> Preference signal from format selection widget
          </li>
        </ul>
      </div>
    </div>
  );
}
