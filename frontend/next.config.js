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

    // Optimize CSS handling (optional if using a CSS minifier)
    if (isServer) {
      const TerserPlugin = require('terser-webpack-plugin');
      config.optimization.minimizer.push(new TerserPlugin());
    }

    return config;
  },

  // Image optimization configuration
  images: {
    domains: ['localhost', 'example.com'], // Add domains for external images if needed
    formats: ['image/avif', 'image/webp'], // Modern image formats for optimization
  },

  // Custom headers for security and CORS (optional)
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

  // Custom rewrites for WebSocket proxying (if needed)
  async rewrites() {
    return [
      {
        source: '/ws',
        destination: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
      },
    ];
  },

  // Performance optimizations
  swcMinify: true, // Enable SWC minifier for faster builds (Next.js 12+)
  productionBrowserSourceMaps: false, // Disable source maps in production for smaller bundles

  // TypeScript support (optional, uncomment if using TypeScript)
  // typescript: {
  //   ignoreBuildErrors: false, // Enforce type checking in production builds
  // },

  // ESLint configuration (optional, uncomment to enable)
  // eslint: {
  //   dirs: ['pages', 'components', 'lib', 'store'], // Folders to lint
  //   ignoreDuringBuilds: false, // Run ESLint during builds
  // },
};

module.exports = nextConfig;