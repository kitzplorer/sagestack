---
name: LLM Fallback Chain
version: 1.0.0
description: "Automatically chains LLM providers so when one fails or runs out of"
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

## Events Published

- `llm.provider.failed` — provider error with reason
- `llm.fallback.activated` — switched to next provider
- `llm.chain.exhausted` — all providers failed
