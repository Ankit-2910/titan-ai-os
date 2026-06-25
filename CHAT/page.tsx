"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Send, Plus, Trash2, Bot, User, LogOut,
  Loader2, HeartPulse, Server, School, Sparkles, Repeat,
} from "lucide-react";
import { chatApi, authApi, tokenStorage, domainStorage, type Conversation } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

const DOMAIN_META: Record<string, { name: string; icon: React.ReactNode }> = {
  healthcare: { name: "Healthcare OS", icon: <HeartPulse size={15} /> },
  it: { name: "IT Operations OS", icon: <Server size={15} /> },
  education: { name: "Education OS", icon: <School size={15} /> },
  general: { name: "General", icon: <Sparkles size={15} /> },
};

export default function DashboardPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [domain, setDomain] = useState("general");
  const abortRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = tokenStorage.getAccess();
    if (!token) { router.push("/login"); return; }
    setDomain(domainStorage.get());
    authApi.me()
      .then((u) => setUserEmail(u.email))
      .catch(() => { tokenStorage.clear(); router.push("/login"); });
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadConversations() {
    try {
      const convs = await chatApi.listConversations();
      setConversations(convs);
    } catch (_) {}
  }

  function newConversation() {
    setActiveConvId(null);
    setMessages([]);
  }

  async function selectConversation(conv: Conversation) {
    setActiveConvId(conv.id);
    setMessages([]);
    try {
      const res = await chatApi.getMessages(conv.id);
      const loaded: Message[] = res.messages.map((m) => ({
        id: crypto.randomUUID(),
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
      }));
      setMessages(loaded);
    } catch (_) {
      setMessages([]);
    }
  }

  async function deleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await chatApi.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConvId === id) newConversation();
  }

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
      use_tools: false,
      domain: domain,
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
  }, [input, isStreaming, activeConvId, domain]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function logout() {
    await authApi.logout();
    router.push("/login");
  }

  const dm = DOMAIN_META[domain] || DOMAIN_META.general;

  return (
    <div className="dash-root">
      <aside className="sidebar">
        <div className="logo-row">
          <div className="logo-box">
            <svg width="20" height="20" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="dg" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
                  <stop offset="0" stopColor="#c4b5fd" /><stop offset="1" stopColor="#6d28d9" />
                </linearGradient>
              </defs>
              <path d="M50 10 L86 30 L86 70 L50 90 L14 70 L14 30 Z" fill="none" stroke="url(#dg)" strokeWidth="4" strokeLinejoin="round" />
              <path d="M36 40 L64 40 M50 40 L50 68" fill="none" stroke="url(#dg)" strokeWidth="8" strokeLinecap="round" />
            </svg>
          </div>
          <span className="logo-text">TITAN</span>
        </div>

        <button className="new-btn" onClick={newConversation}>
          <Plus size={14} /> New conversation
        </button>

        <button className="change-sector" onClick={() => router.push("/select")}>
          <Repeat size={13} /> Change sector
        </button>

        <div className="conv-list">
          {conversations.length === 0 && (
            <p className="empty-hint">No conversations yet.</p>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => selectConversation(conv)}
              className={`conv-item ${activeConvId === conv.id ? "active" : ""}`}
            >
              <span className="conv-title">{conv.title || "Untitled"}</span>
              <span className="conv-del" onClick={(e) => deleteConversation(conv.id, e)}>
                <Trash2 size={12} />
              </span>
            </button>
          ))}
        </div>

        <div className="user-row">
          <div className="avatar">{userEmail.charAt(0).toUpperCase()}</div>
          <span className="user-email">{userEmail}</span>
          <button className="logout-icon" onClick={logout}><LogOut size={13} /></button>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <span className="domain-badge">
            {dm.icon} {dm.name}
          </span>
          <span className="conv-meta">
            {activeConvId ? `conv: ${activeConvId.slice(0, 8)}…` : "new conversation"}
          </span>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">{dm.icon}</div>
              <h2>{dm.name} is ready</h2>
              <p>Ask anything about your {domain === "general" ? "work" : domain} operations.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.role}`}>
              {msg.role === "assistant" && (
                <div className="msg-avatar bot"><Bot size={14} /></div>
              )}
              <div className={`bubble ${msg.role}`}>
                {msg.role === "assistant" ? (
                  <div className="md-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  msg.content
                )}
                {msg.isStreaming && <span className="cursor" />}
              </div>
              {msg.role === "user" && (
                <div className="msg-avatar user"><User size={14} /></div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="input-wrap">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${dm.name}…`}
              rows={1}
              disabled={isStreaming}
            />
            <button
              onClick={isStreaming ? () => abortRef.current?.() : sendMessage}
              disabled={!input.trim() && !isStreaming}
              className={`send-btn ${isStreaming ? "stop" : ""}`}
            >
              {isStreaming
                ? <Loader2 size={16} className="spin" />
                : <Send size={15} />}
            </button>
          </div>
          <p className="footer-note">
            POWERED BY <span>SHIVANCHAL CONSULTANTS</span>
          </p>
        </div>
      </main>

      <style jsx>{`
        .dash-root {
          display: flex;
          height: 100vh;
          background: #08080c;
          color: #e8e8ef;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .sidebar {
          width: 260px;
          display: flex;
          flex-direction: column;
          background: #0d0d14;
          border-right: 0.5px solid rgba(255,255,255,0.07);
        }
        .logo-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 18px 16px;
          border-bottom: 0.5px solid rgba(255,255,255,0.07);
        }
        .logo-box {
          width: 34px; height: 34px;
          border-radius: 10px;
          background: linear-gradient(145deg, #1a1530, #0d0a1a);
          display: flex; align-items: center; justify-content: center;
          border: 0.5px solid rgba(167,139,250,0.3);
        }
        .logo-text {
          font-weight: 600;
          letter-spacing: 3px;
          font-size: 15px;
          background: linear-gradient(90deg, #e9d5ff, #a78bfa);
          -webkit-background-clip: text; background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .new-btn {
          margin: 14px 12px 8px;
          display: flex; align-items: center; justify-content: center;
          gap: 6px;
          background: linear-gradient(90deg, #7c3aed, #6366f1);
          border: none;
          color: #fff;
          font-size: 13px;
          padding: 10px;
          border-radius: 10px;
          cursor: pointer;
        }
        .change-sector {
          margin: 0 12px 8px;
          display: flex; align-items: center; justify-content: center;
          gap: 6px;
          background: rgba(255,255,255,0.04);
          border: 0.5px solid rgba(255,255,255,0.1);
          color: #a78bfa;
          font-size: 12px;
          padding: 8px;
          border-radius: 10px;
          cursor: pointer;
        }
        .change-sector:hover { background: rgba(124,58,237,0.12); }
        .conv-list {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }
        .empty-hint {
          font-size: 12px;
          color: #5a5a6e;
          text-align: center;
          margin-top: 20px;
        }
        .conv-item {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 9px 12px;
          border-radius: 9px;
          font-size: 13px;
          color: #9999a8;
          background: none;
          border: none;
          cursor: pointer;
          text-align: left;
        }
        .conv-item:hover { background: rgba(255,255,255,0.05); color: #fff; }
        .conv-item.active { background: rgba(124,58,237,0.15); color: #fff; }
        .conv-title {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .conv-del {
          opacity: 0;
          margin-left: 8px;
          color: #6b6b7e;
        }
        .conv-item:hover .conv-del { opacity: 1; }
        .conv-del:hover { color: #f09595; }
        .user-row {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          border-top: 0.5px solid rgba(255,255,255,0.07);
        }
        .avatar {
          width: 28px; height: 28px;
          border-radius: 50%;
          background: linear-gradient(145deg, #7c3aed, #4338ca);
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; font-weight: 500; color: #fff;
        }
        .user-email {
          flex: 1;
          font-size: 12px;
          color: #8b8b9e;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .logout-icon {
          background: none; border: none;
          color: #6b6b7e; cursor: pointer;
          display: flex;
        }
        .logout-icon:hover { color: #fff; }
        .chat-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .chat-header {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px 24px;
          border-bottom: 0.5px solid rgba(255,255,255,0.07);
          background: #0d0d14;
        }
        .domain-badge {
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 13px;
          font-weight: 500;
          color: #c4b5fd;
          background: rgba(124,58,237,0.15);
          padding: 6px 12px;
          border-radius: 10px;
        }
        .conv-meta {
          font-size: 11px;
          color: #5a5a6e;
        }
        .messages {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 18px;
        }
        .empty-state {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
        }
        .empty-icon {
          width: 60px; height: 60px;
          border-radius: 18px;
          background: rgba(124,58,237,0.15);
          display: flex; align-items: center; justify-content: center;
          color: #a78bfa;
          margin-bottom: 16px;
        }
        .empty-state h2 {
          font-size: 20px;
          font-weight: 500;
          color: #fff;
          margin: 0 0 8px;
        }
        .empty-state p {
          font-size: 14px;
          color: #8b8b9e;
          margin: 0;
        }
        .msg-row {
          display: flex;
          gap: 10px;
        }
        .msg-row.user { justify-content: flex-end; }
        .msg-avatar {
          width: 32px; height: 32px;
          border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
        }
        .msg-avatar.bot {
          background: linear-gradient(145deg, #7c3aed, #4338ca);
          color: #fff;
        }
        .msg-avatar.user {
          background: rgba(255,255,255,0.08);
          color: #c4b5fd;
        }
        .bubble {
          max-width: 620px;
          padding: 12px 16px;
          border-radius: 16px;
          font-size: 14px;
          line-height: 1.65;
          white-space: pre-wrap;
        }
        .bubble.user {
          background: linear-gradient(135deg, #7c3aed, #6366f1);
          color: #fff;
          border-top-right-radius: 4px;
        }
        .bubble.assistant {
          background: rgba(255,255,255,0.05);
          color: #e8e8ef;
          border-top-left-radius: 4px;
        }
        .cursor {
          display: inline-block;
          width: 7px; height: 15px;
          background: #a78bfa;
          margin-left: 3px;
          border-radius: 2px;
          animation: blink 1s steps(2) infinite;
          vertical-align: middle;
        }
        @keyframes blink { 0%,50% { opacity: 1; } 51%,100% { opacity: 0; } }
        .input-area {
          padding: 16px 24px;
          border-top: 0.5px solid rgba(255,255,255,0.07);
          background: #0d0d14;
        }
        .input-wrap {
          display: flex;
          align-items: flex-end;
          gap: 12px;
          max-width: 820px;
          margin: 0 auto;
        }
        .input-wrap textarea {
          flex: 1;
          resize: none;
          background: rgba(255,255,255,0.04);
          border: 0.5px solid rgba(255,255,255,0.1);
          border-radius: 14px;
          padding: 13px 16px;
          color: #fff;
          font-size: 14px;
          font-family: inherit;
          outline: none;
          max-height: 140px;
          min-height: 48px;
        }
        .input-wrap textarea:focus {
          border-color: rgba(167,139,250,0.5);
          background: rgba(124,58,237,0.06);
        }
        .input-wrap textarea::placeholder { color: #5a5a6e; }
        .send-btn {
          width: 48px; height: 48px;
          border-radius: 14px;
          border: none;
          background: linear-gradient(135deg, #7c3aed, #6366f1);
          color: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .send-btn.stop { background: #dc2626; }
        .spin { animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .md-content :global(p) { margin: 0 0 10px; }
        .md-content :global(p:last-child) { margin-bottom: 0; }
        .md-content :global(h1),
        .md-content :global(h2),
        .md-content :global(h3) {
          font-size: 15px;
          font-weight: 600;
          color: #c4b5fd;
          margin: 14px 0 8px;
        }
        .md-content :global(ul),
        .md-content :global(ol) {
          margin: 8px 0;
          padding-left: 20px;
        }
        .md-content :global(li) { margin: 4px 0; }
        .md-content :global(strong) {
          color: #fff;
          font-weight: 600;
        }
        .md-content :global(code) {
          background: rgba(124,58,237,0.2);
          padding: 2px 6px;
          border-radius: 5px;
          font-size: 13px;
          font-family: monospace;
        }
        .md-content :global(pre) {
          background: rgba(0,0,0,0.3);
          padding: 12px;
          border-radius: 10px;
          overflow-x: auto;
          margin: 10px 0;
        }
        .md-content :global(pre code) { background: none; padding: 0; }
        .md-content :global(table) {
          border-collapse: collapse;
          width: 100%;
          margin: 10px 0;
          font-size: 13px;
        }
        .md-content :global(th),
        .md-content :global(td) {
          border: 0.5px solid rgba(255,255,255,0.15);
          padding: 6px 10px;
          text-align: left;
        }
        .md-content :global(th) { background: rgba(124,58,237,0.15); }
        .md-content :global(a) { color: #a78bfa; }
        .md-content :global(blockquote) {
          border-left: 3px solid #7c3aed;
          padding-left: 12px;
          margin: 10px 0;
          color: #b8b8c8;
        }
        .footer-note {
          text-align: center;
          margin: 10px 0 0;
          font-size: 10px;
          color: #5a5a6e;
          letter-spacing: 1.5px;
        }
        .footer-note span { color: #a78bfa; }
      `}</style>
    </div>
  );
}
