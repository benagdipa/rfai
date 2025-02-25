/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React Strict Mode for development checks
  reactStrictMode: true,

  // Environment variables exposed to the client (prefixed with NEXT_PUBLIC_)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
  },

  // Custom webpack configuration
  webpack: (config, { isServer }) => {
    // Add support for WebSocket connections on the client
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false, // Not needed on client-side
        net: false,
        tls: false,
      };
    }

    return config;
  },

  // Image optimization configuration
  images: {
    domains: ['localhost', 'example.com'],
    formats: ['image/avif', 'image/webp'],
  },

  // Custom headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
        ],
      },
    ];
  },

  // Performance optimizations
  swcMinify: true, // Use SWC minifier (built-in, no extra dependency needed)
  productionBrowserSourceMaps: false, // Disable source maps in production
};

module.exports = nextConfig;