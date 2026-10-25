"""Which files of a Kattis package domjudgeimport reads."""
from polygon_uploader.domjudge.domjudge import find_statement_file


def touch(directory, *names):
    (directory / "problem_statement").mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / "problem_statement" / name).write_text("%")


def test_statement_file_is_not_the_slide(tmp_path):
    # GCPC 2026 / NCPC 2025: problem-slide.en.tex matched prob*en*.tex too, and the first glob result
    # depends on the file system's directory order
    touch(tmp_path, "problem-slide.en.tex", "problem.en.tex", "problem.is.tex")
    assert find_statement_file(str(tmp_path), "en") == str(tmp_path / "problem_statement/problem.en.tex")


def test_legacy_statement_without_language(tmp_path):
    # the old Kattis format has problem_statement/problem.tex (English)
    touch(tmp_path, "problem.tex")
    assert find_statement_file(str(tmp_path), "en") == str(tmp_path / "problem_statement/problem.tex")


def test_no_statement(tmp_path):
    touch(tmp_path, "problem.is.tex", "problem-slide.en.tex")
    assert find_statement_file(str(tmp_path), "en") is None
