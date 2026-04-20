'use client';

import { useState, useEffect } from 'react';
import TextRenderer from './TextRenderer';
import VideoRenderer from './VideoRenderer';
import AudioRenderer from './AudioRenderer';
import QuizRenderer from './QuizRenderer';

/**
 * ContentRenderer Component
 * Routes between different content delivery modes with smooth transitions
 * Includes confidence gate to show thinking skeleton when confidence is low
 */
export default function ContentRenderer({
  mode = 'text',
  content = {},
  confidence = 1.0,
  onBreakTrigger,
  onQuizComplete = () => {},
  onChunkComplete = () => {},
}) {
  const [fadeOut, setFadeOut] = useState(false);
  const [displayMode, setDisplayMode] = useState(mode);

  // Get confidence gate threshold from env or default to 0.60
  const confidenceGate =
    typeof process.env.NEXT_PUBLIC_CONFIDENCE_GATE !== 'undefined'
      ? Number(process.env.NEXT_PUBLIC_CONFIDENCE_GATE)
      : 0.6;

  // Handle mode transitions with fade out/in
  useEffect(() => {
    if (mode !== displayMode) {
      setFadeOut(true);
      const timer = setTimeout(() => {
        setDisplayMode(mode);
        setFadeOut(false);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [mode, displayMode]);

  // Log when confidence is below gate
  useEffect(() => {
    if (confidence < confidenceGate) {
      console.log(
        `[ContentRenderer] confidence below gate: ${confidence} < ${confidenceGate}`
      );
    }
  }, [confidence, confidenceGate]);

  // Trigger break callback when mode is 'break'
  useEffect(() => {
    if (displayMode === 'break' && onBreakTrigger) {
      onBreakTrigger();
    }
  }, [displayMode, onBreakTrigger]);

  // Show thinking skeleton if confidence below gate
  if (confidence < confidenceGate) {
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
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        {/* Thinking skeleton */}
        <div
          style={{
            width: '200px',
            height: '200px',
            borderRadius: '50%',
            backgroundColor: 'var(--border)',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            marginBottom: '24px',
          }}
        />
        <p
          style={{
            fontSize: '16px',
            color: 'var(--muted)',
            textAlign: 'center',
          }}
        >
          Thinking…
        </p>

        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
      </div>
    );
  }

  const contentStyle = {
    opacity: fadeOut ? 0 : 1,
    transition: 'opacity 200ms ease',
  };

  // Route to appropriate renderer based on mode
  switch (displayMode) {
    case 'text':
      return (
        <div style={contentStyle}>
          <TextRenderer content={content} onChunkComplete={onChunkComplete} />
        </div>
      );

    case 'video':
      return (
        <div style={contentStyle}>
          <VideoRenderer content={content} />
        </div>
      );

    case 'audio':
      return (
        <div style={contentStyle}>
          <AudioRenderer content={content} />
        </div>
      );

    case 'quiz':
      return (
        <div style={contentStyle}>
          <QuizRenderer content={content} onQuizComplete={onQuizComplete} />
        </div>
      );

    case 'break':
      // Break mode - parent should handle mounting SensoryBreak
      return null;

    default:
      return (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          Unknown content mode: {displayMode}
        </div>
      );
  }
}
