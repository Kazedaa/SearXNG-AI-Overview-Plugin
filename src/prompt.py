"""System prompt and prompt assembly for AI Overview."""

import time

from .config import Config


def build_prompt(
    query: str,
    context: str,
    config: Config,
    lang: str = "all",
    prev_answer: str | None = None,
) -> list[dict]:
    """Build the messages list for the Ollama chat API.

    Returns a list of message dicts in the format:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    today = time.strftime("%Y-%m-%d")

    lang_instruction = f" Respond in {lang}." if lang not in ("all", "auto") else ""

    system_content = (
        "You are an expert search assistant. Your task is to provide a direct, concise, and accurate answer based ONLY on the provided context."
        f"\nToday is {today}.{lang_instruction}"
    )

    # --- Core rules as a proper list ---
    rules = [
        "Be extremely direct. Start your answer immediately. Do not use phrases like 'Based on the context' or 'Here is the answer.'",
        "Synthesize the provided sources into a high-density, 1-2 paragraph response.",
        "MANDATORY: Cite your sources inline using [1], [2], etc., matching the source numbers provided.",
        "If the context does not contain the answer, rely on your general knowledge but state that you are doing so, and cite as [*].",
        "Never use markdown headers. Use bold text, lists, and inline code formatting where appropriate.",
        "Keep it professional and objective.",
    ]

    # --- Task directive ---
    if prev_answer:
        task = "FOLLOW-UP: The user is asking a follow-up question. Answer it using the new context and conversation history."
    else:
        task = "PRIMARY TASK: Answer the user's query directly."

    # --- Assemble instructions ---
    instructions = [task] + rules
    if not context:
        instructions.append("No context provided. Rely entirely on general knowledge and cite as [*].")

    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(instructions))

    user_content = f"""CONVERSATION HISTORY:
{prev_answer or 'None.'}

SEARCH CONTEXT (SOURCES):
{context or 'None.'}

USER QUERY: {query}

INSTRUCTIONS:
{numbered}

Now, write your response:"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
