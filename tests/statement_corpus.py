"""Corpus of real Kattis statements with the sections domjudgeimport's parser makes of them.

tests/statements/<contest>/<problem>/ holds the package's problem_statement/problem.en.tex (or problem.tex)
and problem.yaml,
and expected/ with one file per Polygon statement section (name.txt, legend.tex, input.tex, output.tex,
interaction.tex, notes.tex; a missing file = no section). test_statement_corpus.py compares the parser
with them.

    python tests/statement_corpus.py add <contest> <package dir>...   copy statements, write expected/
    python tests/statement_corpus.py regen                            rewrite every expected/ (after an
                                                                      intended parser change: review git diff)
"""
import os
import pathlib
import re
import shutil
import sys

import yaml

from polygon_uploader.domjudge.domjudge import find_statement_file, inline_newcommands, parse_statement, \
    problem_yaml_name

ROOT = pathlib.Path(__file__).resolve().parent / "statements"
FIELDS = {"name": "name.txt", "legend": "legend.tex", "input": "input.tex", "output": "output.tex",
          "interaction": "interaction.tex", "notes": "notes.tex"}


def cases():
    return sorted(p for p in ROOT.glob("*/*") if (p / "problem.yaml").is_file())


def parse_case(case):
    """The parser's sections for a corpus case, as domjudgeimport calls it."""
    meta = yaml.safe_load((case / "problem.yaml").read_text(encoding="utf-8")) or {}
    tex = find_statement_file(str(case), "en")
    interactive = "interactive" in str(meta.get("validation", ""))
    statement = parse_statement(pathlib.Path(tex).read_text(encoding="utf-8"), interactive,
                                problem_yaml_name(meta, "en"))
    return {field: getattr(statement, field, None) for field in FIELDS}


def read_expected(case):
    expected = {}
    for field, file in FIELDS.items():
        path = case / "expected" / file
        expected[field] = path.read_text(encoding="utf-8") if path.is_file() else None
    return expected


def write_expected(case):
    target = case / "expected"
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir()
    for field, value in parse_case(case).items():
        if value is not None:
            (target / FIELDS[field]).write_text(value, encoding="utf-8")


def words(tex):
    """Words of LaTeX text without markup: comments, macro and environment names, Polygon's own section
    headings, image file names and lengths dropped (the same idea as the skill's statement_diff)."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\(sub)?section\*?\{(Input|Output|Interaction|Notes?|Examples?)\}", " ", tex)
    tex = re.sub(r"\\(begin|end)\{[^}]*\}(\[[^\]]*\])?", " ", tex)
    tex = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}", " ", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?", " ", tex)
    return re.findall(r"[A-Za-z0-9]+", tex)


def add(contest, packages):
    for package in packages:
        tex = find_statement_file(package, "en")
        if tex is None or not os.path.isfile(os.path.join(package, "problem.yaml")):
            print("skipping %s: no statement or problem.yaml" % package)
            continue
        case = ROOT / contest / os.path.basename(os.path.normpath(package))
        (case / "problem_statement").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tex, case / "problem_statement" / os.path.basename(tex))
        shutil.copyfile(os.path.join(package, "problem.yaml"), case / "problem.yaml")
        write_expected(case)
        print("added", case.relative_to(ROOT))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "add":
        add(sys.argv[2], sys.argv[3:])
    elif sys.argv[1:] == ["regen"]:
        for case in cases():
            write_expected(case)
        print("rewrote expected/ of %d cases" % len(cases()))
    else:
        sys.exit(__doc__)
