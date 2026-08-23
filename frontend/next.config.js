/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Allow product images from Amazon CDN and any domain
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.media-amazon.com',
      },
      {
        protocol: 'https',
        hostname: '**.amazon.com',
      },
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // Surface the Railway backend URL to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

module.exports = nextConfig;
