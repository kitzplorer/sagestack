---
name: LLM Fallback Chain
version: 1.0.0
description: "Automatically chains LLM providers so when one fails or hits rate limits, the next picks up. Zero downtime for AI workflows. Use when you need resilient LLM calls across Anthropic, OpenAI, Groq, Ollama, and LM Studio."
---
# LLM Fallback Chain

Automatically chains LLM providers so when one fails or runs out of
tokens, the next one picks up. Zero downtime for your AI workflows.

## Chain Order (configurable)

1. Anthropic Claude (primary)
2. OpenAI GPT (fallback 1)
3. Groq (fallback 2 — fast + free tier)
4. Ollama local (fallback 3 — always available)
5. LM Studio local (fallback 4)

## Usage

```bash
# Check all providers
python3 skills/llm-fallback/scripts/llm_fallback.py status

# Send a message through the chain
python3 skills/llm-fallback/scripts/llm_fallback.py ask "explain async/await"

# Test all providers
python3 skills/llm-fallback/scripts/llm_fallback.py test

# Configure chain order
python3 skills/llm-fallback/scripts/llm_fallback.py config
```

## Configuration

```bash
LLM_CHAIN_ORDER=anthropic,openai,groq,ollama,lmstudio
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GROQ_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
LMSTUDIO_BASE_URL=http://localhost:1234
```

## Events Published

- `llm.provider.failed` — provider error with reason
- `llm.fallback.activated` — switched to next provider
- `llm.chain.exhausted` — all providers failed

## Programmatic use

```python
from llm_fallback import FallbackChain

chain = FallbackChain()
response = await chain.chat(
    messages=[{"role": "user", "content": "Hello"}],
    task_class="summarize_short"  # optional routing hint
)
print(response.text, "via", response.provider)
```
