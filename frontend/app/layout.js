'use client';

import "./globals.css";
import Navbar from '@/components/Navbar';
import { useEffect } from 'react';
import { init, destroy } from '@/components/Observer';

export default function RootLayout({ children }) {
  useEffect(() => {
    // Initialize Observer globally (persists across page navigations)
    init();

    return () => {
      // Only cleanup when the entire app unmounts
      destroy();
    };
  }, []);

  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Serif+Display:wght@400&display=swap" rel="stylesheet" />
      </head>
      <body>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
