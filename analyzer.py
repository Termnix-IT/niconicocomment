from __future__ import annotations
import base64
import time
import ollama
from config import OLLAMA_MODEL, OLLAMA_HOST, OLLAMA_PROMPT

import perf_log


class CommentAnalyzer:
    """Sends a PNG screenshot to a local Ollama vision model and returns comment strings.

    Requires Ollama to be running: `ollama serve`
    Requires the model to be pulled: `ollama pull gemma4`

    Designed to be called from a QThread worker; never touches Qt directly.
    """

    def __init__(self, comment_count: int = 5) -> None:
        self._comment_count = comment_count
        self._client = ollama.Client(host=OLLAMA_HOST)
        self._verify_connection()

    def set_comment_count(self, comment_count: int) -> None:
        self._comment_count = comment_count

    def _verify_connection(self) -> None:
        """Raises RuntimeError if Ollama is not reachable or the model is missing."""
        try:
            models = [m.model for m in self._client.list().models]
        except Exception as exc:
            raise RuntimeError(
                f"Ollama に接続できません ({OLLAMA_HOST})。\n"
                "Ollama が起動しているか確認してください: ollama serve"
            ) from exc

        # モデル名はタグ付き ("llava:latest") で返るため前方一致で確認
        if not any(m.startswith(OLLAMA_MODEL) for m in models):
            raise RuntimeError(
                f"モデル '{OLLAMA_MODEL}' が見つかりません。\n"
                f"以下のコマンドでダウンロードしてください: ollama pull {OLLAMA_MODEL}"
            )

    def generate_comments(self, png_base64: str) -> list[str]:
        """Returns comment strings, or empty list on any error."""
        t0 = time.perf_counter()
        status = "ok"
        comments: list[str] = []
        try:
            # ollama.Client.chat accepts images as base64 strings
            response = self._client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": self._prompt(),
                        "images": [png_base64],
                    }
                ],
            )
            raw = response.message.content
            comments = self._parse(raw)
            return comments
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
            print(f"[analyzer] Ollama error: {exc}")
            return []
        finally:
            perf_log.record(
                "analyze",
                (time.perf_counter() - t0) * 1000.0,
                extra=(
                    f"model={OLLAMA_MODEL};"
                    f"requested={self._comment_count};"
                    f"returned={len(comments)};"
                    f"png_b64_bytes={len(png_base64)};"
                    f"status={status}"
                ),
            )

    def _prompt(self) -> str:
        return (
            OLLAMA_PROMPT
            .replace("generate 5", f"generate {self._comment_count}")
            .replace("ONLY the 5", f"ONLY the {self._comment_count}")
        )

    def _parse(self, raw: str) -> list[str]:
        lines = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip "1. " or "1) " prefixes the model sometimes adds
            if len(line) > 2 and line[0].isdigit() and line[1] in ".)":
                line = line[2:].strip()
            if line:
                lines.append(line)
        return lines[: self._comment_count]
