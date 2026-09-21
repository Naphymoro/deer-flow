"""Guards for the ndim-engine skill: valid package, no broken links, docs match the MCP server, script works."""

import asyncio
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from deerflow.skills.validation import _validate_skill_frontmatter

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "public" / "ndim-engine"
MCP_SERVER = REPO.parent / "nidm-rwanda-dashboard" / "mcp_server"
DOCS = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]
TOOL_NAME = re.compile(r"\bndim_[a-z_]+\b")


def _load_preflight():
    spec = importlib.util.spec_from_file_location("evidence_preflight", SKILL / "scripts" / "evidence_preflight.py")
    module = importlib.util.module_from_spec(spec)
    # A __pycache__ inside the skill directory would be copied into every sandbox skill view.
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _server_tool_names() -> set[str]:
    if not (MCP_SERVER / "ndim_mcp").is_dir():
        pytest.skip("nidm-rwanda-dashboard/mcp_server is not checked out next to deer-flow")
    sys.path.insert(0, str(MCP_SERVER))
    try:
        from ndim_mcp.config import Settings
        from ndim_mcp.server import create_server

        server = create_server(Settings(audit_log=None))
        return {tool.name for tool in asyncio.run(server.list_tools())}
    finally:
        sys.path.remove(str(MCP_SERVER))


def test_skill_frontmatter_is_valid():
    valid, message, name = _validate_skill_frontmatter(SKILL)
    assert valid, message
    assert name == "ndim-engine"


def test_every_referenced_file_exists():
    for doc in DOCS:
        for target in re.findall(r"`((?:references|scripts)/[\w./-]+)`", doc.read_text()):
            assert (SKILL / target).exists(), f"{doc.name} points to missing {target}"


def test_every_reference_file_is_indexed_in_skill_md():
    index = (SKILL / "SKILL.md").read_text()
    for path in [*(SKILL / "references").glob("*.md"), *(SKILL / "scripts").glob("*.py")]:
        assert f"{path.parent.name}/{path.name}" in index, f"{path.name} is not listed in SKILL.md"


def test_docs_only_name_tools_the_server_really_has():
    real = _server_tool_names()
    for doc in DOCS:
        unknown = set(TOOL_NAME.findall(doc.read_text())) - real - {"ndim_mcp", "ndim_engine"}
        assert not unknown, f"{doc.name} mentions tools that do not exist: {sorted(unknown)}"


def test_tool_reference_documents_every_server_tool():
    real = _server_tool_names()
    documented = set(TOOL_NAME.findall((SKILL / "references" / "tool-reference.md").read_text()))
    assert real <= documented, f"tool-reference.md is missing: {sorted(real - documented)}"


def test_hard_rules_survive_edits():
    text = (SKILL / "SKILL.md").read_text()
    for phrase in ("Never approve on the researcher's behalf", "Never set `consent`", "researcher review", "Never repeat an identical run", "Never translate silently"):
        assert phrase in text


# ── evidence_preflight.py ─────────────────────────────────────────────────────

ENGLISH = "Reliable electricity would help me extend working hours, but connection charges and outages make planning difficult. We support cleaner energy if the tariff remains affordable for the households in our village."


def test_preflight_accepts_english_text(tmp_path):
    (tmp_path / "e.txt").write_text(ENGLISH)
    preflight = _load_preflight()
    report = preflight.check(ENGLISH)
    assert report["ready_to_plan"] and report["language"]["likely"] == "en" and not report["personal_data"]
    assert preflight.main(["--file", str(tmp_path / "e.txt")]) == 0


def test_preflight_blocks_french_and_flags_personal_data():
    text = "Mon voisin dit que le foyer amélioré est trop cher et nous ne sommes pas sûrs de la qualité pour nos enfants dans le village. Contact: jean@example.rw ou +250 788 123 456."
    report = _load_preflight().check(text)
    assert not report["ready_to_plan"] and report["language"]["likely"] == "fr"
    assert report["personal_data"]["email"]["count"] == 1 and report["personal_data"]["phone"]["count"] == 1
    assert "jean" not in json.dumps(report["personal_data"])  # examples are masked


def test_preflight_length_limits():
    preflight = _load_preflight()
    assert "Too short" in preflight.check("too short")["problems"][0]
    assert "Too long" in preflight.check(ENGLISH * 100)["problems"][0]


def test_preflight_does_not_flag_ordinary_long_numbers_as_ids():
    assert "national_id_16_digits" not in _load_preflight().check(ENGLISH + " Budget was 1234567 francs.")["personal_data"]


def test_preflight_split_keeps_every_word_and_respects_the_limit(tmp_path):
    preflight = _load_preflight()
    paragraphs = [f"Paragraph {i}. " + ENGLISH * 6 for i in range(40)]
    text = "\n\n".join(paragraphs)
    chunks = preflight.split_text(text)
    assert len(chunks) > 1 and all(len(chunk) <= preflight.MAX_CHARS for chunk in chunks)
    assert "".join("".join(chunk.split()) for chunk in chunks) == "".join(text.split())


def test_preflight_splits_a_single_giant_paragraph(tmp_path):
    preflight = _load_preflight()
    text = (ENGLISH + " ") * 400
    chunks = preflight.split_text(text)
    assert all(len(chunk) <= preflight.MAX_CHARS for chunk in chunks)
    assert "".join("".join(chunk.split()) for chunk in chunks) == "".join(text.split())


def test_preflight_cli_writes_chunks_and_reports_unreadable_file(tmp_path):
    preflight = _load_preflight()
    source = tmp_path / "long.txt"
    source.write_text("\n\n".join(ENGLISH * 5 for _ in range(30)))
    assert preflight.main(["--file", str(source), "--split-dir", str(tmp_path / "chunks"), "--json"]) == 1
    assert len(list((tmp_path / "chunks").glob("chunk_*.txt"))) > 1
    assert preflight.main(["--file", str(tmp_path / "missing.txt")]) == 2
