import type { Metadata } from "next";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoadSecure AI",
  description: "Defensive monitoring for synthetic road transport activity",
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
