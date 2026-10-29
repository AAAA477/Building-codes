"""Thin LLM interface. Real Anthropic client only if ANTHROPIC_API_KEY is set and the
`anthropic` package is installed; otherwise a deterministic offline fallback.
Every result is a draft: callers label it provenance 'ai_draft'."""
from __future__ import annotations
import os, re

import privacy, ratelimit


class OfflineLLM:
    name = "offline"

    def explain_article(self, article: str, intent: str = "", objective: str = "", function: str = "") -> str:
        """Deterministic explainer assembled only from lookup text. No new facts."""
        parts = [f"Article {article} is cited as part of the acceptable solution being varied."]
        if objective:
            parts.append(f"Its attributed objective(s): {objective}.")
        if function:
            parts.append(f"Attributed function(s): {function}.")
        if intent:
            parts.append(f"Stated intent: {intent}")
        if not (objective or function or intent):
            parts.append("No attributed objective, function or intent was resolved from the code; confirm against the code text.")
        parts.append("Draft for the applicant to confirm; it makes no statement about safety or equivalence.")
        return " ".join(parts)

    def chat_text(self, prompt: str):
        return None

    def chat_json(self, prompt: str, schema_hint: str = ""):
        return None

    def expand_query(self, query: str) -> str:
        """Offline: no rewriting."""
        return ""

    def extract_facts(self, text: str) -> dict:
        """Regex extraction of explicit facts only. Returns {field_path: (value, confidence)}."""
        out = {}
        t = text or ""
        m = re.search(r"(\d+)[\s-]*(?:storey|story|floor)s?", t, re.I)
        if m:
            out["project.storeys"] = (int(m.group(1)), 0.6)
        m = re.search(r"([\d,\.]+)\s*(?:m2|m²|sq\.?\s*m|square met)", t, re.I)
        if m:
            try:
                out["project.building_area_m2"] = (float(m.group(1).replace(",", "")), 0.6)
            except ValueError:
                pass
        m = re.search(r"(\d+)\s*(?:units?|suites?|apartments?)\s*(?:per|each|/)\s*(?:floor|storey|level)", t, re.I)
        if m:
            out["project.units_per_floor"] = (int(m.group(1)), 0.6)
        if re.search(r"\b(not sprinklered|unsprinklered|no sprinklers?)\b", t, re.I):
            out["project.sprinklered"] = (False, 0.6)
        elif re.search(r"\bsprinklered|sprinkler system\b", t, re.I):
            out["project.sprinklered"] = (True, 0.5)
        if re.search(r"\brenovat|retrofit|conversion\b", t, re.I):
            out["project.new_or_renovation"] = ("renovation", 0.5)
        return out


class _ChatLLM(OfflineLLM):
    """Shared drafting prompt for hosted models. Subclasses implement `_ask`; any failure returns the
    deterministic fallback text, so the app never breaks when the network or key is wrong."""
    last_error: str = ""

    def _ask(self, prompt: str, fallback: str) -> str:  # pragma: no cover - overridden
        return fallback

    def expand_query(self, query: str) -> str:
        prompt = ("A builder typed this plain-language question about building, fire, plumbing or energy codes: "
                  f"\"{query}\"\nReply with 3 to 5 keywords (words only, space separated, no numbers, no article "
                  "numbers) that the Canadian model codes (NBC, NFC, NPC, NECB) would use for this topic.")
        return self._ask(prompt, "")

    def explain_article(self, article, intent="", objective="", function=""):
        base = super().explain_article(article, intent, objective, function)
        prompt = ("Write one plain-language paragraph (max 80 words) explaining what building code article "
                  f"{article} is for, using ONLY these facts. Do not add facts, do not say any design is safe "
                  f"or equivalent.\nObjective: {objective}\nFunction: {function}\nIntent: {intent}")
        return self._ask(prompt, base)

    # ---- generic helpers used by suggest.py (return None on any failure) ----
    def chat_text(self, prompt: str):
        out = self._ask(prompt, "")
        return out or None

    def chat_json(self, prompt: str, schema_hint: str = ""):
        import json as _json
        hint = (" Reply with JSON only. Shape: " + schema_hint) if schema_hint else " Reply with JSON only."
        raw = self._ask(prompt + hint, "")
        if not raw:
            return None
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
        try:
            return _json.loads(raw)
        except ValueError:
            m = re.search(r"[\[{].*[\]}]", raw, re.S)
            try:
                return _json.loads(m.group(0)) if m else None
            except ValueError:
                return None


class AzureOpenAILLM(_ChatLLM):
    """Azure OpenAI. Needs AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT
    (the deployment name you chose in Azure, not the model family)."""
    name = "azure-openai"

    def __init__(self):
        from openai import AzureOpenAI
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    def _ask(self, prompt: str, fallback: str) -> str:
        if not privacy.ai_allowed():   # AI switched off for this application: nothing leaves the server
            return fallback
        prompt = privacy.redact_current(prompt)
        ok, prompt = ratelimit.llm_gate(prompt)   # daily / per-application budget + prompt cap
        if not ok:
            return fallback
        try:
            r = self.client.chat.completions.create(
                model=self.deployment, messages=[{"role": "user", "content": prompt}])
            return (r.choices[0].message.content or "").strip() or fallback
        except Exception as e:  # keep the app working; surface the reason via `last_error` / the check CLI
            self.last_error = ratelimit.scrub(f"{type(e).__name__}: {e}")
            return fallback


class AnthropicLLM(_ChatLLM):
    name = "anthropic"

    def __init__(self):
        import anthropic  # noqa
        self.client = anthropic.Anthropic()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    def _ask(self, prompt: str, fallback: str) -> str:
        if not privacy.ai_allowed():
            return fallback
        prompt = privacy.redact_current(prompt)
        ok, prompt = ratelimit.llm_gate(prompt)
        if not ok:
            return fallback
        try:
            r = self.client.messages.create(model=self.model, max_tokens=400,
                                            messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip() or fallback
        except Exception as e:
            self.last_error = ratelimit.scrub(f"{type(e).__name__}: {e}")
            return fallback


_llm = None
_OFFLINE = OfflineLLM()


def _azure_configured() -> bool:
    return all(os.environ.get(k) for k in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"))


def get_llm():
    """Provider order: Azure OpenAI, then Anthropic, then the offline fallback."""
    global _llm
    if not privacy.ai_allowed():
        return _OFFLINE
    if _llm is None:
        _llm = OfflineLLM()
        if _azure_configured():
            try:
                _llm = AzureOpenAILLM()
            except Exception:
                pass
        elif os.environ.get("ANTHROPIC_API_KEY"):
            try:
                _llm = AnthropicLLM()
            except Exception:
                pass
    return _llm


if __name__ == "__main__":
    # Connectivity check:  python llm.py   (from app/backend). Never prints the key.
    import envload
    envload.load_env()
    llm = get_llm()
    print("provider:", llm.name)
    if llm.name == "offline":
        print("No key configured: set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT in app/backend/.env")
    else:
        out = llm._ask("Reply with exactly: OK", "FALLBACK")
        print("reply:", out)
        print("RESULT:", "connected" if out != "FALLBACK" else f"FAILED ({llm.last_error})")
