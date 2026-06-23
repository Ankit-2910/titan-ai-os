// lib/api.ts — Typed API client for TITAN AI OS backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "user" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SSEChunk {
  type: "chunk" | "start" | "done" | "error";
  text?: string;
  conversation_id?: string;
  message?: string;
}

// ─── Token Storage ────────────────────────────────────────────────────────────

export const tokenStorage = {
  getAccess: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem("titan_access_token") : null,

  getRefresh: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem("titan_refresh_token") : null,

  set: (tokens: Pick<AuthTokens, "access_token" | "refresh_token">) => {
    localStorage.setItem("titan_access_token", tokens.access_token);
    localStorage.setItem("titan_refresh_token", tokens.refresh_token);
  },

  clear: () => {
    localStorage.removeItem("titan_access_token");
    localStorage.removeItem("titan_refresh_token");
  },
};

// ─── Fetch Helper ─────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  withAuth = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (withAuth) {
    const token = tokenStorage.getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    apiFetch<AuthTokens>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }, false),

  login: (email: string, password: string) =>
    apiFetch<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, false),

  me: () => apiFetch<User>("/auth/me"),

  logout: async () => {
    const refresh_token = tokenStorage.getRefresh();
    if (refresh_token) {
      await apiFetch("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }).catch(() => {});
    }
    tokenStorage.clear();
  },
};

// ─── Chat API ─────────────────────────────────────────────────────────────────

export interface ChatStreamOptions {
  message: string;
  conversation_id?: string;
  use_tools?: boolean;
  onChunk: (text: string) => void;
  onDone: (conversation_id: string) => void;
  onError: (error: string) => void;
}

export const chatApi = {
  /**
   * Send a message and stream back the response via SSE.
   * Returns a function to abort the stream.
   */
  stream: (opts: ChatStreamOptions): (() => void) => {
    const controller = new AbortController();

    const token = tokenStorage.getAccess();

    fetch(`${API_BASE}/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: opts.message,
        conversation_id: opts.conversation_id,
        use_tools: opts.use_tools ?? true,
      }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error("No response body");

        let currentConversationId = opts.conversation_id || "";

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const raw = line.slice(6).trim();
              if (!raw) continue;
              try {
                const parsed: SSEChunk = JSON.parse(raw);

                if (parsed.type === "chunk" && parsed.text) {
                  // Unescape newlines we escaped on the server side
                  opts.onChunk(parsed.text.replace(/\\n/g, "\n"));
                } else if (parsed.type === "start" && parsed.conversation_id) {
                  currentConversationId = parsed.conversation_id;
                } else if (parsed.type === "done") {
                  opts.onDone(currentConversationId);
                } else if (parsed.type === "error") {
                  opts.onError(parsed.message || "Unknown error");
                }
              } catch (_) {
                // malformed JSON — skip
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          opts.onError(err.message);
        }
      });

    return () => controller.abort();
  },

  listConversations: () =>
    apiFetch<Conversation[]>("/chat/conversations"),

  deleteConversation: (id: string) =>
    apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }),
};
