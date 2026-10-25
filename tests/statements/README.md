# Statement corpus

Real Kattis problem statements (`problem_statement/problem.en.tex` and `problem.yaml`) from public contest
archives, and in `expected/` what domjudgeimport's statement parser makes of each one (one file per Polygon
statement section; a missing file means no such section). `tests/test_statement_corpus.py` checks the parser
against them and checks that no text is lost, duplicated or reordered.

- add contests: `python tests/statement_corpus.py add <contest> <package dir>...`
- after an intended parser change: `python tests/statement_corpus.py regen`, then review
  `git diff tests/statements`

## License

The statements here are not covered by the repository's MIT license. Each keeps its own license, given
together with its authors in the `problem.yaml` next to it (all of them CC BY-SA; problems whose
`problem.yaml` names no license are left out). Sources:

- `bapc2023`, `bapc2024`, `bapc2025`: Benelux Algorithm Programming Contest, https://chipcie.wisv.ch/archive/bapc/
- `gcpc2023`, `gcpc2024`, `gcpc2025`, `gcpc2026`: German Collegiate Programming Contest, https://gcpc.nwerc.eu
- `nac2026`: ICPC North America Championship 2026
- `ncpc2023`, `ncpc2024`, `ncpc2025`: Nordic Collegiate Programming Contest,
  https://github.com/icpc/ncpc-web/releases (CC BY-SA 3.0)
- `nwerc2023`, `nwerc2024`, `nwerc2025`: Northwestern Europe Regional Contest, https://nwerc.eu
  (2025: the legacy-format packages)
- `ukiepc2026`: UK & Ireland Programming Contest 2026
