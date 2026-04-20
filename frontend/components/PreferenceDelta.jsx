'use client';

import { useEffect, useRef } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { Portal } from './Portal';
import { FORMAT_METADATA } from '@/utils/constants';

/**
 * PreferenceDelta Component
 * Modal where student picks preferred content format (text, video, audio, quiz)
 */
export default function PreferenceDelta({
  open = false,
  onSelect = () => {},
  onClose = () => {},
}) {
  const containerRef = useRef(null);

  // Trap focus inside modal
  useFocusTrap(containerRef, open);

  // Handle Escape key to close
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  const formats = [
    { key: 'text', label: 'Read it', subtext: 'Bite-sized text, at your pace', icon: '📖' },
    { key: 'video', label: 'Watch it', subtext: 'Visual walkthrough', icon: '📹' },
    { key: 'audio', label: 'Listen to it', subtext: 'Narrated explanation', icon: '🎧' },
    { key: 'quiz', label: 'Test yourself', subtext: 'Questions and answers', icon: '✓' },
  ];

  if (!open) return null;

  return (
    <Portal>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pref-delta-title"
        ref={containerRef}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 9998,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          backdropFilter: 'blur(4px)',
          animation: 'fadeIn 200ms ease',
        }}
        onClick={(e) => {
          // Close only if clicking on the backdrop, not the modal
          if (e.target === e.currentTarget) {
            onClose?.();
          }
        }}
      >
        <div
          style={{
            backgroundColor: 'var(--surface)',
            borderRadius: '16px',
            padding: '40px',
            maxWidth: '700px',
            width: '90%',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
            animation: 'slideUp 300ms ease',
          }}
        >
          {/* Title */}
          <h2
            id="pref-delta-title"
            style={{
              fontSize: '24px',
              fontWeight: 500,
              color: 'var(--navy)',
              textAlign: 'center',
              marginTop: 0,
              marginBottom: '12px',
            }}
          >
            How would you like to learn?
          </h2>

          <p
            style={{
              fontSize: '14px',
              color: 'var(--muted)',
              textAlign: 'center',
              marginBottom: '32px',
              marginTop: 0,
            }}
          >
            Choose a content format that works best for you
          </p>

          {/* Format Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '16px',
              marginBottom: '24px',
            }}
          >
            {formats.map((format) => (
              <button
                key={format.key}
                onClick={() => {
                  onSelect?.(format.key);
                  onClose?.();
                }}
                style={{
                  padding: '20px',
                  border: '2px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  backgroundColor: 'var(--surface)',
                  cursor: 'pointer',
                  transition: 'all 200ms ease',
                  textAlign: 'left',
                  minHeight: '140px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  justifyContent: 'flex-start',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--teal)';
                  e.currentTarget.style.backgroundColor = 'var(--teal-soft)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.backgroundColor = 'var(--surface)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
                onFocus={(e) => {
                  e.currentTarget.style.outlineOffset = '2px';
                  e.currentTarget.style.outline = '2px solid var(--teal)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.outline = 'none';
                  e.currentTarget.style.outlineOffset = '0';
                }}
              >
                {/* Icon */}
                <div style={{ fontSize: '28px' }}>{format.icon}</div>

                {/* Label */}
                <div
                  style={{
                    fontSize: '16px',
                    fontWeight: 500,
                    color: 'var(--navy)',
                  }}
                >
                  {format.label}
                </div>

                {/* Subtext */}
                <div
                  style={{
                    fontSize: '13px',
                    color: 'var(--muted)',
                    lineHeight: 1.4,
                  }}
                >
                  {format.subtext}
                </div>
              </button>
            ))}
          </div>

          {/* Close hint */}
          <div
            style={{
              fontSize: '12px',
              color: 'var(--muted)',
              textAlign: 'center',
            }}
          >
            Press <kbd style={{ padding: '2px 4px', backgroundColor: 'var(--border)', borderRadius: '4px' }}>Esc</kbd> to close
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </Portal>
  );
}
