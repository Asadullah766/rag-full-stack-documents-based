"use client";

import ThemeToggle from "../components/themetoggle";
import FileUploader from "../components/FileUploader";
import ChatBox from "../components/ChatBox";

export default function Page() {
  return (
    <main className="flex h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 bg-white dark:bg-gray-900 p-6 shadow-lg flex flex-col justify-between fixed left-0 top-0 bottom-0">
        <div className="flex-1 overflow-y-auto">
          <h2 className="text-xl font-semibold mb-4">📁 Upload & Process</h2>
          <FileUploader />
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-6">
          RAG-Qdrant v1.2
        </p>
      </aside>

      {/* Chat Area */}
      <section className="flex-1 flex flex-col p-6 relative ml-72 overflow-y-auto h-screen">
        {/* Removed duplicate ThemeToggle */}
        <h2 className="text-2xl font-semibold mb-4">💬 Chat Interface</h2>
        <ChatBox />
      </section>
    </main>
  );
}
