'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '56px',
        backgroundColor: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        zIndex: 999,
      }}
    >
      <div
        style={{
          maxWidth: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingLeft: '24px',
          paddingRight: '24px',
        }}
      >
        {/* Left: Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: '20px',
              fontWeight: 400,
              color: 'var(--navy)',
            }}
          >
            NeuroAdapt
          </span>
          <span
            style={{
              display: 'inline-block',
              backgroundColor: 'var(--teal-soft)',
              color: 'var(--teal)',
              padding: '4px 10px',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: 500,
            }}
          >
            POC
          </span>
        </div>

        {/* Right: Nav Links */}
        <div style={{ display: 'flex', gap: '32px' }}>
          <Link
            href="/"
            style={{
              color: 'var(--text)',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
              paddingBottom: '8px',
              borderBottom: pathname === '/' ? '2px solid var(--teal)' : '2px solid transparent',
              transition: 'border-color 200ms ease',
            }}
          >
            Lesson
          </Link>
          <Link
            href="/dashboard"
            style={{
              color: 'var(--text)',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
              paddingBottom: '8px',
              borderBottom: pathname === '/dashboard' ? '2px solid var(--teal)' : '2px solid transparent',
              transition: 'border-color 200ms ease',
            }}
          >
            Dashboard
          </Link>
          <Link
            href="/dashboard/analytics"
            style={{
              color: 'var(--text)',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
              paddingBottom: '8px',
              borderBottom: pathname === '/dashboard/analytics' ? '2px solid var(--teal)' : '2px solid transparent',
              transition: 'border-color 200ms ease',
            }}
          >
            Analytics
          </Link>
        </div>
      </div>
    </nav>
  );
}
