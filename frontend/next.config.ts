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
      { protocol: "https", hostname: "www.masoutis.gr" },
    ],
  },
};

export default nextConfig;
