'use client';

import { useState } from 'react';

/**
 * VideoRenderer Component
 * Native video player with captions, transcript, and custom controls
 */
export default function VideoRenderer({
  content = {},
}) {
  const [showTranscript, setShowTranscript] = useState(false);

  const src = content.src || '';
  const poster = content.poster || '';
  const transcript = content.transcript || '';
  const title = content.title || '';
  const captionsUrl = content.captionsUrl || '';

  if (!src) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        No video source provided
      </div>
    );
  }

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

      {/* Video Player */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '800px',
          aspectRatio: '16 / 9',
          backgroundColor: '#000',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
          marginBottom: '24px',
        }}
      >
        <video
          style={{
            width: '100%',
            height: '100%',
          }}
          controls
          poster={poster}
        >
          <source src={src} type="video/mp4" />
          {captionsUrl && (
            <track
              kind="subtitles"
              src={captionsUrl}
              srcLang="en"
              label="English"
              default
            />
          )}
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Transcript Section */}
      {transcript && (
        <details
          style={{
            marginTop: '24px',
            padding: '16px',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            cursor: 'pointer',
          }}
          open={false}
          onClick={() => setShowTranscript(!showTranscript)}
        >
          <summary
            style={{
              fontSize: '16px',
              fontWeight: 500,
              color: 'var(--navy)',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            Show transcript
          </summary>
          <div
            style={{
              marginTop: '16px',
              fontSize: '15px',
              lineHeight: '1.7',
              color: 'var(--text)',
            }}
          >
            {transcript}
          </div>
        </details>
      )}
    </div>
  );
}
