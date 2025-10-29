import "./globals.css";
import { Geist } from "next/font/google";
import Navbar from "../components/Navbar";
import ThemeProviderWrapper from "../components/ThemeProviderWrapper";

const geist = Geist({ subsets: ["latin"], weight: "400" });

export const metadata = {
  title: "RAG App",
  description: "Chat with your uploaded documents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.className} bg-gray-100 dark:bg-gray-900`}>
        {/* ThemeProviderWrapper must be inside <body> */}
        <ThemeProviderWrapper>
          <Navbar />
          {children}
        </ThemeProviderWrapper>
      </body>
    </html>
  );
}
