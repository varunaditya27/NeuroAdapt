'use client';

import { useEffect, useState } from 'react';
import EnergyBar from '@/components/EnergyBar';

export default function Home() {
  const [activeModuleId, setActiveModuleId] = useState(1);

  const modules = [
    { id: 1, name: 'Intro to Quantum Computing' },
    { id: 2, name: 'Superposition & Entanglement' },
    { id: 3, name: 'Quantum Gates' },
    { id: 4, name: 'Quantum Algorithms' },
    { id: 5, name: 'Real Applications' },
  ];

  const lessonContent = {
    1: {
      title: 'Introduction to Quantum Computing',
      wordCount: 240,
      paragraphs: [
        'Quantum computing represents a paradigm shift in computational power, leveraging the principles of quantum mechanics to process information in fundamentally new ways. Unlike classical computers that use bits as their basic unit of information, quantum computers utilise quantum bits or qubits, which can exist in a superposition of both 0 and 1 simultaneously. This property allows quantum computers to explore multiple solutions in parallel, potentially solving certain problems exponentially faster than their classical counterparts.',
        'The power of quantum computing stems from several key quantum phenomena. Superposition allows qubits to be in multiple states at once, exponentially increasing the computational space that can be explored. Entanglement links qubits together such that the state of one qubit instantaneously influences the others, enabling complex correlations that classical systems cannot achieve. Finally, interference allows quantum algorithms to amplify correct answers whilst cancelling out incorrect ones, guiding the computation towards the desired solution through carefully designed probability amplitudes.',
        'Current quantum computers face significant challenges, including decoherence where environmental noise causes qubits to lose their quantum properties, and error rates that remain too high for many practical applications. However, the field is advancing rapidly with improvements in qubit stability, error correction codes, and algorithm development. Major companies and research institutions are investing heavily in quantum technology, and we are entering an era where hybrid classical-quantum systems may begin solving real-world problems in cryptography, optimisation, drug discovery, and artificial intelligence.',
      ]
    },
    2: {
      title: 'Superposition & Entanglement',
      wordCount: 285,
      paragraphs: [
        'Superposition is one of the most fundamental principles of quantum mechanics. In classical systems, a bit must be either 0 or 1. In contrast, a quantum bit or qubit can exist in a superposition of both states simultaneously. This means that before measurement, a qubit is in a linear combination of 0 and 1 states, described mathematically by coefficients that determine the probability of observing each outcome.',
        'Entanglement is another cornerstone of quantum mechanics that has no classical analogue. When two or more qubits become entangled, their quantum states are correlated in such a way that measuring one qubit instantaneously affects the state of the others, regardless of the distance between them. This phenomenon fascinated Einstein, who famously referred to it as "spooky action at a distance." Entanglement enables quantum computers to perform certain calculations far more efficiently than classical computers.',
        'The combination of superposition and entanglement gives quantum computers their extraordinary computational power. While a classical computer with n bits can represent one of 2^n possible values at any given time, a quantum computer with n qubits can represent all 2^n values simultaneously. This exponential advantage is the key to quantum computing\'s potential for solving previously intractable problems in optimization, cryptography, and simulation.',
      ]
    },
    3: {
      title: 'Quantum Gates',
      wordCount: 268,
      paragraphs: [
        'Quantum gates are the basic building blocks of quantum circuits, analogous to logic gates in classical computing. However, quantum gates operate on qubits and must preserve the quantum mechanical properties of superposition and entanglement. Single-qubit gates like the Pauli gates (X, Y, Z) and the Hadamard gate manipulate individual qubits, while multi-qubit gates like the CNOT gate create entanglement between qubits.',
        'The Hadamard gate is particularly important in quantum computing because it creates superposition by transforming a definite qubit state into an equal superposition of 0 and 1. The Pauli-X gate acts as a quantum analog of the classical NOT gate, flipping the qubit state. The Pauli-Z gate introduces a phase shift, which is crucial for quantum algorithms. These gates, combined with rotation gates parameterized by angles, form a universal set that can implement any quantum computation.',
        'Quantum circuit design involves carefully orchestrating sequences of gates to achieve desired computational outcomes. The CNOT (Controlled-NOT) gate is essential for creating entanglement between qubits. More complex operations can be decomposed into combinations of elementary gates. Understanding how to design efficient quantum circuits is fundamental to developing practical quantum algorithms and harnessing the power of quantum computers.',
      ]
    },
    4: {
      title: 'Quantum Algorithms',
      wordCount: 301,
      paragraphs: [
        'Quantum algorithms are procedures designed to solve specific problems using quantum computers. The most famous quantum algorithm is Shor\'s algorithm, which can factor large numbers exponentially faster than any known classical algorithm. This algorithm has profound implications for cryptography, as the security of many modern encryption schemes relies on the difficulty of factoring large numbers. Other important quantum algorithms include Grover\'s algorithm for searching unsorted databases and the Quantum Fourier Transform, which is the foundation for many quantum algorithms.',
        'Grover\'s algorithm provides a quadratic speedup for searching an unsorted database of N items. While a classical computer would require O(N) operations to search the entire database, Grover\'s algorithm accomplishes this in O(√N) operations. This might not seem as dramatic as Shor\'s exponential speedup, but for large databases, the quadratic improvement can still be significant. The algorithm uses quantum amplitude amplification to increase the probability of measuring the correct answer.',
        'The development of quantum algorithms requires a deep understanding of both quantum mechanics and computer science. Quantum algorithms leverage unique quantum phenomena like superposition, entanglement, and interference to achieve computational advantages. As quantum hardware continues to improve, researchers are discovering new algorithms and optimizing existing ones to solve practical problems in drug discovery, materials science, optimization, and machine learning.',
      ]
    },
    5: {
      title: 'Real Applications',
      wordCount: 256,
      paragraphs: [
        'Quantum computing has tremendous potential for real-world applications across multiple industries. In drug discovery, quantum computers can simulate molecular interactions and properties with unprecedented accuracy, potentially accelerating the development of new pharmaceuticals. Companies like IBM and Pfizer are already exploring quantum computing for drug development. In materials science, quantum computers can help design new materials with specific properties by accurately simulating quantum mechanical processes.',
        'Financial institutions are investigating quantum computing for portfolio optimization and risk analysis. Quantum algorithms can explore a vast space of possible portfolios and find optimal solutions more efficiently than classical methods. Additionally, quantum computers could help with pricing complex financial derivatives and Monte Carlo simulations. Banks like JPMorgan Chase are already researching quantum algorithms for financial applications.',
        'Optimization problems appear across industries, from logistics and supply chain management to manufacturing and energy distribution. Many of these problems are NP-hard, meaning they are computationally intractable for classical computers at scale. Quantum computers, particularly those using quantum annealing or variational algorithms, could provide significant advantages in solving these optimization challenges, leading to substantial cost savings and efficiency improvements across sectors.',
      ]
    }
  };

  const currentLesson = lessonContent[activeModuleId];
  const isFirstLesson = activeModuleId === 1;
  const isLastLesson = activeModuleId === modules.length;

  const handlePrevious = () => {
    if (!isFirstLesson) {
      setActiveModuleId(activeModuleId - 1);
    }
  };

  const handleNext = () => {
    if (!isLastLesson) {
      setActiveModuleId(activeModuleId + 1);
    }
  };

  const progress = Math.round((activeModuleId / modules.length) * 100);

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
            data-word-count={currentLesson.wordCount}
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
              {currentLesson.title}
            </h1>

            {currentLesson.paragraphs.map((paragraph, idx) => (
              <p key={idx} style={{ fontSize: '17px', lineHeight: '1.75', color: 'var(--text)', marginBottom: '24px' }}>
                {paragraph}
              </p>
            ))}

            {/* Navigation Buttons */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '48px' }}>
              {!isFirstLesson && (
                <button
                  type="button"
                  onClick={handlePrevious}
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
              )}
              {!isLastLesson && (
                <button
                  type="button"
                  onClick={handleNext}
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
              )}
            </div>
          </div>
        </div>
      </main>

      {/* EnergyBar Component */}
      <EnergyBar
        onBreakRequest={() => {
          console.log('Break requested');
        }}
        onBreakEnd={() => {
          console.log('Break ended');
        }}
        breakDuration={60}
      />

    </div>
  );
}
