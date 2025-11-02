"use client";

import dynamic from "next/dynamic";
import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import { ArrowRight, Square, Copy } from "lucide-react";

const SyntaxHighlighter = dynamic(
  () => import("react-syntax-highlighter").then((mod) => mod.Prism),
  { ssr: false }
);
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Message {
  text: string;
  sender: "user" | "system";
}

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const stopRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const typeMessage = async (fullText: string) => {
    stopRef.current = false;
    setMessages((prev) => [...prev, { text: "", sender: "system" }]);
    let current = "";
    const delay = 0.5;
    const chunkSize = 20;

    for (let i = 0; i < fullText.length; i++) {
      if (stopRef.current) break;
      current += fullText[i];

      if (i % chunkSize === 0 || i === fullText.length - 1) {
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg.sender === "system") {
            return [...prev.slice(0, -1), { text: current, sender: "system" }];
          }
          return [...prev, { text: current, sender: "system" }];
        });
      }
      await new Promise((r) => setTimeout(r, delay));
    }

    setMessages((prev) => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg.sender === "system") {
        return [...prev.slice(0, -1), { text: fullText, sender: "system" }];
      }
      return prev;
    });

    setIsGenerating(false);
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { text: input, sender: "user" as const };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsGenerating(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });

      const data = await res.json();
      let answer = data.answer || data.detail || "No response from model.";
      if (typeof answer !== "string") answer = JSON.stringify(answer, null, 2);

      await typeMessage(answer);
    } catch (err) {
      console.error("Error:", err);
      setMessages((prev) => [
        ...prev,
        { text: "⚠️ Unable to connect to backend.", sender: "system" },
      ]);
      setIsGenerating(false);
    }
  };

  const handleStop = () => {
    stopRef.current = true;
    setIsGenerating(false);
  };

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
  };

  return (
    <div className="relative flex flex-col h-full w-full bg-black">
      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-6 pb-20 scrollbar-hide scroll-smooth max-w-5xl w-full mx-auto">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex mb-4 ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.sender === "user" ? (
              <div className="px-6 py-4 rounded-3xl shadow-md leading-relaxed whitespace-pre-wrap bg-gray-600 text-white inline-block max-w-[85%]">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            ) : (
              <div className="w-full p-4 rounded-2xl mb-4 shadow-md text-gray-200 leading-relaxed whitespace-pre-wrap break-words">
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    code: ({ inline, className, children, ...props }: any) => {
                      const match = /language-(\w+)/.exec(className || "");
                      const codeString = String(children).replace(/\n$/, "");
                      return !inline && match ? (
                        <div className="relative group my-3">
                          <button
                            onClick={() => handleCopy(codeString)}
                            className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition bg-gray-700 hover:bg-gray-600 text-xs px-2 py-1 rounded-md flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy
                          </button>
                          <SyntaxHighlighter
                            language={match[1]}
                            PreTag="div"
                            style={oneDark as any}
                            customStyle={{
                              borderRadius: "0.5rem",
                              padding: "1rem",
                              fontSize: "0.95rem",
                              lineHeight: "1.6",
                            }}
                          >
                            {codeString}
                          </SyntaxHighlighter>
                        </div>
                      ) : (
                        <code
                          className="bg-gray-700 px-2 py-1 rounded text-green-400 text-sm"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ))}

        {isGenerating && (
          <div className="text-gray-400 italic animate-pulse ml-4">
            ✨ AI is thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div
        className={`absolute left-0 right-0 w-full px-6 text-center transition-all duration-700 ease-in-out ${
          messages.length > 0
            ? "bottom-4 max-w-5xl mx-auto"
            : "top-1/2 -translate-y-1/2 max-w-5xl mx-auto"
        }`}
      >
        {messages.length === 0 && (
          <div className="mb-8 text-gray-200 text-2xl font-semibold animate-fade-in">
            👋 Welcome! How can I help you today?
          </div>
        )}

        <div className="relative w-full">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask something..."
            className="w-full p-5 pr-16 text-lg rounded-full border border-gray-700 bg-gray-600 text-white focus:ring-2 focus:ring-gray-500 focus:outline-none"
            disabled={isGenerating}
          />
          <button
            onClick={isGenerating ? handleStop : handleSend}
            className={`absolute right-3 top-1/2 -translate-y-1/2 p-3 rounded-full transition flex items-center justify-center z-20 ${
              isGenerating
                ? "bg-gray-700 text-white border-none hover:bg-gray-700"
                : "bg-gray-700 hover:bg-gray-600 text-white"
            }`}
          >
            {isGenerating ? (
              <Square className="w-5 h-5 fill-current" />
            ) : (
              <ArrowRight className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
