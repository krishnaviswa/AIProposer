/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The web client talks to FastAPI only. No rewrites to third parties.
};

export default nextConfig;
