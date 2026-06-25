const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  id: string; email: string; full_name: string | null;
  role: "admin" | "user" | "viewer"; is_active: boolean; created_at: string;
}
export interface AuthTokens {
  access_token: string; refresh_token: string;
  token_type: string; expires_in: number; user: User;
}
export interface Conversation {
  id: string; title: string; created_at: string; updated_at: string;
}
export interface Domain {
  key: string; name: string; icon: string; tagline: string;
}
export interface FilePayload {
  filename: string; content_base64: string; mime_type: string;
  description: string; rows_count: number;
}

export const tokenStorage = {
  getAccess: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem("titan_access_token") : null,
  getRefresh: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem("titan_refresh_token") : null,
  set: (t: Pick<AuthTokens, "access_token" | "refresh_token">) => {
    localStorage.setItem("titan_access_token", t.access_token);
    localStorage.setItem("titan_refresh_token", t.refresh_token);
  },
  clear: () => {
    localStorage.removeItem("titan_access_token");
    localStorage.removeItem("titan_refresh_token");
  },
};

export const domainStorage = {
  get: (): string =>
    typeof window !== "undefined"
      ? localStorage.getItem("titan_domain") || "general"
      : "general",
  set: (d: string) => localStorage.setItem("titan_domain", d),
  clear: () => localStorage.removeItem("titan_domain"),
};

// Auto-logout helper
function handleUnauthorized() {
  tokenStorage.clear();
  domainStorage.clear();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

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

  // Auto logout on 401
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please login again.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

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
    domainStorage.clear();
  },
};

export interface ChatStreamOptions {
  message: string;
  conversation_id?: string;
  use_tools?: boolean;
  domain?: string;
  onChunk: (text: string) => void;
  onFile?: (payload: FilePayload) => void;
  onDone: (conversation_id: string) => void;
  onError: (error: string) => void;
}

export const chatApi = {
  getDomains: () =>
    apiFetch<{ domains: Domain[] }>("/chat/domains", {}, false),

  getMessages: (id: string) =>
    apiFetch<{ messages: { role: string; content: string }[] }>(
      `/chat/conversations/${id}/messages`
    ),

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
        domain: opts.domain ?? "general",
      }),
      signal: controller.signal,
    }).then(async (res) => {
      // Handle 401 in streaming too
      if (res.status === 401) {
        handleUnauthorized();
        opts.onError("Session expired. Redirecting to login...");
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      let currentConvId = opts.conversation_id || "";
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
              const parsed = JSON.parse(raw);
              if (parsed.type === "chunk" && parsed.text) {
                opts.onChunk(parsed.text.replace(/\\n/g, "\n"));
              } else if (parsed.type === "file" && parsed.payload) {
                opts.onFile?.(parsed.payload);
              } else if (parsed.type === "start" && parsed.conversation_id) {
                currentConvId = parsed.conversation_id;
              } else if (parsed.type === "done") {
                opts.onDone(currentConvId);
              } else if (parsed.type === "error") {
                opts.onError(parsed.message || "Unknown error");
              }
            } catch (_) {}
          }
        }
      }
    }).catch((err) => {
      if (err.name !== "AbortError") opts.onError(err.message);
    });

    return () => controller.abort();
  },

  listConversations: () =>
    apiFetch<Conversation[]>("/chat/conversations"),

  deleteConversation: (id: string) =>
    apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }),
};
