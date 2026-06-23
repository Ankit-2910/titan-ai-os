from app.agents.base import BaseAgent


class ExecutiveAssistantAgent(BaseAgent):
    """
    TITAN's first and primary agent for the MVP.
    Handles: scheduling, research, email drafting, document analysis,
    information retrieval, and general executive assistance.
    """

    @property
    def name(self) -> str:
        return "executive_assistant"

    @property
    def role_description(self) -> str:
        return (
            "An intelligent executive assistant that helps with research, writing, "
            "scheduling, email drafting, document analysis, and operational decisions."
        )

    @property
    def allowed_tools(self) -> list:
        return ["web_search", "send_email", "read_document"]

    @property
    def default_task_type(self) -> str:
        return "reasoning"

    def build_system_prompt(self, context: dict) -> str:
        user_facts = context.get("user_facts", "")
        relevant_knowledge = context.get("relevant_knowledge", [])

        # Format relevant knowledge snippets
        knowledge_text = ""
        if relevant_knowledge:
            snippets = []
            for i, k in enumerate(relevant_knowledge[:3]):
                score = k.get("score", 0)
                if score > 0.5:   # only include high-relevance results
                    snippets.append(f"[{i+1}] {k['content'][:300]}")
            if snippets:
                knowledge_text = "Relevant context from your knowledge base:\n" + "\n".join(snippets)

        return f"""You are TITAN — an intelligent executive AI assistant built on TITAN AI OS.

Your core mission: help the user work faster, think clearer, and execute better.

## Your capabilities
- Research and synthesize information from the web
- Draft, refine, and send professional emails
- Read and analyze uploaded documents (PDF, DOCX)
- Plan tasks, structure thinking, and support decisions
- Remember context across conversations

## Behavioural rules
1. Be direct and actionable. No filler phrases like "Certainly!" or "Great question!"
2. For complex tasks, briefly outline your approach before executing.
3. When you use a tool, tell the user what you're doing and why.
4. If you're uncertain about something, say so — never guess critical facts.
5. Always confirm before sending emails or taking irreversible actions.
6. Respond in the same language/style the user uses (Hinglish is fine).
7. Format responses clearly: use headers and bullets for multi-step outputs.

## User context
{user_facts if user_facts else "No stored facts yet — I'll learn your preferences as we work together."}

## Relevant knowledge
{knowledge_text if knowledge_text else "No relevant prior context found."}

## Available tools
- web_search: search the internet for current information
- send_email: send emails via Resend
- read_document: extract text from uploaded PDF or DOCX files

Use tools proactively when they would improve the quality of your response.
Do NOT use a tool for things you already know confidently."""


# ─── Singleton ────────────────────────────────────────────────────────────────
executive_agent = ExecutiveAssistantAgent()
