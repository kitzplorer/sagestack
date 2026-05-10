---
name: Local LLM Connector
version: 1.0.0
description: "Connect to self-hosted open-source LLMs running locally. Supports Ollama, LM Studio, LocalAI, and any OpenAI-compatible local server. Use for free code generation with models like CodeLlama, DeepSeek, Qwen — or for offline/air-gapped operation."
---
# Local LLM Connector

Connect to self-hosted open-source LLMs running on your machine.
Supports Ollama, LM Studio, and any OpenAI-compatible local server.

Free code generation with quality models like CodeLlama, DeepSeek, Qwen.

## Usage

```bash
# Auto-detect running LLM servers
python3 skills/local-llm-connector/scripts/local_llm.py detect

# List available models
python3 skills/local-llm-connector/scripts/local_llm.py models

# Chat with local model
python3 skills/local-llm-connector/scripts/local_llm.py chat

# Generate code
python3 skills/local-llm-connector/scripts/local_llm.py code "write a python web scraper"

# Setup guide (install Ollama + recommended models)
python3 skills/local-llm-connector/scripts/local_llm.py setup

# Health check all local LLM endpoints
python3 skills/local-llm-connector/scripts/local_llm.py health

# Start proxy server (unified API for all local models)
python3 skills/local-llm-connector/scripts/local_llm.py serve --port 8877
```

## Supported Backends

- **Ollama** — `http://localhost:11434` (recommended, easiest setup)
- **LM Studio** — `http://localhost:1234`
- **LocalAI** — `http://localhost:8080`
- **Any OpenAI-compatible** — set `LOCAL_LLM_BASE_URL`

## Recommended Models for Code

- `deepseek-coder-v2` — best free code model
- `qwen2.5-coder:7b` — fast, good quality
- `codellama:13b` — Meta's code specialist
- `starcoder2:7b` — code completion

## Quick start with Ollama

```bash
brew install ollama
ollama serve &
ollama pull deepseek-coder-v2
ollama run deepseek-coder-v2
```

## Events Published

- `local-llm.connected` — local LLM server detected
- `local-llm.model.loaded` — model pulled/loaded
