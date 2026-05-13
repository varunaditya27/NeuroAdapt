'use client';

import { useEffect, useRef, useState } from 'react';
import { splitIntoChunks } from '@/utils/splitIntoChunks';

/**
 * AudioRenderer Component
 * Audio player with always-visible transcript (chunked for independent pacing)
 */
export default function AudioRenderer({
  content = {},
}) {
  const [playbackRate, setPlaybackRate] = useState(1);
  const audioRef = useRef(null);

  const src = content.audio_url || content.src || '';
  const transcriptValue =
    content.transcript ||
    content.simplified_text ||
    content.text ||
    content.narration?.script ||
    '';
  const transcript = Array.isArray(transcriptValue)
    ? transcriptValue.join(' ')
    : String(transcriptValue || '');
  const title = content.title || '';
  const audioType = src.endsWith('.wav')
    ? 'audio/wav'
    : src.endsWith('.mp3')
      ? 'audio/mpeg'
      : undefined;

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

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
        paddingTop: '16px',
        padding: '20px',
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
          ref={audioRef}
          controls
          onLoadedMetadata={() => {
            if (audioRef.current) {
              audioRef.current.playbackRate = playbackRate;
            }
          }}
          style={{
            width: '100%',
            marginBottom: '12px',
          }}
        >
          <source src={src} type={audioType} />
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
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '16px 18px',
          }}
        >
          <h2
            style={{
              fontSize: '18px',
              fontWeight: 500,
              color: 'var(--navy)',
              marginBottom: '12px',
            }}
          >
            Transcript
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {transcriptChunks.map((chunk, idx) => (
              <p
                key={`${idx}-${chunk.slice(0, 12)}`}
                style={{
                  margin: 0,
                  fontSize: '15px',
                  lineHeight: 1.7,
                  color: 'var(--text)',
                }}
              >
                {chunk}
              </p>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ color: 'var(--muted)' }}>No transcript available</div>
      )}
    </div>
  );
}
