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
    // ThemeProviderWrapper ko html ke upar rakha
    <ThemeProviderWrapper>
      <html lang="en" suppressHydrationWarning>
        <body className={`${geist.className} bg-gray-100 dark:bg-gray-900`}>
          <Navbar />
          {children}
        </body>
      </html>
    </ThemeProviderWrapper>
  );
}
