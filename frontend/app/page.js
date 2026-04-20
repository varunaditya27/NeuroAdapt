'use client';

import { useEffect, useState } from 'react';
import { init, flush, destroy } from '@/components/Observer';

export default function Home() {
  const [stateVector, setStateVector] = useState(null);
  const [lastPostTime, setLastPostTime] = useState(null);
  const [observerActive, setObserverActive] = useState(false);
  const [activeModuleId, setActiveModuleId] = useState(1);

  useEffect(() => {
    // Initialize Observer on mount
    init();
    setObserverActive(true);

    // Set up the global callback for Observer flush events
    window.__onObserverFlush = (data) => {
      setStateVector({
        dwell: parseFloat(data.dwell),
        jitter: parseFloat(data.jitter),
        focus: parseFloat(data.focus),
        stall: parseFloat(data.stall),
        pref_delta: parseFloat(data.pref_delta),
      });
      setLastPostTime(data.timestamp);
    };

    // Cleanup on unmount
    return () => {
      destroy();
      setObserverActive(false);
      delete window.__onObserverFlush;
    };
  }, []);

  const handleFlushNow = async () => {
    await flush();
  };

  const modules = [
    { id: 1, name: 'Intro to Quantum Computing' },
    { id: 2, name: 'Superposition & Entanglement' },
    { id: 3, name: 'Quantum Gates' },
    { id: 4, name: 'Quantum Algorithms' },
    { id: 5, name: 'Real Applications' },
  ];

  const progress = 33; // TODO: Wire to real data

  const SignalBar = ({ label, value }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
      <div style={{ minWidth: '80px', fontSize: '13px', color: 'var(--muted)' }}>
        {label}
      </div>
      <div
        style={{
          flex: 1,
          height: '8px',
          backgroundColor: 'var(--border)',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${value * 100}%`,
            backgroundColor: 'var(--teal)',
            borderRadius: '4px',
            transition: 'width 200ms ease',
          }}
        />
      </div>
      <div style={{ minWidth: '45px', textAlign: 'right', fontSize: '13px', fontWeight: 500 }}>
        {value.toFixed(2)}
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh', paddingTop: '56px' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: '260px',
          position: 'fixed',
          left: 0,
          top: '56px',
          height: 'calc(100vh - 56px)',
          backgroundColor: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          padding: '24px 0',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Modules Section */}
        <div style={{ flex: 1, paddingLeft: '20px', paddingRight: '16px' }}>
          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.08em',
              color: 'var(--muted)',
              marginBottom: '16px',
              textTransform: 'uppercase',
            }}
          >
            Lesson Modules
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {modules.map((mod) => (
              <button
                key={mod.id}
                type="button"
                onClick={() => {
                  console.log('Module switched to:', mod.name);
                  setActiveModuleId(mod.id);
                }}
                style={{
                  padding: '10px 12px',
                  borderLeft: activeModuleId === mod.id ? '3px solid var(--teal)' : '3px solid transparent',
                  paddingLeft: activeModuleId === mod.id ? '9px' : '12px',
                  color: activeModuleId === mod.id ? 'var(--navy)' : 'var(--muted)',
                  fontSize: '13px',
                  fontWeight: activeModuleId === mod.id ? 500 : 400,
                  cursor: 'pointer',
                  opacity: 1,
                  transition: 'all 200ms ease',
                  backgroundColor: 'transparent',
                  border: 'none',
                  textAlign: 'left',
                  pointerEvents: 'auto',
                }}
                onMouseEnter={(e) => {
                  if (activeModuleId !== mod.id) {
                    e.currentTarget.style.color = 'var(--navy)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (activeModuleId !== mod.id) {
                    e.currentTarget.style.color = 'var(--muted)';
                  }
                }}
              >
                {mod.name}
              </button>
            ))}
          </div>
        </div>

        {/* Observer Status */}
        <div
          style={{
            paddingLeft: '20px',
            paddingRight: '16px',
            borderTop: '1px solid var(--border)',
            paddingTop: '16px',
            marginTop: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: observerActive ? '#10b981' : '#d1d5db',
                animation: observerActive ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
              }}
            />
            <div style={{ fontSize: '12px', color: 'var(--text)', fontWeight: 500 }}>
              {observerActive ? 'Active' : 'Idle'}
            </div>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px' }}>
            Observer Status
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main
        style={{
          marginLeft: '260px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Progress Bar */}
        <div
          style={{
            height: '4px',
            backgroundColor: 'var(--border)',
            position: 'sticky',
            top: '56px',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              backgroundColor: 'var(--teal)',
              transition: 'width 300ms ease',
            }}
          />
        </div>

        {/* Slide Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '48px 0' }}>
          <div
            style={{
              maxWidth: '680px',
              margin: '0 auto',
              paddingLeft: '48px',
              paddingRight: '48px',
            }}
            data-word-count="240"
          >
            <h1
              style={{
                fontFamily: "'DM Serif Display', serif",
                fontSize: '36px',
                fontWeight: 400,
                color: 'var(--navy)',
                marginBottom: '32px',
              }}
            >
              Introduction to Quantum Computing
            </h1>

            <p style={{ fontSize: '17px', lineHeight: '1.75', color: 'var(--text)', marginBottom: '24px' }}>
              Quantum computing represents a paradigm shift in computational power, leveraging the principles of quantum mechanics to process information in fundamentally new ways. Unlike classical computers that use bits as their basic unit of information, quantum computers utilise quantum bits or qubits, which can exist in a superposition of both 0 and 1 simultaneously. This property allows quantum computers to explore multiple solutions in parallel, potentially solving certain problems exponentially faster than their classical counterparts.
            </p>

            <p style={{ fontSize: '17px', lineHeight: '1.75', color: 'var(--text)', marginBottom: '24px' }}>
              The power of quantum computing stems from several key quantum phenomena. Superposition allows qubits to be in multiple states at once, exponentially increasing the computational space that can be explored. Entanglement links qubits together such that the state of one qubit instantaneously influences the others, enabling complex correlations that classical systems cannot achieve. Finally, interference allows quantum algorithms to amplify correct answers whilst cancelling out incorrect ones, guiding the computation towards the desired solution through carefully designed probability amplitudes.
            </p>

            <p style={{ fontSize: '17px', lineHeight: '1.75', color: 'var(--text)', marginBottom: '48px' }}>
              Current quantum computers face significant challenges, including decoherence where environmental noise causes qubits to lose their quantum properties, and error rates that remain too high for many practical applications. However, the field is advancing rapidly with improvements in qubit stability, error correction codes, and algorithm development. Major companies and research institutions are investing heavily in quantum technology, and we are entering an era where hybrid classical-quantum systems may begin solving real-world problems in cryptography, optimisation, drug discovery, and artificial intelligence.
            </p>

            {/* Navigation Buttons */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '48px' }}>
              <button
                type="button"
                onClick={() => console.log('Previous clicked')}
                style={{
                  padding: '10px 20px',
                  border: '1px solid var(--navy)',
                  backgroundColor: 'transparent',
                  color: 'var(--navy)',
                  borderRadius: 'var(--radius)',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 200ms ease',
                  pointerEvents: 'auto',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(27, 42, 74, 0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                ← Previous
              </button>
              <button
                type="button"
                onClick={() => console.log('Next clicked')}
                style={{
                  padding: '10px 20px',
                  border: 'none',
                  backgroundColor: 'var(--teal)',
                  color: 'white',
                  borderRadius: 'var(--radius)',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 200ms ease',
                  pointerEvents: 'auto',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = '0.9';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = '1';
                }}
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Debug Panel */}
      <div
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          backgroundColor: 'var(--navy)',
          color: 'white',
          borderRadius: 'var(--radius)',
          padding: '14px 18px',
          fontSize: '12px',
          minWidth: '220px',
          fontFamily: 'Courier New, monospace',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ color: 'var(--teal)', fontWeight: 600, marginBottom: '12px' }}>
          Observer Debug
        </div>

        {stateVector ? (
          <>
            <SignalBar label="Dwell" value={stateVector.dwell} />
            <SignalBar label="Jitter" value={stateVector.jitter} />
            <SignalBar label="Focus" value={stateVector.focus} />
            <SignalBar label="Stall" value={stateVector.stall} />
            <SignalBar label="Pref Δ" value={stateVector.pref_delta} />
            <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '12px', marginBottom: '12px' }}>
              last POST: {lastPostTime}
            </div>
          </>
        ) : (
          <div style={{ color: '#9ca3af', marginBottom: '12px' }}>
            Waiting for first flush...
          </div>
        )}

        <button
          onClick={handleFlushNow}
          style={{
            width: '100%',
            backgroundColor: 'var(--teal)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 0',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 200ms ease',
            marginTop: '12px',
          }}
          onMouseEnter={(e) => {
            e.target.style.opacity = '0.9';
          }}
          onMouseLeave={(e) => {
            e.target.style.opacity = '1';
          }}
        >
          Flush Now
        </button>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}
