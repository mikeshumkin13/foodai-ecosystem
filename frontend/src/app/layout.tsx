import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { ServiceWorkerRegistration } from "@/components/service-worker-registration";
import { messages } from "@/lib/i18n/messages";

import "./globals.css";

const copy = messages.ru;

export const metadata: Metadata = {
  applicationName: copy.app.productName,
  title: {
    default: copy.app.productName,
    template: `%s | ${copy.app.name}`,
  },
  description: copy.app.tagline,
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#18332f",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru">
      <body>
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
