'use client';

import { useState, useEffect, useRef } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { Portal } from './Portal';

/**
 * SensoryBreak Component
 * Full-screen overlay for guided sensory breaks with countdown timer
 */
export default function SensoryBreak({
  duration = 60,
  onBreakStart = () => {},
  onBreakEnd = () => {},
}) {
  const [timeLeft, setTimeLeft] = useState(duration);
  const [showButton, setShowButton] = useState(false);
  const containerRef = useRef(null);

  // Call onBreakStart callback when component mounts
  useEffect(() => {
    onBreakStart?.({ text: 'Take a breath. You\'ll be back soon.' });
  }, [onBreakStart]);

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) {
      onBreakEnd?.();
      return;
    }

    const timer = setTimeout(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [timeLeft, onBreakEnd]);

  // Show button after 10 seconds
  useEffect(() => {
    if (duration - timeLeft >= 10) {
      setShowButton(true);
    }
  }, [timeLeft, duration]);

  // Trap focus inside the modal
  useFocusTrap(containerRef, true);

  // Handle Escape key — does NOT dismiss (as per spec)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleDismiss = () => {
    onBreakEnd?.();
  };

  // Calculate SVG circle stroke-dashoffset for progress animation
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (timeLeft / duration) * circumference;

  return (
    <Portal>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Sensory break"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, rgba(242, 240, 235, 0.95) 0%, rgba(232, 245, 243, 0.95) 100%)',
          backdropFilter: 'blur(4px)',
          animation: 'fadeIn 300ms ease',
          '@keyframes fadeIn': {
            from: { opacity: 0 },
            to: { opacity: 1 },
          },
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '32px',
            textAlign: 'center',
            maxWidth: '500px',
            padding: '40px',
          }}
        >
          {/* Circular SVG Timer */}
          <div style={{ position: 'relative', width: '200px', height: '200px' }}>
            <svg
              width="200"
              height="200"
              style={{ transform: 'rotate(-90deg)' }}
            >
              {/* Background circle */}
              <circle
                cx="100"
                cy="100"
                r={radius}
                fill="none"
                stroke="var(--border)"
                strokeWidth="3"
              />
              {/* Progress circle */}
              <circle
                cx="100"
                cy="100"
                r={radius}
                fill="none"
                stroke="var(--teal)"
                strokeWidth="3"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{
                  transition: 'stroke-dashoffset 1s linear',
                }}
              />
            </svg>

            {/* Time display in center */}
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '48px',
                fontWeight: 500,
                color: 'var(--navy)',
              }}
            >
              {timeLeft}
            </div>
          </div>

          {/* Text */}
          <div style={{ maxWidth: '400px' }}>
            <p
              style={{
                fontSize: '18px',
                lineHeight: '1.7',
                color: 'var(--text)',
                fontWeight: 400,
                margin: '0',
              }}
            >
              Take a breath. You&apos;ll be back soon.
            </p>
          </div>

          {/* Button — appears after 10 seconds */}
          {showButton && (
            <button
              onClick={handleDismiss}
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
                animation: 'slideUp 300ms ease',
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
              I&apos;m ready
            </button>
          )}
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
