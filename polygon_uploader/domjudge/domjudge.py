import io
import zipfile

from polygon_api import (
    SolutionTag,
    Statement,
    FileType,
    ProblemInfo,
    PolygonRequestFailedException,
    ValidatorTestVerdict,
    CheckerTestVerdict,
)
import sys
import os
import glob
import re
import yaml
from ..common import *
from .. import __version__


CPP_EXTENSIONS = [".cpp", ".cc", ".cxx", ".c++"]


def main():
    if len(sys.argv) < 3:
        print("Usage: domjudgeimport <problem_directory> <polygon problem id> [--create]")
        print("Example: domjudgeimport bapc2022/adjustedaverage 123123")
        print("Version: " + __version__)
        exit(239)

    directory = sys.argv[1]
    polygon_pid = sys.argv[2]

    # API errors that no fallback recovered from, printed at the end
    failures = []

    def api_error(action, e, fallback=None):
        print("API Error: " + e.comment)
        if fallback is not None:
            print("  -> " + fallback)
        else:
            failures.append("%s: %s" % (action, e.comment))

    def upload_from_file(file, file_type, name=None, preprocess=None, fallback=None):
        if os.path.basename(file) == "testlib.h" and name is None:
            print("Skipping uploading 'testlib.h'")
            return False
        try:
            with open(file, encoding="utf-8") as fs:
                content = fs.read()
        except UnicodeDecodeError:
            print("Skipping '%s': not a UTF-8 text file" % file)
            return False
        if preprocess is not None:
            content = preprocess(content)
        print('problem.saveFile: ' + file + ("   with name='" + name + "'" if name else ""))
        try:
            # Polygon guesses an old C++ standard for sources without a type (e.g. no std::string::starts_with)
            source_type = None
            if file_type == FileType.SOURCE and os.path.splitext(file)[1] in CPP_EXTENSIONS:
                source_type = "cpp.gcc14-64-msys2-g++23"
            return prob.save_file(type=file_type,
                                  name=name if name else os.path.basename(file),
                                  file=content,
                                  source_type=source_type) is None
        except PolygonRequestFailedException as e:
            api_error("saveFile %s" % file, e, fallback)
            return False

    def parse_statement(content):
        result = Statement(encoding="UTF-8")
        legend = content

        def extract_pattern(pattern):
            match = pattern.search(legend)
            if match is None:
                return None, legend
            return_value = match.group(1)
            new_legend = pattern.sub('', legend)
            return return_value, new_legend

        def replace_new_command():
            pattern = re.compile(r"\\newcommand\s*\{?\s*(\\[a-zA-Z][a-zA-Z0-9]+)\s*}?\s*\{([^}]+)}", flags=re.S)
            vars = {}
            for match in pattern.finditer(legend):
                vars[match.group(1)] = match.group(2)
            new_legend = pattern.sub('', legend)
            for var, value in vars.items():
                new_legend = new_legend.replace(var + "{}", value)
                new_legend = new_legend.replace(var, value)
            return new_legend

        def extract_latex_tag_block(tag_name):
            return extract_pattern(re.compile(r"\\begin\{%s}(.*)\\end\{%s}" % (tag_name, tag_name), flags=re.S))

        def extract_section(tag_name):
            return extract_pattern(re.compile(r"\\(?:sub)?section[*]?\{%s}(.*)" % tag_name, flags=re.S))

        def extract_latex_tag(tag_name):
            return extract_pattern(re.compile(r"\\%s\{([^}]*)}" % tag_name, flags=re.S))

        def extract_input_output(tag_name):
            if re.search(r"\\(?:sub)?section[*]?\{%s}(.*)" % tag_name, legend) is not None:
                return extract_section(tag_name)
            else:
                return extract_latex_tag_block(tag_name)

        def replace_formula_brackets():
            return legend.replace('\\(', '$').replace('\\)', '$')

        legend = replace_new_command()
        legend = replace_formula_brackets()
        result.notes, legend = extract_input_output("(?:Examples?|Notes?)")
        if is_interactive:
            result.interaction, legend = extract_input_output("Interaction")
        result.output, legend = extract_input_output("Output")
        result.input, legend = extract_input_output("Input")
        result.name, legend = extract_latex_tag("problemname")
        result.legend = legend
        return result

    def upload_statement():
        for lang, lang_polygon in [('en', 'english')]:
            file = glob.glob(os.path.join(directory, "problem_statement/prob*%s*.tex" % lang))
            print(file)
            if len(file) == 0:
                continue
            file = file[0]
            with open(file) as statement_file:
                content = statement_file.read()
            print("problem.saveStatement language = " + lang_polygon)
            polygon_statement = parse_statement(content)
            try:
                prob.save_statement(lang=lang_polygon, problem_statement=polygon_statement)
            except PolygonRequestFailedException as e:
                api_error("saveStatement %s" % file, e)

        solution_file = glob.glob(os.path.join(directory, "problem_statement/sol*.tex"))
        if len(solution_file) > 0:
            solution_file = solution_file[0]
            with open(solution_file) as fs:
                content = fs.read()
            try:
                prob.save_statement(lang="english", problem_statement=Statement(tutorial=content))
            except PolygonRequestFailedException as e:
                api_error("saveStatement tutorial %s" % solution_file, e)

        for file in glob.glob(os.path.join(directory, "problem_statement/**"), recursive=True):
            if os.path.isfile(file):
                with open(file, "rb") as fs:
                    content = fs.read()
                try:
                    print("problem.saveStatementResource %s, size = %d bytes" % (file, len(content)))
                    prob.save_statement_resource(os.path.basename(file), content)
                except PolygonRequestFailedException as e:
                    api_error("saveStatementResource %s" % file, e)

    def upload_tests():
        def get_tests_from_directory(test_type, use_in_statements=False):
            files = (glob.glob(os.path.join(directory, "data/%s/*.in" % test_type)) +
                         glob.glob(os.path.join(directory, "data/%s/*/*.in" % test_type)))
            files.sort(key=lambda x: os.path.basename(x))
            return [Test(FileContents(file), "domjudgeimport: %s/%s" % (test_type, os.path.basename(file)),
                         use_in_statements=use_in_statements) for file in files]

        sample_tests = get_tests_from_directory("sample", use_in_statements=True)
        main_tests = get_tests_from_directory("secret")
        groups = [
            Group(0, sample_tests, GroupScoring.SUM),
            Group(100, main_tests, GroupScoring.SUM),
        ]

        all_tests = sample_tests + main_tests

        def get_test_by_prefix(file_path):
            file_name = os.path.basename(file_path)
            return all_tests[int(file_name[:file_name.find('.')]) - 1]

        if is_interactive:
            for test_file in sorted(glob.glob(os.path.join(directory, "data/sample/*.interaction"))):
                contents = open(test_file).readlines()

                def cut_if_starts_with(ch, contents):
                    return ''.join(map(lambda x: '\n' if x.startswith(ch) else x[1:], contents))

                test = get_test_by_prefix(test_file)
                test.use_in_statements = True
                test.input_for_statements = cut_if_starts_with('>', contents)
                test.output_for_statements = cut_if_starts_with('<', contents)
                test.verify = False
                test.description += ", non-verified custom input/output from sample/%s" % os.path.basename(test_file)
        elif is_custom_checker:
            for test_file in sorted(glob.glob(os.path.join(directory, "data/sample/*.ans"))):
                test = get_test_by_prefix(test_file)
                test.use_in_statements = True
                test.output_for_statements = open(test_file).read()
                test.verify = True
                test.description += ", verified custom output from sample/%s" % os.path.basename(test_file)

        upload_groups(prob, groups)
        for file in (glob.glob(os.path.join(directory, "data/*"))) + glob.glob(os.path.join(directory, "generators/*")):
            if os.path.isfile(file):
                if not upload_from_file(file, FileType.SOURCE, fallback="saving it as a resource instead"):
                    upload_from_file(file, FileType.RESOURCE)

    def read_data_cases(section, extensions):
        """Test cases data/<section>/**/*.in as (name, {extension: content}) with the files that exist."""
        cases = []
        section_files = glob.glob(os.path.join(directory, "data", section, "**", "*.in"), recursive=True)
        for file in sorted(section_files):
            base = file[:-len(".in")]
            case = {}
            for extension in extensions:
                if os.path.isfile(base + "." + extension):
                    with open(base + "." + extension) as fs:
                        case[extension] = fs.read()
            cases.append((os.path.relpath(base, os.path.join(directory, "data")), case))
        return cases

    def read_generators_yaml_cases(section):
        """Test cases of data.<section> in generators/generators.yaml given inline (in:, ans:, out:)."""
        file = os.path.join(directory, "generators/generators.yaml")
        if not os.path.isfile(file):
            return []
        with open(file) as fs:
            data = (yaml.safe_load(fs) or {}).get("data") or {}
        cases = []

        def walk(name, node):
            if isinstance(node, list):
                for item in node:
                    walk(name, item)
            elif isinstance(node, dict):
                if "in" in node:
                    cases.append(("generators.yaml " + name, {k: str(v) for k, v in node.items()}))
                elif "data" in node:
                    walk(name, node["data"])
                elif any(key in node for key in ("generate", "copy", "ans", "out")):
                    print("Skipping generators.yaml %s: no inline input" % name)
                else:
                    for key, value in node.items():
                        walk(name + "/" + str(key), value)
            elif node is not None:
                print("Skipping generators.yaml %s: no inline input" % name)

        walk(section, data.get(section))
        return cases

    def upload_validator_tests():
        tests = [(name, case["in"], ValidatorTestVerdict.VALID)
                 for name, case in read_data_cases("sample", ["in"])]
        tests += [(name, case["in"], ValidatorTestVerdict.INVALID)
                  for name, case in read_data_cases("invalid_input", ["in"]) + read_generators_yaml_cases("invalid_input")]
        for index, (name, content, verdict) in enumerate(tests, 1):
            print("problem.saveValidatorTest %d [%s] %s" % (index, name, verdict))
            try:
                prob.save_validator_test(index, test_input=content, test_verdict=verdict)
            except PolygonRequestFailedException as e:
                api_error("saveValidatorTest %s" % name, e)

    def upload_checker_tests():
        # the interactor decides the verdict of an interactive problem, a standard checker needs no tests
        if is_interactive or not is_custom_checker:
            return
        # a sample answer is assumed to be a valid output
        tests = [(name, case["in"], case["ans"], case["ans"], CheckerTestVerdict.OK)
                 for name, case in read_data_cases("sample", ["in", "ans"]) if "ans" in case]
        for section, verdict in [("valid_output", CheckerTestVerdict.OK),
                                 ("invalid_output", CheckerTestVerdict.WRONG_ANSWER)]:
            for name, case in read_data_cases(section, ["in", "ans", "out"]) + read_generators_yaml_cases(section):
                if "ans" not in case or "out" not in case:
                    print("Skipping checker test %s: needs both an answer and an output" % name)
                    continue
                tests.append((name, case["in"], case["out"], case["ans"], verdict))
        for index, (name, test_input, output, answer, verdict) in enumerate(tests, 1):
            # Polygon validates checker test inputs, inline ones like `in: "1"` lack the final newline
            if not test_input.endswith("\n"):
                test_input += "\n"
            print("problem.saveCheckerTest %d [%s] %s" % (index, name, verdict))
            try:
                prob.save_checker_test(index, test_input=test_input, test_output=output, test_answer=answer,
                                       test_verdict=verdict)
            except PolygonRequestFailedException as e:
                api_error("saveCheckerTest %s" % name, e)

    def upload_solutions():
        solution_types = sorted(os.path.basename(x) for x in glob.glob(os.path.join(directory, "submissions/*")))
        solution_types.sort(key=lambda x: 0 if x == "accepted" else 1)
        tags = {"accepted": SolutionTag.OK, "wrong_answer": SolutionTag.WA, "time_limit_exceeded": SolutionTag.TL,
                "run_time_error": SolutionTag.RJ}
        id = 1
        used_names = set()
        for t in solution_types:
            solutions = glob.glob(os.path.join(directory, "submissions/%s/**" % t), recursive=True)
            solutions = sorted(filter(lambda x: os.path.isfile(x), solutions))
            solutions.sort(key=lambda x: 0 if os.path.splitext(x)[1] in CPP_EXTENSIONS else 1)
            print(solutions)
            need_main = t == "accepted"
            for file in solutions:
                tag = tags.get(t, SolutionTag.RJ)
                try:
                    code = open(file, "r", encoding="utf-8").read()
                except UnicodeDecodeError:
                    print(f"Couldn't decode UTF-8 in solution '{file}'")
                    continue
                if tag == SolutionTag.RJ and "@EXPECTED_RESULTS@" in code:
                    for line in code.splitlines():
                        if "@EXPECTED_RESULTS@" in line:
                            after_colon = line.split(":")[1].strip()
                            elements = [x.strip() for x in after_colon.split(",")]
                            elements.sort()
                            if elements == ["ACCEPTED", "TIME_LIMIT_EXCEEDED"]:
                                tag = SolutionTag.TO

                fname = os.path.basename(file)
                _, extension = os.path.splitext(fname)
                # a Java file keeps its name unless another submission directory already used it
                if extension != ".java" or fname in used_names:
                    fname = ("s%02d_" % id) + fname
                    id += 1
                used_names.add(fname)
                source_types = [None]
                if extension == ".py":
                    source_types = ["python.pypy3-64", "python.pypy3", "python.3", "python.pypy2", "python.2"]
                elif extension in CPP_EXTENSIONS:
                    source_types = ["cpp.gcc14-64-msys2-g++23", "cpp.g++17", "cpp.msys2-mingw64-9-g++17", "cpp.ms2017", "cpp.gcc11-64-winlibs-g++20"]
                elif extension in [".java"]:
                    source_types = ["java21", "java8"]
                for i, source_type in enumerate(source_types):
                    print('problem.saveSolution name = %s, sourceType = %s' % (fname, source_type))
                    last = i + 1 == len(source_types)
                    try:
                        prob.save_solution(name=fname,
                                           file=code,
                                           source_type=source_type,
                                           tag=SolutionTag.MA if need_main else tag)
                        need_main = False
                        break
                    except PolygonRequestFailedException as e:
                        api_error("saveSolution %s" % file, e,
                                  None if last else "trying sourceType %s" % source_types[i + 1])

    def upload_resources(validator_dir, prefix):
        validators = (glob.glob(os.path.join(directory, "%s/*/*" % validator_dir)) +
                             glob.glob(os.path.join(directory, "%s/*" % validator_dir)))
        if len(validators) > 0:
            for file in validators:
                if os.path.isfile(file):
                    name = os.path.basename(file)
                    _, extension = os.path.splitext(name)
                    if extension in { ".py", ".java", ".cpp", ".cc", ".cxx", ".c++" } and prefix not in name:
                        name = prefix + "val_" + name
                    upload_from_file(file, FileType.RESOURCE, name=name)

    def upload_archive_file(file):
        if os.path.isfile(file):
            with open(file, "rb") as fs:
                content = fs.read()
            print('problem.saveFile: ' + file)
            try:
                prob.save_file(type=FileType.AUX,
                               name=os.path.basename(file),
                               file=content)
            except PolygonRequestFailedException as e:
                api_error("saveFile %s" % file, e)

    def upload_archive():
        def create_archive_bytes(directory):
            buffer = io.BytesIO()
            zip_file = zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED)
            for dirname, _, files in os.walk(directory):
                dirname = os.path.relpath(dirname, directory)
                if dirname.startswith(os.path.join("data", "secret")):
                    continue
                zip_file.write(os.path.join(directory, dirname), arcname=dirname)
                for filename in files:
                    zip_file.write(
                        os.path.join(directory, dirname, filename),
                        arcname=os.path.join(dirname, filename)
                    )
            zip_file.close()
            buffer.seek(0)
            return buffer.read()

        content = create_archive_bytes(directory)
        file = "archive.zip.jar"
        print('problem.saveFile: ' + file)
        try:
            prob.save_file(type=FileType.AUX,
                           name=file,
                           file=content)
        except PolygonRequestFailedException as e:
            api_error("saveFile %s" % file, e)

    def upload_description_and_info(description, is_interactive):
        info = ProblemInfo()
        info.interactive = is_interactive

        time_limit_file = glob.glob(os.path.join(directory, ".timelimit"))
        domjudge_ini = glob.glob(os.path.join(directory, "domjudge-problem.ini"))
        info.memory_limit = 1024
        if len(time_limit_file) > 0:
            time_limit_file = time_limit_file[0]
            with open(time_limit_file) as fs:
                tl = int(float(fs.read().strip()) * 1000)
            info.time_limit = tl
        elif len(domjudge_ini) > 0:
            domjudge_ini = domjudge_ini[0]
            tl = None
            with open(domjudge_ini, "r") as fs:
                for text in fs:
                    s = re.match(r"^\s*timelimit\s*=\s*'?(\d+)'?\s*$", text)
                    if s:
                        tl = int(s.group(1)) * 1000
                        break
            if tl:
                info.time_limit = tl
                print(f"Found timelimit = {tl} in domjudge-problem.ini")
        if info.time_limit is not None:
            try:
                if int(info.time_limit) > 15000:
                    print("Warning: Time limit '%s' exceeds 15000. Setting time limit to 15000." % tl)
                    info.time_limit = "15000"
            except ValueError:
                print("Error: Time limit is not a valid number.")
        prob.update_info(info)

        print("problem.saveGeneralDescription")
        limit = 14000
        if len(description) > limit:
            description = description[:limit] + "..."
        prob.save_general_description(description)

    def read_problem_yaml():
        file = os.path.join(directory, "problem.yaml")
        if os.path.isfile(file):
            with open(file) as fs:
                return fs.read()
        else:
            return None

    api = authenticate()
    print("problems.list id = %s" % polygon_pid)
    prob = list(api.problems_list(name=polygon_pid))
    to_create = any(map(lambda x: x == '--create', sys.argv))
    if len(prob) == 0:
        if to_create and not polygon_pid.isdigit():
            prob = [api.problem_create(name=polygon_pid)]
        else:
            print("Problem %s not found" % polygon_pid)
            exit(1)
    prob = prob[0]
    print("problem.enablePoints")
    prob.enable_points(True)
    print("problem.enableGroups")
    prob.enable_groups('tests', True)

    description = """Imported by domjudge-import
The statement shouldn't compile, edit it
The checker is set to wcmp by default, if not set custom checker/validator should be implemented, the original ones are uploaded to resource files
"""
    problem_yaml = read_problem_yaml()
    is_interactive = False
    is_custom_checker = False
    if problem_yaml is not None:
        description += "\n\n" + problem_yaml.strip()
        yaml_contents = yaml.safe_load(problem_yaml)
        if "validation" in yaml_contents:
            if "interactive" in yaml_contents["validation"]:
                is_interactive = True
            if "custom" in yaml_contents["validation"]:
                is_custom_checker = True

    # the interactive flag must be set before the statement: Polygon rejects
    # the interaction section of a non-interactive problem
    upload_description_and_info(description, is_interactive)

    upload_tests()

    upload_solutions()

    upload_statement()

    if len(glob.glob(os.path.join(directory, "output_validators"))) == 0:
        print("problem.setChecker std::wcmp.cpp")
        prob.set_checker('std::wcmp.cpp')
    else:
        name = "testlib_checker.cpp"
        for checker in glob.glob(os.path.join(directory, "output_validators/main/*.cpp")):
            if upload_from_file(checker, FileType.SOURCE, name=name):
                prob.set_checker(name)

    if len(glob.glob(os.path.join(directory, "input_validators/main"))) > 0:
        name = "testlib_validator.cpp"
        for validator in glob.glob(os.path.join(directory, "input_validators/main/*.cpp")):
            preprocess = lambda x: re.sub(r'return\s+42\s*;', 'return 0;', x)
            if upload_from_file(validator, FileType.SOURCE, name=name, preprocess=preprocess):
                prob.set_validator(name)

    upload_validator_tests()
    upload_checker_tests()

    upload_resources("output_validators", "out")
    upload_resources("input_validators", "in")

    upload_archive()

    if failures:
        print("domjudgeimport: %d API error(s) not recovered:" % len(failures))
        for failure in failures:
            print("  " + failure)
        exit(3)
    print("domjudgeimport: done, no unrecovered API errors")


#     tags = ['usaco']
#     print("problem.saveTags: " + str(tags))
#     prob.save_tags(tags)


if __name__ == "__main__":
    main()
