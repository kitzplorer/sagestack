---
version: 1.0.0
name: summarize
description: Summarize or extract text/transcripts from URLs, podcasts, and local files. Use when the user asks to summarize a URL/article/video, "what's this link about?", "transcribe this YouTube", or explicitly says "use summarize.sh".
homepage: https://summarize.sh
---

# Summarize

Fast CLI to summarize URLs, local files, and YouTube links.

## When to use

- "use summarize.sh"
- "what's this link/video about?"
- "summarize this URL/article"
- "transcribe this YouTube/video"

## Quick start

```bash
summarize "https://example.com" --model google/gemini-3-flash-preview
summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto
```

## Install

```bash
brew install steipete/tap/summarize
```

## YouTube: summary vs transcript

Best-effort transcript (URLs only):

```bash
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto --extract-only
```

If the transcript is huge, return a tight summary first, then ask which section/time range to expand.

## Model + keys

Set the API key for your chosen provider:

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY`

Default model is `google/gemini-3-flash-preview` if none is set.

## Useful flags

- `--length short|medium|long|xl|xxl|<chars>`
- `--max-output-tokens <count>`
- `--extract-only` (URLs only)
- `--json` (machine readable)
- `--firecrawl auto|off|always` (fallback extraction)
- `--youtube auto` (Apify fallback if `APIFY_API_TOKEN` set)

## Config

Optional config file: `~/.summarize/config.json`

```json
{ "model": "openai/gpt-5.2" }
```

Optional services:
- `FIRECRAWL_API_KEY` for blocked sites
- `APIFY_API_TOKEN` for YouTube fallback
