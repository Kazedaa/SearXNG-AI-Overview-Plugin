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
        "CRITICAL: NEVER output your thought process, internal monologue, or planning.",
        "CRITICAL: NEVER converse with the user, greet them, or reference previous questions (e.g., NEVER say 'You previously asked...').",
        "Be extremely direct. Start your answer immediately. Do not use phrases like 'Based on the context'.",
        "Synthesize the provided sources into a high-density, 1-2 paragraph response.",
        "MANDATORY: Cite your sources inline using [1], [2], etc., matching the source numbers.",
        "If the context lacks the answer, use general knowledge and cite as [*].",
        "Never use markdown headers. Use bold text and lists.",
    ]

    # --- Task directive ---
    if prev_answer:
        task = "FOLLOW-UP TASK: Answer the NEW USER QUERY using the CONTEXT and HISTORY. DO NOT summarize the history."
    else:
        task = "PRIMARY TASK: Answer the USER QUERY directly."

    # --- Assemble instructions ---
    instructions = [task] + rules
    if not context:
        instructions.append("No context provided. Rely entirely on general knowledge and cite as [*].")

    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(instructions))

    user_content = f"""=== CONTEXT ===
{context or 'None.'}

=== HISTORY ===
{prev_answer or 'None.'}

=== NEW USER QUERY ===
{query}

=== INSTRUCTIONS ===
{numbered}

Output ONLY the final answer. No thoughts, no chat:"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
