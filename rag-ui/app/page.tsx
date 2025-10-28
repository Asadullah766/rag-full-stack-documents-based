"use client";

import ThemeToggle from "../components/themetoggle";
import FileUploader from "../components/FileUploader";
import ChatBox from "../components/ChatBox";

export default function Page() {
  return (
    <main className="flex min-h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Sidebar */}
      <aside className="w-72 bg-white dark:bg-gray-900 p-6 shadow-lg flex flex-col justify-between">
        <div>
          <h2 className="text-xl font-semibold mb-4">📁 Upload & Process</h2>
          <FileUploader />
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-6">
          RAG-Qdrant v1.2
        </p>
      </aside>

      {/* Chat Area */}
      <section className="flex-1 flex flex-col p-6 relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <h2 className="text-2xl font-semibold mb-4">💬 Chat Interface</h2>
        <ChatBox />
      </section>
    </main>
  );
}
