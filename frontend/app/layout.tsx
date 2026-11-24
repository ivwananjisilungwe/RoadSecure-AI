import type { Metadata } from "next";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoadSecure AI",
  description: "Defensive monitoring for synthetic road transport activity",
};

const themeScript = `(function(){try{var theme=localStorage.getItem('roadsecure-theme');if(theme==='light'||theme==='dark'){document.documentElement.dataset.theme=theme;}}catch(error){}})();`;

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head><body>{children}</body></html>;
}
