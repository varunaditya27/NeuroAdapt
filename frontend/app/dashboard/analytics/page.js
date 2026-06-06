'use client';

import { useEffect, useState } from 'react';
import LearnerIdentityStrip from '@/components/analytics/LearnerIdentityStrip';
import CognitiveStabilityPanel from '@/components/analytics/CognitiveStabilityPanel';
import CognitiveOverloadPanel from '@/components/analytics/CognitiveOverloadPanel';
import ModalitiesPanel from '@/components/analytics/ModalitiesPanel';
import ExportReportButton from '@/components/analytics/ExportReportButton';

/**
 * AnalyticsDashboardPage
 * Main analytics dashboard page at /dashboard/analytics.
 */
export default function AnalyticsDashboardPage() {
  const [summary, setSummary] = useState(null);
  const [stability, setStability] = useState(null);
  const [overload, setOverload] = useState(null);
  const [modalities, setModalities] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, stabilityRes, overloadRes, modalitiesRes] = await Promise.all([
          fetch('/api/analytics/user-summary'),
          fetch('/api/analytics/stability'),
          fetch('/api/analytics/overload'),
          fetch('/api/analytics/modalities'),
        ]);

        if (!summaryRes.ok || !stabilityRes.ok || !overloadRes.ok || !modalitiesRes.ok) {
          throw new Error('Failed to fetch analytics data');
        }

        setSummary(await summaryRes.json());
        setStability(await stabilityRes.json());
        setOverload(await overloadRes.json());
        setModalities(await modalitiesRes.json());
      } catch (err) {
        console.error('[AnalyticsDashboard] Fetch error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  if (loading) {
    return (
      <PageWrapper>
        <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--muted)' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              border: '3px solid var(--border)',
              borderTopColor: 'var(--teal)',
              borderRadius: '50%',
              animation: 'analyticsSpin 0.8s linear infinite',
              margin: '0 auto 16px',
            }}
          />
          <div style={{ fontSize: '14px' }}>Loading analytics…</div>
          <style>{`@keyframes analyticsSpin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </PageWrapper>
    );
  }

  if (error) {
    return (
      <PageWrapper>
        <div
          style={{
            textAlign: 'center',
            padding: '80px 0',
            color: '#c0392b',
            fontSize: '14px',
          }}
        >
          Failed to load analytics data. Please try again later.
          <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>
            {error}
          </div>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      {/* Learner Identity Strip */}
      <div style={{ marginBottom: '24px' }}>
        <LearnerIdentityStrip
          name={summary?.name}
          memberSince={summary?.member_since}
          totalSessions={summary?.total_sessions}
          currentStreak={summary?.current_streak}
        />
      </div>

      {/* Main Grid: Stability + Overload */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '16px',
          marginBottom: '16px',
        }}
      >
        <CognitiveStabilityPanel data={stability} />
        <CognitiveOverloadPanel data={overload} />
      </div>

      {/* Learning Modalities */}
      <ModalitiesPanel data={modalities} />

      {/* Export Button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
        <ExportReportButton />
      </div>
    </PageWrapper>
  );
}

function PageWrapper({ children }) {
  return (
    <div style={{ paddingTop: '56px', minHeight: '100vh', backgroundColor: 'var(--bg)' }}>
      <div style={{ padding: '40px 48px' }}>
        {/* Page Heading */}
        <div style={{ marginBottom: '32px' }}>
          <h1
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: '32px',
              fontWeight: 400,
              color: 'var(--navy)',
              marginBottom: '8px',
            }}
          >
            Analytics
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--muted)' }}>
            Cognitive stability, learning modalities, and engagement insights
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}