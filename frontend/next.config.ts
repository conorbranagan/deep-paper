import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  devIndicators: {
    position: "bottom-right",
  },
  images: {
    remotePatterns: [
      {
        hostname: "www.google.com",
      },
    ],
  },
};

export default nextConfig;
