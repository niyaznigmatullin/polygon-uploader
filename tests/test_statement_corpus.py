"""domjudgeimport's statement parser on the real statements of tests/statements (see statement_corpus.py)."""
import pathlib
import re

import pytest

from polygon_uploader.domjudge.domjudge import find_statement_file, group_end, inline_newcommands
from statement_corpus import FIELDS, ROOT, cases, parse_case, read_expected, words

CASES = cases()
IDS = [str(case.relative_to(ROOT)) for case in CASES]


def without_problemname(tex):
    match = re.search(r"\\problemname\s*\{", tex)
    return tex if match is None else tex[:match.start()] + tex[group_end(tex, match.end() - 1):]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_sections_as_expected(case):
    # after an intended parser change: python tests/statement_corpus.py regen, then review git diff
    assert parse_case(case) == read_expected(case)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_text_kept_in_order(case):
    # no word of the statement lost, duplicated or moved (Polygon shows legend, input, output,
    # interaction, notes in this order)
    original = pathlib.Path(find_statement_file(str(case), "en")).read_text(encoding="utf-8")
    sections = parse_case(case)
    parsed = "\n".join(sections[field] or "" for field in FIELDS if field != "name")
    assert words(parsed) == words(without_problemname(inline_newcommands(original)))


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_sections_well_formed(case):
    for field, value in parse_case(case).items():
        if value is None:
            continue
        assert "\\newcommand" not in value, field
        depth = 0
        for ch in re.sub(r"\\[{}%]", "", re.sub(r"(?<!\\)%.*", "", value)):
            depth += {"{": 1, "}": -1}.get(ch, 0)
            assert depth >= 0, "%s: a } without its {" % field
        assert depth == 0, "%s: a { without its }" % field
