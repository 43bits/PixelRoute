/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
    remotePatterns: [],
  },
  // NOTE: rewrites are intentionally removed.
  // The frontend calls the backend directly via NEXT_PUBLIC_API_URL at runtime.
  // A rewrite destination that depends on a runtime env var is invalid at build time
  // and causes "Invalid rewrite found" on Vercel.
};

module.exports = nextConfig;
