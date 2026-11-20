# tests/test_parser.py
from textwrap import dedent

import pytest

from data_extraction_layer.loader import SourceDocument, load_markdown_files
from data_extraction_layer.parser import ParsingError, parse_document, parse_documents


def make_doc(text: str, source: str = "test.md") -> SourceDocument:
    """Build a small in-memory document, so unit tests never touch the disk."""
    return SourceDocument(source=source, text=dedent(text).strip())


# ---------------------------------------------------------------------------
# 1. Unit tests: the parsing rules, on tiny hand-written inputs
# ---------------------------------------------------------------------------

def test_body_on_next_line_layout():
    doc = make_doc("""
        # Section 2 · Motor Insurance

        **Clause 2.1 — What motor cover includes.**
        Collision damage and theft.
    """)

    chunks = parse_document(doc)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.id == "clause-2.1"
    assert chunk.metadata.clause_title == "What motor cover includes"
    assert chunk.metadata.section_title == "Motor Insurance"
    assert chunk.metadata.line_of_business == "motor"
    assert "Collision damage and theft." in chunk.text


def test_body_on_same_line_layout():
    doc = make_doc("""
        # Section 5 · Universal Exclusions

        **Clause 5.1 — War and terrorism.** Loss caused by war is excluded.
    """)

    chunk = parse_document(doc)[0]

    assert chunk.metadata.clause_title == "War and terrorism"
    assert "Loss caused by war is excluded." in chunk.text


def test_title_containing_a_period_is_not_cut():
    doc = make_doc("""
        # Section 3 · Property & Home Insurance

        **Clause 3.2 — Burst pipes (covered) vs. flood (excluded without rider).**
        Body text.
    """)

    chunk = parse_document(doc)[0]

    assert chunk.metadata.clause_title == "Burst pipes (covered) vs. flood (excluded without rider)"


def test_each_body_stops_at_the_next_clause():
    doc = make_doc("""
        # Section 2 · Motor Insurance

        **Clause 2.1 — First.**
        Body one.

        **Clause 2.2 — Second.**
        Body two.
    """)

    first, second = parse_document(doc)

    assert "Body one." in first.text
    assert "Body two." not in first.text      # no bleed into the next clause
    assert "Body two." in second.text


def test_table_rows_are_dropped():
    doc = make_doc("""
        # Section 6 · Required-Documents Matrix

        | Claim type | Required documents |
        |---|---|
        | Motor — theft | police report |

        **Clause 6.1 — Partial documents.** Request what is missing.
    """)

    chunks = parse_document(doc)

    assert len(chunks) == 1
    assert "|" not in chunks[0].text
    assert "police report" not in chunks[0].text


def test_double_hash_section_header_and_title_line():
    doc = make_doc("""
        # AXA Egypt — Claims Handbook
        ## Section 0 · General Rules & Claims Authority

        **Clause 0.1 — Purpose of this handbook.**
        Body.
    """)

    chunk = parse_document(doc)[0]

    assert chunk.metadata.section_number == "0"
    assert chunk.metadata.section_title == "General Rules & Claims Authority"
    assert chunk.metadata.line_of_business == "general"


def test_markdown_bold_is_stripped_from_body():
    doc = make_doc("""
        # Section 2 · Motor Insurance

        **Clause 2.2 — Third-party-only.**
        It does **not** cover own damage.
    """)

    chunk = parse_document(doc)[0]

    assert "**" not in chunk.text
    assert "It does not cover own damage." in chunk.text


def test_new_chunks_have_no_vector_yet():
    doc = make_doc("""
        # Section 2 · Motor Insurance

        **Clause 2.1 — Cover.**
        Body.
    """)

    assert parse_document(doc)[0].vector is None


# ---------------------------------------------------------------------------
# 2. Error handling: bad input must fail loudly, never silently
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected_message"),
    [
        ("**Clause 2.1 — Cover.**\nBody.", "no 'Section N · Title' header"),
        ("# Section 9 · Unknown\n\n**Clause 9.1 — X.**\nBody.", "unknown section number"),
        ("# Section 2 · Motor Insurance\n\nJust text, no clauses.", "no clauses found"),
        ("# Section 2 · Motor Insurance\n\n**Clause 3.1 — Wrong.**\nBody.", "doesn't belong to section"),
        ("# Section 2 · Motor Insurance\n\n**Clause 2.1 — Empty.**\n", "empty body"),
    ],
    ids=["missing-section", "unknown-section", "no-clauses", "wrong-section", "empty-body"],
)
def test_malformed_documents_raise(text, expected_message):
    with pytest.raises(ParsingError, match=expected_message):
        parse_document(make_doc(text))


def test_duplicate_ids_across_files_raise():
    text = "# Section 2 · Motor Insurance\n\n**Clause 2.1 — Cover.**\nBody."
    docs = [make_doc(text, "a.md"), make_doc(text, "b.md")]

    with pytest.raises(ParsingError, match="Duplicate clause ids"):
        parse_documents(docs)


# ---------------------------------------------------------------------------
# 3. Integration tests: the real handbook on disk
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_chunks():
    """Parse the real handbook once and share it across the tests below."""
    return parse_documents(load_markdown_files())


def test_real_handbook_has_expected_clause_count(real_chunks):
    assert len(real_chunks) == 54


def test_real_handbook_ids_are_unique(real_chunks):
    ids = [c.id for c in real_chunks]
    assert len(ids) == len(set(ids))


def test_known_distractor_clauses_exist(real_chunks):
    by_id = {c.id: c for c in real_chunks}
    assert "clause-3.2" in by_id    # burst pipe vs flood
    assert "clause-4.5" in by_id    # baggage delay vs loss
    assert "clause-1.6" in by_id    # dental cosmetic
    assert by_id["clause-2.2"].metadata.line_of_business == "motor"


def test_parsing_is_deterministic():
    first = parse_documents(load_markdown_files())
    second = parse_documents(load_markdown_files())
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]
