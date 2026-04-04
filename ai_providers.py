#!/usr/bin/env python3
"""Multi-provider AI abstraction for LoveSpark message generation."""

import json
import os
import urllib.request

SYSTEM_PROMPT = (
    "Tu es un ami bienveillant et empathique. Genere un message d'encouragement "
    "personnalise pour {name}. Le message doit etre:\n"
    "\n"
    "- Chaleureux et sincere (pas de cliches creux)\n"
    "- Reconnaissant des efforts invisibles que la personne fait au quotidien\n"
    "- Encourageant face aux moments difficiles (travail, tristesse, periodes compliquees)\n"
    "- Court (3-4 phrases maximum, environ 50 mots)\n"
    "- En francais, avec un ton intime et doux\n"
    "- Generique (ne presume rien de specifique sur la personne)\n"
    "- Different a chaque fois (varie le style, les metaphores, l'angle)\n"
    "\n"
    "Ne commence PAS par \"Cher/Chere {name}\" ou \"Bonjour {name}\".\n"
    "Ne mets PAS de guillemets autour du message.\n"
    "Reponds UNIQUEMENT avec le message, sans explication ni introduction."
)

FALLBACK_MESSAGE = (
    "Tout ce que tu fais en silence, ces efforts que personne ne voit, "
    "sache que quelqu'un les voit. Quelque part, il y a une personne qui "
    "tient a toi et qui souhaite ton bonheur. Cette personne, c'est celle "
    "qui t'envoie ce lien. Tu comptes plus que tu ne le crois."
)

PROVIDER_CONFIGS = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-3-haiku-20240307",
        "format": "anthropic",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "format": "openai",
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "default_model": "moonshot-v1-8k",
        "format": "openai",
    },
}


def get_ai_message(name: str) -> str:
    """Generate an inspirational message for the given name using the configured AI provider."""
    provider = os.environ.get("AI_PROVIDER", "").lower().strip()
    api_key = os.environ.get("AI_API_KEY", "").strip()
    model = os.environ.get("AI_MODEL", "").strip()

    if not provider or not api_key:
        return FALLBACK_MESSAGE

    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return FALLBACK_MESSAGE

    if not model:
        model = config["default_model"]

    prompt = SYSTEM_PROMPT.replace("{name}", name)

    try:
        if config["format"] == "anthropic":
            return _call_anthropic(config["url"], api_key, model, name, prompt)
        return _call_openai_compatible(config["url"], api_key, model, prompt)
    except Exception:
        return FALLBACK_MESSAGE


def _call_anthropic(url: str, api_key: str, model: str, name: str, system_prompt: str) -> str:
    """Call the Anthropic Messages API."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 200,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": f"Genere un message d'encouragement pour {name}."}
        ],
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["content"][0]["text"].strip()


def _call_openai_compatible(url: str, api_key: str, model: str, system_prompt: str) -> str:
    """Call an OpenAI-compatible Chat Completions API (OpenAI, Kimi, etc.)."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 200,
        "temperature": 0.9,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Genere un message d'encouragement."},
        ],
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
