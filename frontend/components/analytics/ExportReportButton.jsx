'use client';

import { useState } from 'react';

/**
 * ExportReportButton Component
 * Triggers PDF download from GET /api/analytics/report/pdf.
 * Shows loading spinner during generation, then auto-downloads.
 */
export default function ExportReportButton() {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/analytics/report/pdf');
      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      // Extract filename from Content-Disposition or use default
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'neuroadapt_report.pdf';
      if (disposition) {
        const match = disposition.match(/filename="?(.+?)"?$/);
        if (match) filename = match[1];
      }
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('[ExportReportButton] Download failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '10px 20px',
        backgroundColor: loading ? 'var(--muted)' : 'var(--teal)',
        color: '#fff',
        border: 'none',
        borderRadius: 'var(--radius)',
        fontSize: '14px',
        fontWeight: 600,
        cursor: loading ? 'not-allowed' : 'pointer',
        transition: 'all 200ms ease',
      }}
      onMouseEnter={(e) => {
        if (!loading) {
          e.currentTarget.style.backgroundColor = '#21867a';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 157, 143, 0.2)';
        }
      }}
      onMouseLeave={(e) => {
        if (!loading) {
          e.currentTarget.style.backgroundColor = 'var(--teal)';
          e.currentTarget.style.boxShadow = 'none';
        }
      }}
    >
      {loading ? (
        <>
          <Spinner />
          Generating…
        </>
      ) : (
        <>
          {/* Download icon */}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export PDF Report
        </>
      )}
    </button>
  );
}

function Spinner() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: 'spin 1s linear infinite' }}
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.3" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}