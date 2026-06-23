"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Send, Plus, Trash2, Bot, User, LogOut,
  Loader2, Zap, ChevronRight,
} from "lucide-react";
import { chatApi, authApi, tokenStorage, type Conversation } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

// ─── Dashboard Page ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const abortRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Auth check ───────────────────────────────────────────────────────────
  useEffect(() => {
    const token = tokenStorage.getAccess();
    if (!token) { router.push("/login"); return; }
    authApi.me()
      .then((u) => setUserEmail(u.email))
      .catch(() => { tokenStorage.clear(); router.push("/login"); });
    loadConversations();
  }, []);

  // ── Auto scroll ──────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadConversations() {
    try {
      const convs = await chatApi.listConversations();
      setConversations(convs);
    } catch (_) {}
  }

  // ── New conversation ─────────────────────────────────────────────────────
  function newConversation() {
    setActiveConvId(null);
    setMessages([]);
  }

  // ── Select conversation (load from history) ──────────────────────────────
  function selectConversation(conv: Conversation) {
    setActiveConvId(conv.id);
    setMessages([]); // TODO: load archived messages from /chat/conversations/{id}/messages
  }

  // ── Delete conversation ──────────────────────────────────────────────────
  async function deleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await chatApi.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConvId === id) newConversation();
  }

  // ── Send message ─────────────────────────────────────────────────────────
  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput("");
    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: text },
      { id: assistantMsgId, role: "assistant", content: "", isStreaming: true },
    ]);
    setIsStreaming(true);

    abortRef.current = chatApi.stream({
      message: text,
      conversation_id: activeConvId ?? undefined,
      use_tools: true,
      onChunk: (chunk) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: m.content + chunk } : m
          )
        );
      },
      onDone: (convId) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, isStreaming: false } : m
          )
        );
        if (!activeConvId) {
          setActiveConvId(convId);
          loadConversations();
        }
      },
      onError: (err) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: `⚠️ Error: ${err}`, isStreaming: false }
              : m
          )
        );
      },
    });
  }, [input, isStreaming, activeConvId]);

  // ── Keyboard: Shift+Enter = newline, Enter = send ────────────────────────
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // ── Logout ───────────────────────────────────────────────────────────────
  async function logout() {
    await authApi.logout();
    router.push("/login");
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans">

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="w-64 flex flex-col bg-gray-900 border-r border-gray-800">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-4 border-b border-gray-800">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-bold text-white tracking-wide">TITAN</span>
          <span className="text-xs text-gray-500 ml-auto">MVP</span>
        </div>

        {/* New Chat */}
        <button
          onClick={newConversation}
          className="mx-3 mt-3 flex items-center gap-2 px-3 py-2 rounded-lg
                     bg-violet-600 hover:bg-violet-500 text-white text-sm transition-colors"
        >
          <Plus size={14} />
          New conversation
        </button>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto mt-3 px-2 space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-gray-600 text-center mt-6 px-4">
              No conversations yet. Start one above.
            </p>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => selectConversation(conv)}
              className={`group w-full flex items-center justify-between px-3 py-2 rounded-lg
                          text-sm text-left truncate transition-colors
                          ${activeConvId === conv.id
                            ? "bg-gray-800 text-white"
                            : "text-gray-400 hover:bg-gray-800 hover:text-white"
                          }`}
            >
              <span className="truncate flex-1">{conv.title || "Untitled"}</span>
              <button
                onClick={(e) => deleteConversation(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 ml-2 p-0.5 rounded
                           hover:text-red-400 transition-all"
              >
                <Trash2 size={12} />
              </button>
            </button>
          ))}
        </div>

        {/* User + Logout */}
        <div className="p-3 border-t border-gray-800">
          <div className="flex items-center gap-2 px-2 py-1">
            <div className="w-7 h-7 rounded-full bg-violet-700 flex items-center justify-center text-xs font-bold">
              {userEmail.charAt(0).toUpperCase()}
            </div>
            <span className="text-xs text-gray-400 truncate flex-1">{userEmail}</span>
            <button
              onClick={logout}
              className="p-1 rounded hover:bg-gray-800 text-gray-500 hover:text-white transition-colors"
              title="Logout"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────────── */}
      <main className="flex flex-col flex-1 overflow-hidden">

        {/* Header */}
        <header className="flex items-center px-6 py-3 border-b border-gray-800 bg-gray-900">
          <Bot size={18} className="text-violet-400 mr-2" />
          <span className="text-sm font-medium text-gray-300">Executive Assistant</span>
          <span className="ml-3 text-xs text-gray-600">
            {activeConvId ? `conv: ${activeConvId.slice(0, 8)}…` : "new conversation"}
          </span>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-violet-600/20 flex items-center justify-center mb-4">
                <Zap size={28} className="text-violet-400" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">TITAN is ready</h2>
              <p className="text-gray-500 text-sm max-w-sm">
                Ask me to research, draft emails, analyze documents, or plan your day.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot size={14} className="text-white" />
                </div>
              )}

              <div
                className={`max-w-2xl px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
                  ${msg.role === "user"
                    ? "bg-violet-600 text-white rounded-tr-sm"
                    : "bg-gray-800 text-gray-100 rounded-tl-sm"
                  }`}
              >
                {msg.content}
                {msg.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-violet-400 ml-1 animate-pulse rounded-sm" />
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User size={14} className="text-gray-300" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-gray-800 bg-gray-900">
          <div className="flex items-end gap-3 max-w-4xl mx-auto">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message TITAN… (Enter to send, Shift+Enter for newline)"
              rows={1}
              disabled={isStreaming}
              className="flex-1 resize-none bg-gray-800 border border-gray-700 rounded-xl
                         px-4 py-3 text-sm text-gray-100 placeholder-gray-500
                         focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                         disabled:opacity-50 max-h-40 overflow-y-auto"
              style={{ minHeight: "48px" }}
            />
            <button
              onClick={isStreaming ? () => abortRef.current?.() : sendMessage}
              disabled={!input.trim() && !isStreaming}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all
                ${isStreaming
                  ? "bg-red-600 hover:bg-red-500"
                  : "bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed"
                }`}
              title={isStreaming ? "Stop generating" : "Send message"}
            >
              {isStreaming
                ? <Loader2 size={16} className="text-white animate-spin" />
                : <Send size={15} className="text-white" />
              }
            </button>
          </div>
          <p className="text-xs text-gray-600 text-center mt-2">
            TITAN can use web search, send emails, and read documents.
          </p>
        </div>
      </main>
    </div>
  );
}
