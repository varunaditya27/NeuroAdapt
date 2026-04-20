'use client';

import { useState } from 'react';
import EnergyBar from '@/components/EnergyBar';

/**
 * Dev page for EnergyBar component testing
 */
export default function EnergyBarDevPage() {
  const [breakLog, setBreakLog] = useState([]);
  const [breakDuration, setBreakDuration] = useState(60);

  const handleBreakRequest = () => {
    setBreakLog((prev) => [...prev, { type: 'request', time: new Date().toLocaleTimeString() }]);
  };

  const handleBreakEnd = () => {
    setBreakLog((prev) => [...prev, { type: 'end', time: new Date().toLocaleTimeString() }]);
  };

  return (
    <div style={{ paddingTop: '56px', padding: '40px 20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 500, color: 'var(--navy)', marginBottom: '8px' }}>
        EnergyBar Component
      </h1>

      <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '24px' }}>
        Test the sensory break trigger and flow
      </p>

      {/* Controls */}
      <div style={{ marginBottom: '32px', padding: '16px', backgroundColor: 'var(--teal-soft)', borderRadius: 'var(--radius)' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
          Break Duration (seconds)
        </label>
        <input
          type="number"
          value={breakDuration}
          onChange={(e) => setBreakDuration(Number(e.target.value))}
          min="10"
          max="300"
          style={{
            width: '120px',
            padding: '8px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            fontSize: '14px',
          }}
        />
      </div>

      {/* EnergyBar Component */}
      <EnergyBar
        onBreakRequest={handleBreakRequest}
        onBreakEnd={handleBreakEnd}
        breakDuration={breakDuration}
      />

      {/* Event Log */}
      <div style={{ marginTop: '40px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--navy)' }}>Event Log</h2>

        {breakLog.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>Click &quot;Take a Break&quot; to see events</p>
        ) : (
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {breakLog.map((event, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: event.type === 'request' ? '#D4EDDA' : '#E2E3E5',
                  borderLeft: `4px solid ${event.type === 'request' ? '#28A745' : '#6C757D'}`,
                  borderRadius: '4px',
                  fontSize: '13px',
                }}
              >
                <strong>
                  {event.type === 'request' ? '📍 Break Requested' : '✓ Break Ended'}
                </strong>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '4px' }}>
                  {event.time}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div
        style={{
          marginTop: '40px',
          padding: '16px',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          fontSize: '13px',
          color: 'var(--text)',
          lineHeight: 1.6,
        }}
      >
        <p style={{ marginTop: 0, fontWeight: 500 }}>Usage:</p>
        <ol style={{ marginTop: '8px', marginBottom: 0 }}>
          <li>Click the &quot;Take a Break&quot; button fixed at the bottom-right</li>
          <li>The sensory break overlay appears with a countdown timer</li>
          <li>After 10 seconds, an &quot;I&apos;m ready&quot; button appears</li>
          <li>Click it or wait for auto-dismiss to end the break</li>
          <li>Events are logged above</li>
        </ol>
      </div>
    </div>
  );
}
