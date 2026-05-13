'use client';

import { useEffect, useRef } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { Portal } from './Portal';
import { STUDY_MODES } from '@/utils/constants';

/**
 * StudyModeConfirmation Component
 * Modal for confirming/rejecting adaptive study mode recommendations
 * Shown only when model suggests a mode different from the current mode
 */
export default function StudyModeConfirmation({
  open = false,
  currentMode = 'text',
  suggestedMode = null,
  allowNoSuggestion = false,
  onAccept = () => {},
  onReject = () => {},
  onSelectAlternative = () => {},
  onClose = () => {},
}) {
  const containerRef = useRef(null);
  const hasRecommendation = Boolean(suggestedMode && suggestedMode !== currentMode);

  // Trap focus inside modal
  useFocusTrap(containerRef, open);

  // Handle Escape key - treat as rejection
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (hasRecommendation) {
          onReject?.();
        }
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, hasRecommendation, onReject, onClose]);

  // Only show if we have a suggestion that differs from current mode
  if (!open || (!allowNoSuggestion && !hasRecommendation)) {
    return null;
  }

  const currentModeInfo = STUDY_MODES[currentMode];
  const suggestedModeInfo = suggestedMode ? STUDY_MODES[suggestedMode] : null;

  // All available modes for the alternative selection
  const allModes = Object.entries(STUDY_MODES).map(([key, info]) => ({
    key,
    ...info,
  }));

  const handleAccept = () => {
    onAccept?.(suggestedMode);
    onClose?.();
  };

  const handleReject = () => {
    onReject?.(currentMode);
    onClose?.();
  };

  const handleAlternative = (mode) => {
    onSelectAlternative?.(mode);
    onClose?.();
  };

  return (
    <Portal>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="study-mode-title"
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
            if (hasRecommendation) {
              onReject?.();
            }
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
            maxHeight: '90vh',
            overflowY: 'auto',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
            animation: 'slideUp 300ms ease',
          }}
        >
          {/* Header */}
          <div style={{ marginBottom: '32px' }}>
            <h2
              id="study-mode-title"
              style={{
                fontSize: '24px',
                fontWeight: 500,
                color: 'var(--navy)',
                marginTop: 0,
                marginBottom: '12px',
              }}
            >
              {hasRecommendation ? 'Suggested Study Mode' : 'Choose a Study Mode'}
            </h2>

            <p
              style={{
                fontSize: '15px',
                color: 'var(--muted)',
                marginBottom: 0,
                marginTop: 0,
                lineHeight: '1.5',
              }}
            >
              {hasRecommendation ? (
                <>
                  Based on your recent performance and interaction patterns, we recommend
                  switching to <strong>{suggestedModeInfo?.label}</strong>. Would you like to switch?
                </>
              ) : (
                <>Select the mode that works best for you right now.</>
              )}
            </p>
          </div>

          {hasRecommendation && (
            <>
              {/* Current vs Suggested Mode Comparison */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '16px',
                  marginBottom: '32px',
                }}
              >
                {/* Current Mode */}
                <div
                  style={{
                    padding: '16px',
                    border: '2px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    backgroundColor: 'var(--surface)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '8px', fontWeight: 600, textTransform: 'uppercase' }}>
                    Current Mode
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--navy)' }}>
                    {currentModeInfo?.icon} {currentModeInfo?.label}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--muted)', marginTop: '6px' }}>
                    {currentModeInfo?.description}
                  </div>
                </div>

                {/* Suggested Mode */}
                <div
                  style={{
                    padding: '16px',
                    border: '2px solid var(--teal)',
                    borderRadius: 'var(--radius)',
                    backgroundColor: 'rgba(42, 157, 143, 0.05)',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--teal)', marginBottom: '8px', fontWeight: 600, textTransform: 'uppercase' }}>
                    ✨ Recommended
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--teal)' }}>
                    {suggestedModeInfo?.icon} {suggestedModeInfo?.label}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--muted)', marginTop: '6px' }}>
                    {suggestedModeInfo?.description}
                  </div>
                </div>
              </div>

              {/* Primary Action Buttons */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  marginBottom: '24px',
                }}
              >
                {/* Accept Button */}
                <button
                  onClick={handleAccept}
                  style={{
                    padding: '12px 20px',
                    backgroundColor: 'var(--teal)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--radius)',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 200ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--teal-dark)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--teal)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  Switch to Recommended
                </button>

                {/* Reject Button */}
                <button
                  onClick={handleReject}
                  style={{
                    padding: '12px 20px',
                    backgroundColor: 'transparent',
                    color: 'var(--navy)',
                    border: '2px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 200ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--navy)';
                    e.currentTarget.style.backgroundColor = 'var(--surface)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  Keep Current Mode
                </button>
              </div>
            </>
          )}

          {/* Alternative Modes Section */}
          <div style={{ marginTop: hasRecommendation ? '32px' : '0', borderTop: hasRecommendation ? '1px solid var(--border)' : 'none', paddingTop: hasRecommendation ? '24px' : '0' }}>
            <p
              style={{
                fontSize: '13px',
                color: 'var(--muted)',
                marginTop: 0,
                marginBottom: '16px',
                fontWeight: 500,
                textTransform: 'uppercase',
              }}
            >
              {hasRecommendation ? 'Or choose a different mode:' : 'Choose a mode:'}
            </p>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '12px',
              }}
            >
              {allModes.map((mode) => {
                const isCurrentMode = mode.key === currentMode;
                const isSuggestedMode = mode.key === suggestedMode;

                return (
                  <button
                    key={mode.key}
                    onClick={() => handleAlternative(mode.key)}
                    disabled={isCurrentMode}
                    style={{
                      padding: '12px 16px',
                      border: '2px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      backgroundColor: isCurrentMode ? 'var(--bg)' : 'var(--surface)',
                      color: 'var(--navy)',
                      cursor: isCurrentMode ? 'not-allowed' : 'pointer',
                      fontSize: '13px',
                      fontWeight: 600,
                      opacity: isCurrentMode ? 0.6 : 1,
                      transition: 'all 200ms ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isCurrentMode) {
                        e.currentTarget.style.borderColor = isSuggestedMode ? 'var(--teal)' : 'var(--navy)';
                        e.currentTarget.style.backgroundColor = isSuggestedMode ? 'rgba(42, 157, 143, 0.1)' : 'var(--teal-soft)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isCurrentMode) {
                        e.currentTarget.style.borderColor = 'var(--border)';
                        e.currentTarget.style.backgroundColor = 'var(--surface)';
                      }
                    }}
                  >
                    <span style={{ marginRight: '6px' }}>{mode.icon}</span>
                    {mode.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Accessibility Note */}
          <div
            style={{
              marginTop: '20px',
              padding: '12px',
              backgroundColor: 'var(--bg)',
              borderRadius: 'var(--radius)',
              fontSize: '12px',
              color: 'var(--muted)',
            }}
          >
            <strong>Tip:</strong> Press ESC to close, or click the backdrop to exit.
          </div>

          {!hasRecommendation && (
            <div style={{ marginTop: '20px' }}>
              <button
                onClick={onClose}
                style={{
                  width: '100%',
                  padding: '12px 20px',
                  backgroundColor: 'transparent',
                  color: 'var(--navy)',
                  border: '2px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 200ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--navy)';
                  e.currentTarget.style.backgroundColor = 'var(--surface)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </Portal>
  );
}
