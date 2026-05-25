import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

// Inter ships a Greek subset, which Geist does not.
const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin", "latin-ext", "greek"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Προσφορές Σούπερ Μάρκετ",
    template: "%s · Προσφορές Σούπερ Μάρκετ",
  },
  description:
    "Καθημερινές προσφορές από όλα τα μεγάλα ελληνικά σούπερ μάρκετ σε ένα μέρος. AB, Σκλαβενίτης, Lidl, My Market, Μασούτης.",
  openGraph: {
    title: "Προσφορές Σούπερ Μάρκετ",
    description:
      "Καθημερινές προσφορές από όλα τα ελληνικά σούπερ μάρκετ σε ένα μέρος.",
    locale: "el_GR",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="el"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-canvas font-sans text-ink">
        <Header />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
