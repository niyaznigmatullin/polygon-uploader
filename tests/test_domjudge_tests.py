"""Test-related helpers of domjudgeimport: sample transcripts, sample matching, data/ and generators.yaml cases."""
from polygon_uploader.domjudge.domjudge import (
    cut_if_starts_with,
    find_sample_test,
    read_data_cases,
    read_generators_yaml_cases,
    tests_from_directory as sample_or_secret_tests,  # not test_*: pytest would collect it
)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_transcript_sides():
    transcript = ["< 3\n", "> 1 1 1\n", "<5\n", "> 4 5 6\n"]
    assert cut_if_starts_with(">", transcript) == "3\n\n5\n\n"     # input for statements
    assert cut_if_starts_with("<", transcript) == "\n1 1 1\n\n4 5 6\n"   # output for statements


def test_tests_from_directory_sorted_by_basename(tmp_path):
    write(tmp_path / "data/secret/b/01.in", "1\n")
    write(tmp_path / "data/secret/02.in", "2\n")
    write(tmp_path / "data/secret/a/03.in", "3\n")
    tests = sample_or_secret_tests(str(tmp_path), "secret")
    assert [t.description for t in tests] == ["domjudgeimport: secret/01.in", "domjudgeimport: secret/02.in",
                                             "domjudgeimport: secret/03.in"]
    assert tests[1]() == "2\n"


def test_sample_matched_by_name(tmp_path):
    write(tmp_path / "data/sample/001-small.in", "1\n")
    write(tmp_path / "data/sample/002-large.in", "2\n")
    samples = sample_or_secret_tests(str(tmp_path), "sample", use_in_statements=True)
    test = find_sample_test(str(tmp_path / "data/sample/002-large.interaction"), samples)
    assert test.description == "domjudgeimport: sample/002-large.in"


def test_sample_without_input(tmp_path):
    # NAC 2026: data/sample has only 1.interaction (the input is in attachments/) -- the transcript
    # used to land on the first secret test
    write(tmp_path / "data/secret/00.in", "1\n0\n")
    samples = sample_or_secret_tests(str(tmp_path), "sample", use_in_statements=True)
    assert find_sample_test(str(tmp_path / "data/sample/1.interaction"), samples) is None


def test_read_data_cases(tmp_path):
    write(tmp_path / "data/invalid_output/wrong/1.in", "1\n")
    write(tmp_path / "data/invalid_output/wrong/1.ans", "2\n")
    write(tmp_path / "data/invalid_output/wrong/1.out", "3\n")
    write(tmp_path / "data/invalid_output/2.in", "4\n")
    assert read_data_cases(str(tmp_path), "invalid_output", ["in", "ans", "out"]) == [
        ("invalid_output/2", {"in": "4\n"}),
        ("invalid_output/wrong/1", {"in": "1\n", "ans": "2\n", "out": "3\n"}),
    ]


def test_read_generators_yaml_cases(tmp_path):
    write(tmp_path / "generators/generators.yaml", """
data:
  invalid_input:
    data:
      - zero: {in: "0"}
      - big:
          in: "1000001"
      - gen: {generate: gen.py 5}
""")
    assert read_generators_yaml_cases(str(tmp_path), "invalid_input") == [
        ("generators.yaml invalid_input/zero", {"in": "0"}),
        ("generators.yaml invalid_input/big", {"in": "1000001"}),
    ]
    assert read_generators_yaml_cases(str(tmp_path), "valid_output") == []
