import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppShell } from "@/components/Layout";
import { AppProviders } from "@/components/Providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const description =
  "OpsMind AI is an enterprise knowledge intelligence platform that unifies your team's data, docs, and workflows into a single AI-powered workspace.";

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: {
    default: "OpsMind AI",
    template: "%s | OpsMind AI",
  },
  description,
  applicationName: "OpsMind AI",
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    siteName: "OpsMind AI",
    title: "OpsMind AI",
    description,
  },
  twitter: {
    card: "summary",
    title: "OpsMind AI",
    description,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
