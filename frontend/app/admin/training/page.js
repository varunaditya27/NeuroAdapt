'use client';

import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * Admin page for training metrics visualization
 * Shows preference delta and epsilon (exploration rate) over episodes
 * Accessible only in development mode
 */
export default function AdminTrainingPage() {
  const [data, setData] = useState([]);

  // Generate mock metrics
  const generateMockMetrics = () => {
    return Array.from({ length: 50 }, (_, i) => ({
      episode: i + 1,
      pref_delta: Math.max(0, 0.8 - i * 0.015 + (Math.random() - 0.5) * 0.05),
      epsilon: Math.max(0.05, 1.0 - (i + 1) / 50),
    }));
  };

  // Initialize data on mount
  useEffect(() => {
    setData(generateMockMetrics());
  }, []);

  // Simulate auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      // In production, this would fetch real data from API
      setData(generateMockMetrics());
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        padding: '40px 20px',
        paddingTop: '80px',
        minHeight: '100vh',
        backgroundColor: 'var(--bg)',
      }}
    >
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 500, color: 'var(--navy)', marginBottom: '8px' }}>
          Training Metrics
        </h1>

        <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '32px' }}>
          Preference Delta and Exploration Rate (ε) over episodes
        </p>

        {/* Chart Container */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '24px',
            marginBottom: '32px',
          }}
        >
          {data.length === 0 ? (
            <div
              style={{
                height: '400px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--muted)',
              }}
            >
              Loading metrics...
            </div>
          ) : (
            <ResponsiveContainer
              width="100%"
              height={400}
              aria-label="Training metrics — Preference Delta and Epsilon over episodes"
            >
              <LineChart
                data={data}
                margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="episode"
                  label={{ value: 'Episode', position: 'right', offset: 10 }}
                  stroke="var(--muted)"
                />
                <YAxis
                  yAxisId="left"
                  label={{ value: 'Preference Delta', angle: -90, position: 'insideLeft' }}
                  domain={[0, 1]}
                  stroke="var(--muted)"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  label={{ value: 'Epsilon (ε)', angle: 90, position: 'insideRight' }}
                  domain={[0, 1]}
                  stroke="var(--muted)"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                  }}
                  labelStyle={{ color: 'var(--text)' }}
                />
                <Legend wrapperStyle={{ color: 'var(--text)' }} />

                {/* Preference Delta Line */}
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="pref_delta"
                  stroke="var(--teal)"
                  dot={false}
                  name="Preference Delta"
                  strokeWidth={2}
                  isAnimationActive={false}
                />

                {/* Epsilon Line */}
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="epsilon"
                  stroke="var(--danger)"
                  dot={false}
                  name="Exploration Rate (ε)"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Info Panel */}
        <div
          style={{
            padding: '20px',
            backgroundColor: 'var(--teal-soft)',
            borderRadius: 'var(--radius)',
            border: '1px solid var(--teal)',
          }}
        >
          <p style={{ marginTop: 0, fontSize: '13px', color: 'var(--navy)', lineHeight: 1.6 }}>
            <strong>Metrics:</strong>
          </p>
          <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px', fontSize: '13px' }}>
            <li>
              <strong>Preference Delta (teal):</strong> Indicates student&apos;s preferred content
              format (0 = text preference, 1 = quiz preference)
            </li>
            <li>
              <strong>Exploration Rate (ε, red dashed):</strong> Probability of random action in
              reinforcement learning. Decreases over episodes to exploit learned policy.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
