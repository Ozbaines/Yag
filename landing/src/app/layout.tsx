import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YAg — самые вирусные ролики",
  description: "Отборный вирусный контент каждый день. Только то, что цепляет.",
  openGraph: {
    title: "YAg — вирусные ролики",
    description: "Смотри только вирусные. Каждый день — новое.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
