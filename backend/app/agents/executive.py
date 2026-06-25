from app.agents.base import BaseAgent
from app.agents.domains import get_domain_prompt


class ExecutiveAssistantAgent(BaseAgent):
    """
    TITAN's primary agent, now domain-aware.
    Transforms into a sector expert based on the active domain.
    """

    def __init__(self, domain: str = "general"):
        self.domain = domain

    @property
    def name(self) -> str:
        return "executive_assistant"

    @property
    def role_description(self) -> str:
        return "A domain-specialized AI assistant for business operations."

    @property
    def allowed_tools(self) -> list:
        return ["web_search", "send_email", "read_document"]

    @property
    def default_task_type(self) -> str:
        return "reasoning"

    def build_system_prompt(self, context: dict) -> str:
        user_facts = context.get("user_facts", "")
        relevant_knowledge = context.get("relevant_knowledge", [])

        domain_prompt = get_domain_prompt(self.domain)

        knowledge_text = ""
        if relevant_knowledge:
            snippets = []
            for i, k in enumerate(relevant_knowledge[:3]):
                if k.get("score", 0) > 0.5:
                    snippets.append(f"[{i+1}] {k['content'][:300]}")
            if snippets:
                knowledge_text = "Relevant context:\n" + "\n".join(snippets)

        return f"""{domain_prompt}

USER CONTEXT
{user_facts if user_facts else "Learning your preferences as we work together."}

RELEVANT KNOWLEDGE
{knowledge_text if knowledge_text else "No prior context found yet."}

AVAILABLE TOOLS
- web_search: search the internet for current information
- send_email: send emails via Resend
- read_document: extract text from PDF or DOCX files

Use tools proactively when they improve your response quality."""


# Default agent (general domain)
executive_agent = ExecutiveAssistantAgent()


def get_agent_for_domain(domain: str = "general") -> ExecutiveAssistantAgent:
    """Factory: returns an agent specialized for the given domain."""
    return ExecutiveAssistantAgent(domain=domain)
