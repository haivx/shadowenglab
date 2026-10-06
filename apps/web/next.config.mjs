/** @type {import("next").NextConfig} */
const nextConfig = {
  transpilePackages: ["@shadowenglab/contracts"],
  // ESLint 9 + plugin Next 14 bị crash khi build; lint chạy qua `make lint`.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
