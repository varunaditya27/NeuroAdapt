'use client';

import { useState } from 'react';
import TextRenderer from './TextRenderer';
import { splitIntoChunks } from '@/utils/splitIntoChunks';

/**
 * AudioRenderer Component
 * Audio player with always-visible transcript (chunked for independent pacing)
 */
export default function AudioRenderer({
  content = {},
}) {
  const [playbackRate, setPlaybackRate] = useState(1);

  const src = content.src || '';
  const transcript = content.transcript || '';
  const title = content.title || '';

  if (!src) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        No audio source provided
      </div>
    );
  }

  // Split transcript into chunks for independent reading pace
  const transcriptChunks = transcript ? splitIntoChunks(transcript, 40) : [];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        paddingTop: '56px',
        padding: '40px 20px',
        maxWidth: '900px',
        marginLeft: 'auto',
        marginRight: 'auto',
      }}
    >
      {title && (
        <h1
          style={{
            fontSize: '24px',
            fontWeight: 500,
            marginBottom: '24px',
            color: 'var(--navy)',
          }}
        >
          {title}
        </h1>
      )}

      {/* Audio Player Controls */}
      <div
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '16px',
          marginBottom: '32px',
        }}
      >
        <audio
          controls
          style={{
            width: '100%',
            marginBottom: '12px',
          }}
        >
          <source src={src} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>

        {/* Playback Rate Controls */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            justifyContent: 'center',
            flexWrap: 'wrap',
          }}
        >
          {[0.75, 1, 1.25, 1.5].map((rate) => (
            <button
              key={rate}
              onClick={() => setPlaybackRate(rate)}
              style={{
                minWidth: '60px',
                padding: '8px 12px',
                backgroundColor: playbackRate === rate ? 'var(--teal)' : 'var(--border)',
                color: playbackRate === rate ? 'white' : 'var(--text)',
                border: 'none',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 200ms ease',
              }}
              onMouseEnter={(e) => {
                if (playbackRate !== rate) {
                  e.currentTarget.style.backgroundColor = '#D4D4D4';
                }
              }}
              onMouseLeave={(e) => {
                if (playbackRate !== rate) {
                  e.currentTarget.style.backgroundColor = 'var(--border)';
                }
              }}
            >
              {rate}×
            </button>
          ))}
        </div>
      </div>

      {/* Transcript Section */}
      {transcriptChunks.length > 0 ? (
        <div>
          <h2
            style={{
              fontSize: '18px',
              fontWeight: 500,
              color: 'var(--navy)',
              marginBottom: '16px',
            }}
          >
            Transcript
          </h2>
          <TextRenderer
            content={{
              chunks: transcriptChunks,
            }}
            onChunkComplete={() => {
              // Transcript complete — do nothing, student can continue
            }}
          />
        </div>
      ) : (
        <div style={{ color: 'var(--muted)' }}>No transcript available</div>
      )}
    </div>
  );
}
