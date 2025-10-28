// ChatBox.tsx (fixed for Markdown + Syntax Highlighting visibility)
"use client";

import dynamic from "next/dynamic";
import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import { ArrowRight } from "lucide-react";

// SSR-safe SyntaxHighlighter
const SyntaxHighlighter = dynamic(
  () => import("react-syntax-highlighter").then((mod) => mod.Prism),
  { ssr: false }
);
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function ChatBox() {
  const [messages, setMessages] = useState<{ text: string; sender: "user" | "system" }[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Typing effect for a single block
  const typeMessage = async (fullText: string) => {
    setMessages((prev) => [...prev, { text: "", sender: "system" }]); // Add empty block first
    let current = "";
    for (let char of fullText) {
      current += char;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.sender === "system") {
          return [...prev.slice(0, -1), { text: current, sender: "system" }];
        } else {
          return [...prev, { text: current, sender: "system" }];
        }
      });
      await new Promise((r) => setTimeout(r, 10)); // typing speed
    }
  };

  // Send message
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { text: input, sender: "user" as const };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });

      const data = await res.json();

      // Extract answer
      let answer = "";
      if (typeof data === "string") answer = data;
      else if (data.answer) answer = data.answer;
      else if (data.detail) answer = data.detail;
      else answer = JSON.stringify(data);

      // Type entire response in one block
      await typeMessage(answer);

    } catch (err) {
      setMessages((prev) => [...prev, { text: "⚠️ Backend connection failed.", sender: "system" }]);
      console.error(err);
    }
  };

  return (
    <div className="relative flex flex-col h-full bg-gray-100 dark:bg-gray-900 rounded-xl shadow-md">
      <div className="flex-1 overflow-y-auto p-4 space-y-3 mb-32">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-[75%] px-4 py-2 rounded-2xl shadow-sm ${
              msg.sender === "user"
                ? "bg-blue-500 text-white self-end ml-auto"
                : "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            }`}
          >
            <ReactMarkdown
              rehypePlugins={[rehypeRaw]}
              components={{
                h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
                h2: ({node, ...props}) => <h2 className="text-xl font-semibold mt-3 mb-1" {...props} />,
                h3: ({node, ...props}) => <h3 className="text-lg font-semibold mt-2 mb-1" {...props} />,
                code({ node, inline, className, children, ...props }: any) {
                  if (inline) return <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded" {...props}>{children}</code>;
                  return (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={className?.replace("language-", "")}
                      PreTag="div"
                      {...(props as any)}
                    >
                      {String(children).replace(/\n$/, "")}
                    </SyntaxHighlighter>
                  );
                },
                p: ({node, ...props}) => <p className="mb-2" {...props} />,
                li: ({node, ...props}) => <li className="ml-5 list-disc mb-1" {...props} />,
              }}
            >
              {msg.text}
            </ReactMarkdown>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="fixed bottom-8 left-0 w-full flex justify-center px-4">
        <div className="relative w-[800px]">
          <input
            type="text"
            className="w-full rounded-full px-4 py-5 pr-14 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"
            placeholder="Ask something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-full flex items-center justify-center"
          >
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
