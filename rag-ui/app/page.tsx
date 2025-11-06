"use client";

import { useState } from "react";
import ThemeToggle from "../components/themetoggle";
import FileUploader from "../components/FileUploader";
import ChatBox from "../components/ChatBox";

export default function Page() {
  // ✅ Chat reset control
  const [chatKey, setChatKey] = useState(0);

  // ✅ Function to reset chat when file process completes
  const handleResetChat = () => {
    setChatKey((prev) => prev + 1);
  };

  return (
    <main className="flex h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 bg-white dark:bg-gray-900 p-6 shadow-lg flex flex-col justify-between fixed left-0 top-0 bottom-0 overflow-y-auto scrollbar-hide">
        <div className="flex-1">
          <h2 className="text-xl font-semibold mb-4">📁 Upload & Process</h2>
          {/* ✅ Pass the reset function */}
          <FileUploader onProcessComplete={handleResetChat} />
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-6">
          RAG-Qdrant v1.2
        </p>
      </aside>

      {/* Chat Area */}
      <section className="flex-1 flex flex-col ml-72 h-screen">
        <div className="flex-1 overflow-y-auto scrollbar-hide p-6">
          <h2 className="text-2xl font-semibold mb-4">💬 Chat Interface</h2>

          {/* ✅ ChatBox resets when chatKey changes */}
          <ChatBox key={chatKey} />
        </div>
      </section>
    </main>
  );
}
