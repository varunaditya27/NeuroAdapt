'use client';

import { useState } from 'react';
import SensoryBreak from './SensoryBreak';

/**
 * EnergyBar Component
 * A soft battery/charge indicator that triggers sensory breaks
 * Appears as fixed bottom-right control during lessons
 */
export default function EnergyBar({
  onBreakRequest = () => {},
  onBreakEnd = () => {},
  breakDuration = 60,
  ttsText = '',
}) {
  const [showBreak, setShowBreak] = useState(false);
  const [isActive, setIsActive] = useState(false);

  const handleBreakRequest = () => {
    setIsActive(true);
    setShowBreak(true);
    onBreakRequest?.();
  };

  const handleBreakEnd = () => {
    setShowBreak(false);
    setIsActive(false);
    onBreakEnd?.();
  };

  return (
    <>
      {/* Energy Bar Button */}
      <button
        onClick={handleBreakRequest}
        disabled={isActive}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          height: '48px',
          paddingLeft: '16px',
          paddingRight: '16px',
          minWidth: '140px',
          backgroundColor: 'var(--surface)',
          border: '2px solid var(--teal)',
          borderRadius: '24px',
          cursor: isActive ? 'not-allowed' : 'pointer',
          fontSize: '14px',
          fontWeight: 500,
          color: isActive ? 'var(--muted)' : 'var(--teal)',
          transition: 'all 300ms ease',
          opacity: isActive ? 0.6 : 1,
        }}
        aria-label="Take a sensory break"
        onMouseEnter={(e) => {
          if (!isActive) {
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
            e.currentTarget.style.backgroundColor = 'var(--teal-soft)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isActive) {
            e.currentTarget.style.boxShadow = 'none';
            e.currentTarget.style.backgroundColor = 'var(--surface)';
          }
        }}
        onFocus={(e) => {
          e.currentTarget.style.outline = '2px solid var(--teal)';
          e.currentTarget.style.outlineOffset = '2px';
        }}
        onBlur={(e) => {
          e.currentTarget.style.outline = 'none';
          e.currentTarget.style.outlineOffset = '0';
        }}
      >
        {/* Pause/Leaf Icon SVG */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Leaf icon */}
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <span>Take a Break</span>
      </button>

      {/* Sensory Break Modal */}
      {showBreak && (
        <SensoryBreak
          duration={breakDuration}
          onBreakStart={() => {
            // Future: TTS integration
          }}
          onBreakEnd={handleBreakEnd}
        />
      )}
    </>
  );
}
