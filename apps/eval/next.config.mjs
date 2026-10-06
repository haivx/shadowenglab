/** @type {import("next").NextConfig} */
const nextConfig = {
  // Phase 6 sẽ import ClipManifest/Label từ contracts.
  transpilePackages: ["@shadowenglab/contracts"],
  // ESLint 9 + plugin Next 14 bị crash khi build; lint chạy qua `make lint`.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
