"""LLM provider factory. The provider is chosen by config, not code."""

from typing import Any

from livekit.agents import llm
from livekit.plugins import anthropic, google, openai

from babakoto_agent.config import AgentSettings


def build_llm(settings: AgentSettings) -> llm.LLM[Any]:
    """Create the LLM named in settings. A blank `LLM_MODEL` uses the plugin's default model.

    API keys come from the provider's usual environment variable (`ANTHROPIC_API_KEY`,
    `OPENAI_API_KEY`, `GOOGLE_API_KEY`); the plugins fail loudly when one is missing.
    """
    model = settings.llm_model
    provider = settings.llm_provider
    if provider == "anthropic":
        return anthropic.LLM(model=model) if model else anthropic.LLM()
    if provider == "openai":
        return openai.LLM(model=model) if model else openai.LLM()
    if provider == "google":
        return google.LLM(model=model) if model else google.LLM()
    # Any OpenAI-compatible endpoint (vLLM, Ollama, a gateway). The key may be a placeholder.
    return openai.LLM(
        model=model,
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key or "not-needed",
    )
