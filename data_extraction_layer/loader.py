import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HANDBOOK_DIR = Path(os.getenv("HANDBOOK_DIR") or PROJECT_ROOT / "data" / "policy_handbook")


@dataclass(frozen=True)
class SourceDocument:
    source: str      # "20_motor.md"
    text: str


def load_markdown_files(folder: Path = HANDBOOK_DIR) -> list[SourceDocument]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Handbook folder not found: {folder}")

    docs = []
    for path in sorted(folder.glob("*.md")):          # sorted → deterministic order
        docs.append(SourceDocument(
            source=path.name,
            text=path.read_text(encoding="utf-8"),
        ))
    return docs
