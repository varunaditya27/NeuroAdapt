/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_TELEMETRY_INTERVAL: process.env.TELEMETRY_INTERVAL || '30000',
    NEXT_PUBLIC_CONFIDENCE_GATE: process.env.CONFIDENCE_GATE || '0.60',
    NEXT_PUBLIC_MOCK_API: process.env.MOCK_API || 'true',
    NEXT_PUBLIC_ACTION_SPACE: '6',
    NEXT_PUBLIC_STATE_VECTOR_DIM: '5',
  },
};

export default nextConfig;
