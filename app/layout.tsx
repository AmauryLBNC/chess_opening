import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Echiquier - Entrainement",
  description: "Application web statique pour s'entrainer sur les variantes d'echecs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
