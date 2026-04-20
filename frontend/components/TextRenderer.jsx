'use client';

import { useState, useEffect } from 'react';

/**
 * TextRenderer Component
 * Displays text content in chunked, progressive cards with forward navigation
 */
export default function TextRenderer({
  content = {},
  onChunkComplete = () => {},
}) {
  const [currentChunkIndex, setCurrentChunkIndex] = useState(0);
  const [fadeIn, setFadeIn] = useState(false);

  const chunks = content.chunks || [];
  const title = content.title || '';
  const isLastChunk = currentChunkIndex === chunks.length - 1;
  const totalChunks = chunks.length;

  // TODO(copilot): Animate fade-in when chunk changes
  useEffect(() => {
    setFadeIn(false);
    const timer = setTimeout(() => setFadeIn(true), 50);
    return () => clearTimeout(timer);
  }, [currentChunkIndex]);

  const handleNext = () => {
    if (isLastChunk) {
      onChunkComplete?.();
    } else {
      setCurrentChunkIndex((prev) => prev + 1);
    }
  };

  if (chunks.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          color: 'var(--muted)',
        }}
      >
        No content to display
      </div>
    );
  }

  const progressPercent = ((currentChunkIndex + 1) / totalChunks) * 100;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        paddingTop: '56px',
        padding: '40px 20px',
        maxWidth: '800px',
        marginLeft: 'auto',
        marginRight: 'auto',
      }}
    >
      {/* Title */}
      {title && (
        <h1
          style={{
            fontSize: '24px',
            fontWeight: 500,
            marginBottom: '32px',
            color: 'var(--navy)',
            textAlign: 'center',
          }}
        >
          {title}
        </h1>
      )}

      {/* Progress Bar */}
      <div
        style={{
          height: '3px',
          backgroundColor: 'var(--border)',
          borderRadius: '2px',
          overflow: 'hidden',
          marginBottom: '40px',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progressPercent}%`,
            backgroundColor: 'var(--teal)',
            transition: 'width 300ms ease',
          }}
        />
      </div>

      {/* Content Card */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          paddingBottom: '40px',
        }}
      >
        <div
          style={{
            fontSize: '18px',
            lineHeight: '1.8',
            color: 'var(--text)',
            maxWidth: '60ch',
            opacity: fadeIn ? 1 : 0,
            transition: 'opacity 200ms ease',
          }}
        >
          {chunks[currentChunkIndex]}
        </div>
      </div>

      {/* Navigation */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          paddingTop: '20px',
        }}
      >
        {isLastChunk ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              color: 'var(--teal)',
              fontSize: '18px',
              fontWeight: 500,
            }}
          >
            <span>✓</span> Done
          </div>
        ) : (
          <button
            onClick={handleNext}
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
            aria-label={`Next chunk, ${currentChunkIndex + 1} of ${totalChunks}`}
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
