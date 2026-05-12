'use client';

/**
 * Loader Component
 * Displays a spinner with contextual message based on action type
 */
export default function Loader({ actionId = null, message = null }) {
  // Map action_id to contextual loading messages
  const getLoadingMessage = () => {
    if (message) return message;

    const messageMap = {
      1: '🔤 Generating simplified text...',
      2: '📖 Generating simplified text...',
      3: '🎵 Generating narrated content...',
      4: '❓ Creating quiz...',
      5: '🌬️ Preparing sensory break...',
    };

    return messageMap[actionId] || '✨ Adapting this slide...';
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: '32px',
        padding: '32px 20px',
        minHeight: '200px',
        gap: '16px',
      }}
    >
      {/* Spinner */}
      <div
        style={{
          width: '48px',
          height: '48px',
          border: '4px solid rgba(0, 150, 136, 0.2)',
          borderTop: '4px solid var(--teal)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />

      {/* Message */}
      <p
        style={{
          color: 'var(--muted)',
          fontSize: '14px',
          fontWeight: 500,
          textAlign: 'center',
          margin: 0,
        }}
      >
        {getLoadingMessage()}
      </p>

      {/* Spinner animation keyframes */}
      <style>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
