"""Statement parsing of domjudgeimport: \\newcommand inlining and the split into Polygon sections."""
from polygon_uploader.domjudge.domjudge import inline_newcommands, parse_statement


def test_newcommand_body_with_braces():
    # NAC 2026: the body ended at the first "}", leaving "10^{5" and a stray "}" in the legend
    tex = "\\newcommand{\\maxn}{10^{5}}\n$N \\le \\maxn$"
    assert inline_newcommands(tex) == "\n$N \\le 10^{5}$"


def test_newcommand_nested_and_escaped_braces():
    tex = "\\newcommand{\\lmaxk}{2 \\cdot 10^{5}}\\newcommand{\\set}{\\{1, 2\\}}\n\\lmaxk, \\set"
    assert inline_newcommands(tex) == "\n2 \\cdot 10^{5}, \\{1, 2\\}"


def test_newcommand_whole_names_only():
    # \amax must not eat the start of \amaxn, whatever the definition order
    tex = "\\newcommand{\\amax}{A}\n\\newcommand{\\amaxn}{B}\n\\amaxn \\amax \\amaxn"
    assert inline_newcommands(tex) == "\n\nB A B"


def test_newcommand_empty_braces_use():
    assert inline_newcommands("\\newcommand{\\N}{N}\\N{} items") == "N items"


def test_newcommand_unbraced_name():
    assert inline_newcommands("\\newcommand\\maxq{1\\,000}up to \\maxq") == "up to 1\\,000"


def test_sections():
    tex = ("\\problemname{Some Problem}\n\\newcommand{\\maxn}{10^{5}}\n"
           "Legend \\(x\\).\n"
           "\\section*{Input}\nAn integer $n$ ($1 \\le n \\le \\maxn$).\n"
           "\\section*{Output}\nOne integer.\n")
    st = parse_statement(tex, is_interactive=False)
    assert st.name == "Some Problem"
    assert st.legend.strip() == "Legend $x$."
    assert st.input.strip() == "An integer $n$ ($1 \\le n \\le 10^{5}$)."
    assert st.output.strip() == "One integer."
    assert st.notes is None


def test_environments():
    tex = ("\\problemname{P}\nLegend.\n\\begin{Input}\nIn.\n\\end{Input}\n"
           "\\begin{Output}\nOut.\n\\end{Output}\n")
    st = parse_statement(tex, is_interactive=False)
    assert (st.legend.strip(), st.input.strip(), st.output.strip()) == ("Legend.", "In.", "Out.")


def test_interaction_and_notes():
    tex = ("\\problemname{I}\nLegend.\n\\section*{Interaction}\nAsk.\n"
           "\\subsection*{Notes}\nA note.\n")
    st = parse_statement(tex, is_interactive=True)
    assert st.interaction.strip() == "Ask."
    assert st.notes.strip() == "A note."
    assert st.legend.strip() == "Legend."


def test_interaction_kept_in_legend_when_not_interactive():
    # Polygon rejects an interaction section for a non-interactive problem
    st = parse_statement("Legend.\n\\section*{Interaction}\nAsk.\n", is_interactive=False)
    assert st.interaction is None
    assert "Ask." in st.legend
