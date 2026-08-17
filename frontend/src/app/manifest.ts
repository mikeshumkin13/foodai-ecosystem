import type { MetadataRoute } from "next";

import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: copy.app.productName,
    short_name: copy.app.name,
    description: copy.app.tagline,
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#f8faf7",
    theme_color: "#18332f",
    icons: [
      {
        src: "/icon.svg",
        sizes: "192x192",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
  };
}
