"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Send, Plus, Trash2, Bot, User, LogOut,
  Loader2, HeartPulse, Server, School, Sparkles, Repeat,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatApi, authApi, tokenStorage, domainStorage, type Conversation } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

const DOMAIN_META: Record<string, { name: string; icon: React.ReactNode; color: string }> = {
  healthcare: { name: "Healthcare OS", icon: <HeartPulse size={14} />, color: "#a78bfa" },
  it:         { name: "IT Operations OS", icon: <Server size={14} />, color: "#a78bfa" },
  education:  { name: "Education OS", icon: <School size={14} />, color: "#a78bfa" },
  general:    { name: "General", icon: <Sparkles size={14} />, color: "#a78bfa" },
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
    const d = domainStorage.get();
    setDomain(d);
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

  async function newConversation() {
    setActiveConvId(null);
    setMessages([]);
    await loadConversations();
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
    if (activeConvId === id) { setActiveConvId(null); setMessages([]); }
  }

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    const userMsgId = crypto.randomUUID();
    const asstMsgId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: text },
      { id: asstMsgId, role: "assistant", content: "", isStreaming: true },
    ]);
    setIsStreaming(true);

    abortRef.current = chatApi.stream({
      message: text,
      conversation_id: activeConvId ?? undefined,
      use_tools: false,
      domain,
      onChunk: (chunk) => {
        setMessages((prev) =>
          prev.map((m) => m.id === asstMsgId ? { ...m, content: m.content + chunk } : m)
        );
      },
      onDone: (convId) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) => m.id === asstMsgId ? { ...m, isStreaming: false } : m)
        );
        if (!activeConvId) setActiveConvId(convId);
        loadConversations();
      },
      onError: (err) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId ? { ...m, content: `⚠️ Error: ${err}`, isStreaming: false } : m
          )
        );
      },
    });
  }, [input, isStreaming, activeConvId, domain]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  async function logout() {
    await authApi.logout();
    router.push("/login");
  }

  const dm = DOMAIN_META[domain] || DOMAIN_META.general;

  return (
    <div style={{ display:"flex", height:"100vh", background:"#08080c", color:"#e8e8ef",
      fontFamily:"-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", overflow:"hidden" }}>

      {/* ── Sidebar ── */}
      <aside style={{ width:260, display:"flex", flexDirection:"column",
        background:"#0d0d14", borderRight:"0.5px solid rgba(255,255,255,0.07)", flexShrink:0 }}>

        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:10, padding:"16px",
          borderBottom:"0.5px solid rgba(255,255,255,0.07)" }}>
          <div style={{ width:34, height:34, borderRadius:10, display:"flex",
            alignItems:"center", justifyContent:"center",
            background:"linear-gradient(145deg,#1a1530,#0d0a1a)",
            border:"0.5px solid rgba(167,139,250,0.3)" }}>
            <svg width="20" height="20" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="lg" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
                  <stop offset="0" stopColor="#c4b5fd"/>
                  <stop offset="1" stopColor="#6d28d9"/>
                </linearGradient>
              </defs>
              <path d="M50 10L86 30L86 70L50 90L14 70L14 30Z" fill="none" stroke="url(#lg)" strokeWidth="4" strokeLinejoin="round"/>
              <path d="M36 40L64 40M50 40L50 68" fill="none" stroke="url(#lg)" strokeWidth="8" strokeLinecap="round"/>
            </svg>
          </div>
          <span style={{ fontWeight:600, letterSpacing:3, fontSize:15,
            background:"linear-gradient(90deg,#e9d5ff,#a78bfa)",
            WebkitBackgroundClip:"text", backgroundClip:"text", WebkitTextFillColor:"transparent" }}>
            TITAN
          </span>
        </div>

        {/* Buttons */}
        <div style={{ padding:"12px 12px 4px" }}>
          <button onClick={newConversation} style={{ width:"100%", display:"flex",
            alignItems:"center", justifyContent:"center", gap:6,
            background:"linear-gradient(90deg,#7c3aed,#6366f1)", border:"none",
            color:"#fff", fontSize:13, padding:"10px", borderRadius:10,
            cursor:"pointer", marginBottom:8 }}>
            <Plus size={14}/> New conversation
          </button>
          <button onClick={() => router.push("/select")} style={{ width:"100%",
            display:"flex", alignItems:"center", justifyContent:"center", gap:6,
            background:"rgba(255,255,255,0.04)", border:"0.5px solid rgba(255,255,255,0.1)",
            color:"#a78bfa", fontSize:12, padding:"8px", borderRadius:10, cursor:"pointer" }}>
            <Repeat size={13}/> Change sector
          </button>
        </div>

        {/* Conversation list */}
        <div style={{ flex:1, overflowY:"auto", padding:"8px" }}>
          {conversations.length === 0 && (
            <p style={{ fontSize:12, color:"#5a5a6e", textAlign:"center", marginTop:20 }}>
              No conversations yet.
            </p>
          )}
          {conversations.map((conv) => (
            <button key={conv.id} onClick={() => selectConversation(conv)}
              style={{ width:"100%", display:"flex", alignItems:"center",
                justifyContent:"space-between", padding:"9px 12px", borderRadius:9,
                fontSize:13, textAlign:"left", cursor:"pointer", border:"none",
                background: activeConvId === conv.id ? "rgba(124,58,237,0.2)" : "transparent",
                color: activeConvId === conv.id ? "#fff" : "#9999a8",
                marginBottom:2 }}>
              <span style={{ flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {conv.title || "Untitled"}
              </span>
              <span onClick={(e) => deleteConversation(conv.id, e)}
                style={{ marginLeft:8, color:"#6b6b7e", flexShrink:0,
                  display:"flex", alignItems:"center" }}>
                <Trash2 size={12}/>
              </span>
            </button>
          ))}
        </div>

        {/* User row */}
        <div style={{ display:"flex", alignItems:"center", gap:8, padding:12,
          borderTop:"0.5px solid rgba(255,255,255,0.07)" }}>
          <div style={{ width:28, height:28, borderRadius:"50%", flexShrink:0,
            background:"linear-gradient(145deg,#7c3aed,#4338ca)",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:12, fontWeight:500, color:"#fff" }}>
            {userEmail.charAt(0).toUpperCase()}
          </div>
          <span style={{ flex:1, fontSize:12, color:"#8b8b9e", overflow:"hidden",
            textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{userEmail}</span>
          <button onClick={logout} style={{ background:"none", border:"none",
            color:"#6b6b7e", cursor:"pointer", display:"flex", alignItems:"center" }}>
            <LogOut size={13}/>
          </button>
        </div>
      </aside>

      {/* ── Main Chat ── */}
      <main style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

        {/* Header */}
        <header style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 24px",
          borderBottom:"0.5px solid rgba(255,255,255,0.07)", background:"#0d0d14", flexShrink:0 }}>
          <span style={{ display:"flex", alignItems:"center", gap:7, fontSize:13,
            fontWeight:500, color:"#c4b5fd",
            background:"rgba(124,58,237,0.15)", padding:"6px 12px", borderRadius:10 }}>
            {dm.icon} {dm.name}
          </span>
          <span style={{ fontSize:11, color:"#5a5a6e" }}>
            {activeConvId ? `conv: ${activeConvId.slice(0,8)}…` : "new conversation"}
          </span>
        </header>

        {/* Messages */}
        <div style={{ flex:1, overflowY:"auto", padding:"24px", display:"flex",
          flexDirection:"column", gap:16 }}>

          {messages.length === 0 && (
            <div style={{ flex:1, display:"flex", flexDirection:"column",
              alignItems:"center", justifyContent:"center", textAlign:"center",
              minHeight:"60vh" }}>
              <div style={{ width:60, height:60, borderRadius:18, marginBottom:16,
                background:"rgba(124,58,237,0.15)", display:"flex",
                alignItems:"center", justifyContent:"center", color:"#a78bfa", fontSize:28 }}>
                {dm.icon}
              </div>
              <h2 style={{ fontSize:20, fontWeight:500, color:"#fff", margin:"0 0 8px" }}>
                {dm.name} is ready
              </h2>
              <p style={{ fontSize:14, color:"#8b8b9e", margin:0 }}>
                Ask anything about your {domain === "general" ? "work" : domain} operations.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} style={{ display:"flex", gap:10,
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>

              {msg.role === "assistant" && (
                <div style={{ width:32, height:32, borderRadius:10, flexShrink:0,
                  background:"linear-gradient(145deg,#7c3aed,#4338ca)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  color:"#fff", marginTop:4 }}>
                  <Bot size={14}/>
                </div>
              )}

              <div style={{
                maxWidth:680, padding:"12px 16px", borderRadius:16, fontSize:14,
                lineHeight:1.65,
                ...(msg.role === "user" ? {
                  background:"linear-gradient(135deg,#7c3aed,#6366f1)",
                  color:"#fff", borderTopRightRadius:4,
                } : {
                  background:"rgba(255,255,255,0.05)",
                  color:"#e8e8ef", borderTopLeftRadius:4,
                })
              }}>
                {msg.role === "assistant" ? (
                  <div style={{ lineHeight:1.7 }}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({children}) => <h1 style={{fontSize:16,fontWeight:600,color:"#c4b5fd",margin:"8px 0 4px"}}>{children}</h1>,
                        h2: ({children}) => <h2 style={{fontSize:15,fontWeight:600,color:"#c4b5fd",margin:"8px 0 4px"}}>{children}</h2>,
                        h3: ({children}) => <h3 style={{fontSize:14,fontWeight:600,color:"#c4b5fd",margin:"6px 0 3px"}}>{children}</h3>,
                        p:  ({children}) => <p style={{margin:"0 0 4px"}}>{children}</p>,
                        ul: ({children}) => <ul style={{paddingLeft:20,margin:"4px 0"}}>{children}</ul>,
                        ol: ({children}) => <ol style={{paddingLeft:20,margin:"4px 0"}}>{children}</ol>,
                        li: ({children}) => <li style={{margin:"2px 0"}}>{children}</li>,
                        strong: ({children}) => <strong style={{color:"#fff",fontWeight:600}}>{children}</strong>,
                        code: ({children}) => <code style={{background:"rgba(124,58,237,0.2)",padding:"2px 6px",borderRadius:5,fontSize:13,fontFamily:"monospace"}}>{children}</code>,
                        pre: ({children}) => <pre style={{background:"rgba(0,0,0,0.3)",padding:12,borderRadius:10,overflowX:"auto",margin:"10px 0"}}>{children}</pre>,
                        blockquote: ({children}) => <blockquote style={{borderLeft:"3px solid #7c3aed",paddingLeft:12,margin:"10px 0",color:"#b8b8c8"}}>{children}</blockquote>,
                        table: ({children}) => <table style={{borderCollapse:"collapse",width:"100%",margin:"10px 0",fontSize:13}}>{children}</table>,
                        th: ({children}) => <th style={{border:"0.5px solid rgba(255,255,255,0.15)",padding:"6px 10px",background:"rgba(124,58,237,0.15)"}}>{children}</th>,
                        td: ({children}) => <td style={{border:"0.5px solid rgba(255,255,255,0.15)",padding:"6px 10px"}}>{children}</td>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                    {msg.isStreaming && (
                      <span style={{ display:"inline-block", width:7, height:15,
                        background:"#a78bfa", marginLeft:3, borderRadius:2,
                        animation:"blink 1s steps(2) infinite", verticalAlign:"middle" }}/>
                    )}
                  </div>
                ) : (
                  msg.content
                )}
              </div>

              {msg.role === "user" && (
                <div style={{ width:32, height:32, borderRadius:10, flexShrink:0,
                  background:"rgba(255,255,255,0.08)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  color:"#c4b5fd", marginTop:4 }}>
                  <User size={14}/>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef}/>
        </div>

        {/* Input */}
        <div style={{ padding:"14px 24px 18px", borderTop:"0.5px solid rgba(255,255,255,0.07)",
          background:"#0d0d14", flexShrink:0 }}>
          <div style={{ display:"flex", alignItems:"flex-end", gap:12,
            maxWidth:820, margin:"0 auto" }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${dm.name}…`}
              rows={1}
              disabled={isStreaming}
              style={{ flex:1, resize:"none", background:"rgba(255,255,255,0.04)",
                border:"0.5px solid rgba(255,255,255,0.1)", borderRadius:14,
                padding:"13px 16px", color:"#fff", fontSize:14, fontFamily:"inherit",
                outline:"none", maxHeight:140, minHeight:48 }}
            />
            <button
              onClick={isStreaming ? () => abortRef.current?.() : sendMessage}
              disabled={!input.trim() && !isStreaming}
              style={{ width:48, height:48, borderRadius:14, border:"none",
                background: isStreaming ? "#dc2626" : "linear-gradient(135deg,#7c3aed,#6366f1)",
                color:"#fff", cursor:"pointer", display:"flex",
                alignItems:"center", justifyContent:"center", flexShrink:0 }}>
              {isStreaming ? <Loader2 size={16} className="spin"/> : <Send size={15}/>}
            </button>
          </div>
          <p style={{ textAlign:"center", margin:"10px 0 0", fontSize:10,
            color:"#5a5a6e", letterSpacing:"1.5px" }}>
            POWERED BY <span style={{ color:"#a78bfa" }}>SHIVANCHAL CONSULTANTS</span>
          </p>
        </div>
      </main>

      <style>{`
        @keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
        .spin { animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        textarea::placeholder { color: #5a5a6e; }
        textarea:focus { border-color: rgba(167,139,250,0.5) !important;
          box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.3); border-radius: 4px; }
      `}</style>
    </div>
  );
}
