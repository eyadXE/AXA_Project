# data_extraction_layer/parser.py
import re
from collections import Counter

from .loader import SourceDocument, load_markdown_files
from .models import Chunk, ChunkMetadata

SECTION_RE = re.compile(r"^#{1,2}\s*Section\s+(\d+)\s*·\s*(.+?)\s*$", re.MULTILINE)
CLAUSE_RE = re.compile(r"^\*\*Clause\s+(\d+\.\d+)\s*[—–-]\s*(.+?)\.\*\*", re.MULTILINE)
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)

# Explicit mapping beats guessing from file names: renaming a file can't silently break it.
LINE_OF_BUSINESS = {
    "0": "general",
    "1": "health",
    "2": "motor",
    "3": "property",
    "4": "travel",
    "5": "all",      # universal exclusions apply to every line
    "6": "all",
}


class ParsingError(ValueError):
    """Raised when a handbook file doesn't match the expected structure."""


def _clean_body(raw: str) -> str:
    body = TABLE_LINE_RE.sub("", raw)   # drop table rows
    body = body.replace("**", "")       # markdown bold is noise for embeddings
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_document(doc: SourceDocument) -> list[Chunk]:
    section = SECTION_RE.search(doc.text)
    if section is None:
        raise ParsingError(f"{doc.source}: no 'Section N · Title' header found")
    section_number, section_title = section.groups()

    line_of_business = LINE_OF_BUSINESS.get(section_number)
    if line_of_business is None:
        raise ParsingError(f"{doc.source}: unknown section number {section_number!r}")

    matches = list(CLAUSE_RE.finditer(doc.text))
    if not matches:
        raise ParsingError(f"{doc.source}: no clauses found")

    chunks: list[Chunk] = []
    for i, match in enumerate(matches):
        clause_id, clause_title = match.groups()

        if not clause_id.startswith(f"{section_number}."):
            raise ParsingError(
                f"{doc.source}: clause {clause_id} doesn't belong to section {section_number}"
            )

        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.text)
        body = _clean_body(doc.text[match.end():body_end])
        if not body:
            raise ParsingError(f"{doc.source}: clause {clause_id} has an empty body")

        chunks.append(
            Chunk(
                id=f"clause-{clause_id}",
                text=f"{section_title} — Clause {clause_id}: {clause_title}.\n{body}",
                metadata=ChunkMetadata(
                    source=doc.source,
                    section_number=section_number,
                    section_title=section_title,
                    clause_id=clause_id,
                    clause_title=clause_title,
                    line_of_business=line_of_business,
                ),
            )
        )
    return chunks


def parse_documents(docs: list[SourceDocument]) -> list[Chunk]:
    chunks = [chunk for doc in docs for chunk in parse_document(doc)]

    duplicates = [cid for cid, n in Counter(c.id for c in chunks).items() if n > 1]
    if duplicates:
        raise ParsingError(f"Duplicate clause ids: {sorted(duplicates)}")
    return chunks


if __name__ == "__main__":
    chunks = parse_documents(load_markdown_files())
    print(f"Parsed {len(chunks)} chunks")
    for c in chunks[:3]:
        print(c.id, "|", c.metadata.line_of_business, "|", c.text[:80])
