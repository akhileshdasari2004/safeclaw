/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@safeclaw/shared-types"],
};

export default nextConfig;
