"""Echoue si Git suit une donnee de reunion ou un secret evident."""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".docx", ".db", ".sqlite", ".log", ".token"}
ENV_SECRET_PATTERN = re.compile(
    r"(?im)^(HF_TOKEN|OLLAMA_PROXY_TOKEN|USB_SECRET)[ \t]*=[ \t]*[^\s#]+"
)
TOKEN_PATTERN = re.compile(r"(?i)hf_[a-z0-9]{20,}")


def main():
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    errors = []
    for relative in filter(None, output.split("\0")):
        path = ROOT / relative
        normalized = relative.replace("\\", "/").lower()
        sensitive_json = path.suffix.lower() == ".json" and any(
            marker in path.name.lower()
            for marker in ("transcript", "diarization", "speaker_map")
        )
        if (
            normalized.startswith("data/")
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or sensitive_json
        ):
            errors.append(f"fichier sensible suivi: {relative}")
            continue
        if path.name.startswith(".env") and path.name != ".env.local.exemple":
            errors.append(f"fichier d'environnement suivi: {relative}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_env_file = path.name.startswith(".env")
        if TOKEN_PATTERN.search(content) or (is_env_file and ENV_SECRET_PATTERN.search(content)):
            errors.append(f"secret potentiel: {relative}")

    if errors:
        print("\n".join(errors))
        return 1
    print("Controle Git: aucun audio, document, transcript ou secret suivi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
