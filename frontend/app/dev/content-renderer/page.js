'use client';

import { useState } from 'react';
import ContentRenderer from '@/components/ContentRenderer';
import {
  mockTextContent,
  mockVideoContent,
  mockAudioContent,
  mockQuizContent,
} from '@/__mocks__/contentMocks';

/**
 * Dev page for ContentRenderer testing
 * Allows switching between modes and adjusting confidence level
 */
export default function ContentRendererDevPage() {
  const [mode, setMode] = useState('text');
  const [confidence, setConfidence] = useState(1.0);

  const modeContents = {
    text: mockTextContent,
    video: mockVideoContent,
    audio: mockAudioContent,
    quiz: mockQuizContent,
  };

  const currentContent = modeContents[mode] || {};

  const modes = [
    { key: 'text', label: 'Text', icon: '📖' },
    { key: 'video', label: 'Video', icon: '📹' },
    { key: 'audio', label: 'Audio', icon: '🎧' },
    { key: 'quiz', label: 'Quiz', icon: '✓' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', paddingTop: '56px' }}>
      {/* Control Panel */}
      <aside
        style={{
          width: '280px',
          backgroundColor: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          padding: '24px',
          position: 'fixed',
          left: 0,
          top: '56px',
          height: 'calc(100vh - 56px)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--navy)', marginBottom: '12px' }}>
            Content Mode
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {modes.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => {
                  console.log('Mode switched to:', m.key);
                  setMode(m.key);
                }}
                style={{
                  padding: '10px 12px',
                  border: mode === m.key ? '2px solid var(--teal)' : '1px solid var(--border)',
                  backgroundColor: mode === m.key ? 'var(--teal-soft)' : 'var(--surface)',
                  color: mode === m.key ? 'var(--navy)' : 'var(--text)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                  textAlign: 'left',
                  transition: 'all 200ms ease',
                  pointerEvents: 'auto',
                }}
                onMouseEnter={(e) => {
                  if (mode !== m.key) {
                    e.currentTarget.style.borderColor = 'var(--teal)';
                    e.currentTarget.style.backgroundColor = 'var(--teal-soft)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (mode !== m.key) {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.backgroundColor = 'var(--surface)';
                  }
                }}
              >
                <span>{m.icon}</span> {m.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, color: 'var(--navy)', marginBottom: '12px' }}>
            Confidence Level
          </label>

          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            style={{
              width: '100%',
              cursor: 'pointer',
              accentColor: 'var(--teal)',
            }}
          />

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '8px',
              fontSize: '12px',
            }}
          >
            <span style={{ color: 'var(--muted)' }}>0.0</span>
            <span style={{ fontWeight: 600, color: confidence < 0.6 ? '#DC3545' : 'var(--teal)' }}>
              {confidence.toFixed(2)}
            </span>
            <span style={{ color: 'var(--muted)' }}>1.0</span>
          </div>

          {confidence < 0.6 && (
            <div
              style={{
                marginTop: '12px',
                padding: '8px',
                backgroundColor: '#F8D7DA',
                border: '1px solid #F5C6CB',
                borderRadius: '4px',
                fontSize: '11px',
                color: '#721C24',
              }}
            >
              ⚠️ Below confidence gate (0.60) — shows thinking skeleton
            </div>
          )}
        </div>

        {/* Info */}
        <div
          style={{
            marginTop: 'auto',
            paddingTop: '24px',
            borderTop: '1px solid var(--border)',
            fontSize: '12px',
            color: 'var(--muted)',
            lineHeight: 1.5,
          }}
        >
          <p style={{ marginTop: 0 }}>
            <strong>Modes:</strong>
          </p>
          <ul style={{ marginTop: '6px', marginBottom: 0, paddingLeft: '16px' }}>
            <li>Text: Chunked progressive cards</li>
            <li>Video: Native player + transcript</li>
            <li>Audio: Player + chunked transcript</li>
            <li>Quiz: Q&A with scoring</li>
          </ul>
        </div>
      </aside>

      {/* Content Area */}
      <main
        style={{
          flex: 1,
          marginLeft: '280px',
        }}
      >
        <ContentRenderer
          mode={mode}
          content={currentContent}
          confidence={confidence}
          onChunkComplete={() => console.log('[ContentRenderer] Chunk complete')}
          onQuizComplete={(result) => console.log('[ContentRenderer] Quiz complete:', result)}
        />
      </main>
    </div>
  );
}
