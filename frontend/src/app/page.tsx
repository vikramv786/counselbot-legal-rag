
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type DemoUsername = "adv.rao" | "gc.sharma";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [username, setUsername] = useState<DemoUsername>("adv.rao");

  async function handleSend() {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || isLoading) {
      return;
    }

    // Display the user's question.
    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: trimmedQuestion,
      },
    ]);

    setQuestion("");
    setIsLoading(true);

    try {
      // Send the question through Next.js to FastAPI.
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username,
          question: trimmedQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Something went wrong."
        );
      }

      if (typeof data.answer !== "string") {
        throw new Error("The backend returned an invalid answer.");
      }

      // Display the answer from the legal RAG pipeline.
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
        },
      ]);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "An unexpected error occurred.";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: `Error: ${errorMessage}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-5">
        <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">
              ⚖️ CounselBot
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              AI-Powered Legal Research Assistant
            </p>
          </div>

          {/* Demo-user selector */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="demo-user"
              className="text-xs font-semibold text-slate-400"
            >
              Demo user
            </label>

            <select
              id="demo-user"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value as DemoUsername);
                setMessages([]);
              }}
              disabled={isLoading}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500 disabled:opacity-50"
            >
              <option value="adv.rao">
                adv.rao — Corporate Counsel
              </option>

              <option value="gc.sharma">
                gc.sharma — General Counsel
              </option>
            </select>
          </div>
        </div>
      </header>

      {/* Chat area */}
      <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col p-6">
        <div className="mb-6 flex-1 space-y-4">
          {messages.length === 0 ? (
            <div className="py-16 text-center">
              <h2 className="text-3xl font-semibold">
                Welcome to CounselBot
              </h2>

              <p className="mt-4 text-slate-400">
                Ask about contracts, litigation, or legal documents.
              </p>

              <p className="mt-3 text-sm text-slate-500">
                Select a demo user to explore matter-based access.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`rounded-xl p-4 ${message.role === "user"
                    ? "ml-12 bg-emerald-900"
                    : "mr-12 border border-slate-700 bg-slate-900"
                  }`}
              >
                <p className="mb-2 text-xs font-semibold uppercase text-slate-400">
                  {message.role === "user"
                    ? "You"
                    : "CounselBot"}
                </p>

                {message.role === "user" ? (
                  <p className="whitespace-pre-wrap break-words">
                    {message.content}
                  </p>
                ) : (
                  <div className="space-y-3 break-words text-sm leading-7">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => (
                          <h2 className="text-xl font-bold text-white">
                            {children}
                          </h2>
                        ),
                        h2: ({ children }) => (
                          <h2 className="text-lg font-bold text-white">
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className="font-semibold text-white">
                            {children}
                          </h3>
                        ),
                        p: ({ children }) => (
                          <p className="my-3">{children}</p>
                        ),
                        strong: ({ children }) => (
                          <strong className="font-bold text-emerald-300">
                            {children}
                          </strong>
                        ),
                        ul: ({ children }) => (
                          <ul className="my-3 list-disc space-y-1 pl-6">
                            {children}
                          </ul>
                        ),
                        ol: ({ children }) => (
                          <ol className="my-3 list-decimal space-y-1 pl-6">
                            {children}
                          </ol>
                        ),
                        table: ({ children }) => (
                          <div className="my-4 overflow-x-auto rounded-lg border border-slate-700">
                            <table className="w-full border-collapse text-left text-sm">
                              {children}
                            </table>
                          </div>
                        ),
                        thead: ({ children }) => (
                          <thead className="bg-slate-800 text-emerald-300">
                            {children}
                          </thead>
                        ),
                        th: ({ children }) => (
                          <th className="border-b border-slate-700 px-4 py-3 font-semibold">
                            {children}
                          </th>
                        ),
                        td: ({ children }) => (
                          <td className="border-b border-slate-800 px-4 py-3 align-top">
                            {children}
                          </td>
                        ),
                        tr: ({ children }) => (
                          <tr className="hover:bg-slate-800/50">
                            {children}
                          </tr>
                        ),
                        code: ({ children }) => (
                          <code className="rounded bg-slate-800 px-1 py-0.5 text-emerald-300">
                            {children}
                          </code>
                        ),
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            ))
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="mr-12 rounded-xl border border-slate-700 bg-slate-900 p-4">
              <p className="mb-2 text-xs font-semibold uppercase text-slate-400">
                CounselBot
              </p>

              <p className="animate-pulse text-emerald-400">
                Searching legal documents and preparing your answer...
              </p>
            </div>
          )}
        </div>

        {/* Question input */}
        <div className="sticky bottom-0 border-t border-slate-800 bg-slate-950 py-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleSend();
                }
              }}
              placeholder="Ask a legal question..."
              disabled={isLoading}
              className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-emerald-500 disabled:opacity-50"
            />

            <button
              onClick={handleSend}
              disabled={!question.trim() || isLoading}
              className="rounded-xl bg-emerald-600 px-6 py-3 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </div>

          <p className="mt-3 text-center text-xs text-slate-500">
            Veridian Legal Hub · Local development demo
          </p>

          <p className="mt-1 text-center text-xs text-slate-600">
            Demo identities are not authenticated. Do not use real client data.
          </p>
        </div>
      </section>
    </main>
  );
}
