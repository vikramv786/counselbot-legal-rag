
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  retrievalType?: string;
  accessStatus?: string;
};

type Source = {
  source_document: string;
  section_title: string;
  collection: string;
};

type DemoUsername =
  | "gc.sharma"
  | "adv.rao"
  | "adv.nair"
  | "adv.khan"
  | "adv.iyer"
  | "comp.deshpande"
  | "comp.bose"
  | "para.sneha";

type UserProfile = {
  username: string;
  role: string;
  matters: string[];
  collections: string[];
};

const DEMO_USERS: { username: DemoUsername; label: string }[] = [
  { username: "gc.sharma", label: "General Counsel" },
  { username: "adv.rao", label: "Corporate Counsel" },
  { username: "adv.nair", label: "Corporate Counsel" },
  { username: "adv.khan", label: "Litigation Counsel" },
  { username: "adv.iyer", label: "Litigation Counsel" },
  { username: "comp.deshpande", label: "Compliance Officer" },
  { username: "comp.bose", label: "Compliance Officer" },
  { username: "para.sneha", label: "Paralegal" },
];

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

export default function Home() {
  const [username, setUsername] = useState<DemoUsername>("adv.rao");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  function handleLogout() {
    setToken(null);
    setProfile(null);
    setPassword("");
    setQuestion("");
    setMessages([]);
    setLoginError("");
  }

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loginLoading) {
      return;
    }

    setLoginLoading(true);
    setLoginError("");

    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Login failed. Check your username and password."
        );
      }

      if (typeof data.access_token !== "string") {
        throw new Error("The server did not return an access token.");
      }

      const accessToken = data.access_token;

      // Verify the token and retrieve the authenticated user's
      // role and matter permissions from FastAPI.
      const profileResponse = await fetch(
        "/api/me",
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!profileResponse.ok) {
        throw new Error("Login succeeded, but profile verification failed.");
      }

      const userProfile: UserProfile = await profileResponse.json();

      setToken(accessToken);
      setProfile(userProfile);
      setMessages([]);
      setPassword("");
    } catch (error) {
      setLoginError(
        error instanceof Error ? error.message : "Unable to log in."
      );
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleSend() {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || isLoading || !token) {
      return;
    }

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
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: trimmedQuestion,
        }),
      });

      const data = await response.json();

      if (response.status === 401) {
        handleLogout();
        setLoginError("Your session has expired. Please log in again.");
        return;
      }

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

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
          sources: Array.isArray(data.sources) ? data.sources : [],
          retrievalType:
            typeof data.retrieval_type === "string"
              ? data.retrieval_type
              : undefined,
          accessStatus:
            typeof data.access_status === "string"
              ? data.access_status
              : undefined,
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
      <header className="border-b border-slate-800 px-6 py-5">
        <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">⚖️ CounselBot</h1>
            <p className="mt-1 text-sm text-slate-400">
              AI-Powered Legal Research Assistant
            </p>
          </div>

          {profile && (
            <button
              onClick={handleLogout}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold hover:bg-slate-800"
            >
              Log out
            </button>
          )}
        </div>
      </header>

      {!profile ? (
        <section className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-12">
          <div className="rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
            <h2 className="text-2xl font-bold">Sign in to CounselBot</h2>

            <p className="mt-2 text-sm text-slate-400">
              Choose a demo account to explore role-based and
              matter-based legal research access.
            </p>

            <form onSubmit={handleLogin} className="mt-8 space-y-5">
              <div>
                <label
                  htmlFor="username"
                  className="mb-2 block text-sm font-semibold text-slate-300"
                >
                  Demo user
                </label>

                <select
                  id="username"
                  value={username}
                  onChange={(event) =>
                    setUsername(event.target.value as DemoUsername)
                  }
                  disabled={loginLoading}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-emerald-500"
                >
                  {DEMO_USERS.map((user) => (
                    <option key={user.username} value={user.username}>
                      {user.username} — {user.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="mb-2 block text-sm font-semibold text-slate-300"
                >
                  Password
                </label>

                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  autoComplete="current-password"
                  disabled={loginLoading}
                  placeholder="Enter demo password"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-emerald-500"
                />
              </div>

              {loginError && (
                <p
                  role="alert"
                  className="rounded-lg border border-red-800 bg-red-950/50 p-3 text-sm text-red-300"
                >
                  {loginError}
                </p>
              )}

              <button
                type="submit"
                disabled={loginLoading || !password}
                className="w-full rounded-lg bg-emerald-600 px-5 py-3 font-semibold hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loginLoading ? "Signing in..." : "Sign in"}
              </button>
            </form>

            <p className="mt-6 text-center text-xs text-slate-500">
              Local development demo only. Do not use real client data.
            </p>
          </div>
        </section>
      ) : (
        <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col p-6">
          <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-400">
              Authenticated session
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">
                User: {profile.username}
              </span>

              <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">
                Role: {formatLabel(profile.role)}
              </span>

              <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">
                Collections: {profile.collections.join(", ")}
              </span>

              <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">
                Matters:{" "}
                {profile.matters.length > 0
                  ? profile.matters.join(", ")
                  : "None assigned"}
              </span>
            </div>
          </div>

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
                  Answers are filtered using your authenticated role
                  and matter permissions.
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
                    {message.role === "user" ? "You" : "CounselBot"}
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

                      {message.retrievalType && (
                        <p className="text-xs text-slate-500">
                          Retrieval: {formatLabel(message.retrievalType)}
                        </p>
                      )}

                      {message.accessStatus &&
                        message.accessStatus !== "ok" && (
                          <p className="text-xs text-amber-400">
                            Access status:{" "}
                            {formatLabel(message.accessStatus)}
                          </p>
                        )}

                      {message.sources &&
                        message.sources.length > 0 && (
                          <div className="mt-4 border-t border-slate-700 pt-4">
                            <h3 className="mb-2 font-semibold text-emerald-300">
                              Sources
                            </h3>

                            <ul className="space-y-2">
                              {message.sources.map((source, sourceIndex) => (
                                <li
                                  key={sourceIndex}
                                  className="rounded-lg bg-slate-800 p-3 text-xs"
                                >
                                  <p className="font-semibold">
                                    {source.source_document}
                                  </p>
                                  <p className="mt-1 text-slate-300">
                                    Section: {source.section_title}
                                  </p>
                                  <p className="mt-1 text-slate-400">
                                    Collection: {source.collection}
                                  </p>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                    </div>
                  )}
                </div>
              ))
            )}

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

          <div className="sticky bottom-0 border-t border-slate-800 bg-slate-950 py-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
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
              Demo authentication only. Do not use real client data.
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
