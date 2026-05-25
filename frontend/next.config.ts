import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Allowlist of CDNs we expect to serve product images. Add new
    // hostnames here as more chains come online.
    remotePatterns: [
      { protocol: "https", hostname: "*.ab.gr" },
      { protocol: "https", hostname: "www.ab.gr" },
      { protocol: "https", hostname: "cdn.mymarket.gr" },
      { protocol: "https", hostname: "www.mymarket.gr" },
      { protocol: "https", hostname: "www.lidl-hellas.gr" },
      { protocol: "https", hostname: "masoutisimagesneu.blob.core.windows.net" },
      { protocol: "https", hostname: "www.sklavenitis.gr" },
      { protocol: "https", hostname: "*.sklavenitis.gr" },
      { protocol: "https", hostname: "www.masoutis.gr" },
    ],
  },
  // Quiet HMR / dev-resource cross-origin warnings when accessing via
  // 127.0.0.1 instead of localhost.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
