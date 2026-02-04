import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "SigAid - Cryptographic Identity for AI Agents",
  description:
    "One identity. One instance. Complete audit trail. Give your AI agents verifiable cryptographic identity with exclusive leasing and tamper-proof state chains.",
  keywords: [
    "AI agents",
    "cryptographic identity",
    "agent verification",
    "state chain",
    "Ed25519",
    "autonomous agents",
  ],
  authors: [{ name: "SigAid" }],
  openGraph: {
    title: "SigAid - Cryptographic Identity for AI Agents",
    description:
      "One identity. One instance. Complete audit trail. Give your AI agents verifiable cryptographic identity.",
    url: "https://sigaid.com",
    siteName: "SigAid",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "SigAid - Cryptographic Identity for AI Agents",
    description:
      "One identity. One instance. Complete audit trail. Give your AI agents verifiable cryptographic identity.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
