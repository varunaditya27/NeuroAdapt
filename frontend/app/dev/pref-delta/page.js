'use client';

import { useState } from 'react';
import PreferenceDelta from '@/components/PreferenceDelta';

/**
 * Dev page for PreferenceDelta component testing
 */
export default function PreferenceDeltaDevPage() {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState(null);
  const [selectionLog, setSelectionLog] = useState([]);

  const handleSelect = (format) => {
    setSelectedFormat(format);
    setSelectionLog((prev) => [
      ...prev,
      { format, time: new Date().toLocaleTimeString() },
    ]);
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  return (
    <div style={{ padding: '40px 20px', paddingTop: '80px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 500, color: 'var(--navy)', marginBottom: '8px' }}>
        PreferenceDelta Component
      </h1>

      <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '24px' }}>
        Test format selection modal
      </p>

      {/* Open Button */}
      <button
        onClick={() => setIsOpen(true)}
        style={{
          minHeight: '44px',
          minWidth: '120px',
          padding: '12px 24px',
          backgroundColor: 'var(--teal)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--radius)',
          fontSize: '16px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'all 200ms ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#237d74';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'var(--teal)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        Open Modal
      </button>

      {/* Current Selection */}
      {selectedFormat && (
        <div
          style={{
            marginTop: '24px',
            padding: '16px',
            backgroundColor: 'var(--teal-soft)',
            borderRadius: 'var(--radius)',
            border: '1px solid var(--teal)',
          }}
        >
          <p style={{ marginTop: 0, fontSize: '14px', fontWeight: 500, color: 'var(--navy)' }}>
            Last selected: <strong>{selectedFormat}</strong>
          </p>
        </div>
      )}

      {/* Selection Log */}
      <div style={{ marginTop: '40px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--navy)' }}>Selection Log</h2>

        {selectionLog.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No selections yet. Open the modal and select a format.</p>
        ) : (
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {selectionLog.map((entry, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '13px',
                }}
              >
                <span style={{ fontWeight: 500, color: 'var(--navy)' }}>
                  {entry.format.charAt(0).toUpperCase() + entry.format.slice(1)}
                </span>
                <span style={{ color: 'var(--muted)' }}>{entry.time}</span>
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
        <p style={{ marginTop: 0, fontWeight: 500 }}>Testing notes:</p>
        <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
          <li>Click &quot;Open Modal&quot; to display the preference selection dialog</li>
          <li>Four large format cards: Text, Video, Audio, Quiz</li>
          <li>Click any card to select and close the modal</li>
          <li>Press Escape to close without selecting</li>
          <li>All selections are logged with timestamps above</li>
        </ul>
      </div>

      {/* Modal Component */}
      <PreferenceDelta open={isOpen} onSelect={handleSelect} onClose={handleClose} />
    </div>
  );
}
