import io
import zipfile

from polygon_api import (
    SolutionTag,
    Statement,
    FileType,
    ProblemInfo,
    PolygonRequestFailedException,
)
import sys
import os
import glob
import re
import yaml
from ..common import *
from .. import __version__


def main():
    if len(sys.argv) < 3:
        print("Usage: domjudgeimport <problem_directory> <polygon problem id> [--create]")
        print("Example: domjudgeimport bapc2022/adjustedaverage 123123")
        print("Version: " + __version__)
        exit(239)

    directory = sys.argv[1]
    polygon_pid = sys.argv[2]

    def upload_from_file(file, file_type):
        with open(file) as fs:
            content = fs.read()
        print('problem.saveFile: ' + file)
        try:
            return prob.save_file(type=file_type,
                                  name=os.path.basename(file),
                                  file=content) is None
        except PolygonRequestFailedException as e:
            print("API Error: " + e.comment)
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
                print("API Error: " + e.comment)

        solution_file = glob.glob(os.path.join(directory, "problem_statement/sol*.tex"))
        if len(solution_file) > 0:
            solution_file = solution_file[0]
            with open(solution_file) as fs:
                content = fs.read()
            try:
                prob.save_statement(lang="english", problem_statement=Statement(tutorial=content))
            except PolygonRequestFailedException as e:
                print("API Error: " + e.comment)

        for file in glob.glob(os.path.join(directory, "problem_statement/**"), recursive=True):
            if os.path.isfile(file):
                with open(file, "rb") as fs:
                    content = fs.read()
                try:
                    print("problem.saveStatementResource %s, size = %d bytes" % (file, len(content)))
                    prob.save_statement_resource(os.path.basename(file), content)
                except PolygonRequestFailedException as e:
                    print("API Error: " + e.comment)

    def upload_tests():
        def get_tests_from_directory(test_type, use_in_statements=False):
            files = sorted(glob.glob(os.path.join(directory, "data/%s/*.in" % test_type)),
                           key=lambda x: os.path.basename(x))
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
        for file in glob.glob(os.path.join(directory, "data/*")):
            if os.path.isfile(file):
                if not upload_from_file(file, FileType.SOURCE):
                    upload_from_file(file, FileType.RESOURCE)

    def upload_solutions():
        solution_types = [os.path.basename(x) for x in glob.glob(os.path.join(directory, "submissions/*"))]
        tags = {"accepted": SolutionTag.OK, "wrong_answer": SolutionTag.WA, "time_limit_exceeded": SolutionTag.TL,
                "run_time_error": SolutionTag.RJ}
        id = 1
        for t in solution_types:
            tag = tags.get(t, SolutionTag.RJ)
            solutions = glob.glob(os.path.join(directory, "submissions/%s/**" % t), recursive=True)
            solutions = list(filter(lambda x: os.path.isfile(x), solutions))
            solutions.sort(key=lambda x: 0 if x.endswith(".cpp") else 1)
            print(solutions)
            need_main = tag == SolutionTag.OK
            for file in solutions:
                code = open(file).read()
                fname = os.path.basename(file)
                _, extension = os.path.splitext(fname)
                if extension != ".java":
                    fname = ("s%02d_" % id) + fname
                    id += 1
                source_types = [None]
                if extension == ".py":
                    source_types = ["python.pypy3-64", "python.pypy3", "python.3", "python.pypy2", "python.2"]
                elif extension in [".cpp", ".cc", ".cxx", ".c++"]:
                    source_types = ["cpp.gcc14-64-msys2-g++23", "cpp.g++17", "cpp.msys2-mingw64-9-g++17", "cpp.ms2017", "cpp.gcc11-64-winlibs-g++20"]
                for source_type in source_types:
                    print('problem.saveSolution name = %s, sourceType = %s' % (fname, source_type))
                    try:
                        prob.save_solution(name=fname,
                                           file=code,
                                           source_type=source_type,
                                           tag=SolutionTag.MA if need_main else tag)
                        need_main = False
                        break
                    except PolygonRequestFailedException as e:
                        print("API Error: " + e.comment)
                    except _ as e:
                        print("Error: " + e.comment)

    def upload_resources(validator_dir):
        output_validators = glob.glob(os.path.join(directory, "%s/*/*" % validator_dir))
        if len(output_validators) > 0:
            for file in output_validators:
                upload_from_file(file, FileType.RESOURCE)

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
                print("API Error: " + e.comment)

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
        file = "archive.zip"
        print('problem.saveFile: ' + file)
        try:
            prob.save_file(type=FileType.AUX,
                           name=file,
                           file=content)
        except PolygonRequestFailedException as e:
            print("API Error: " + e.comment)

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
            with open(domjudge_ini) as fs:
                text = fs.read()
                r = re.compile(r"^\s*timelimit='?(\d+)'?\s*$")
                s = r.match(text)
                tl = s.group(1)
            info.time_limit = tl
        prob.update_info(info)

        print("problem.saveGeneralDescription")
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

    upload_tests()

    upload_solutions()

    upload_statement()

    if len(glob.glob(os.path.join(directory, "output_validators"))) == 0:
        print("problem.setChecker std::wcmp.cpp")
        prob.set_checker('std::wcmp.cpp')

    upload_resources("output_validators")
    upload_resources("input_validators")
    upload_description_and_info(description, is_interactive)

    upload_archive()


#     tags = ['usaco']
#     print("problem.saveTags: " + str(tags))
#     prob.save_tags(tags)


if __name__ == "__main__":
    main()
