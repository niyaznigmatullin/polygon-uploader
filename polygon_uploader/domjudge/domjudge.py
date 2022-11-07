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
from polygon_uploader.common import *
import polygon_uploader

__version__ = polygon_uploader.__version__
__author__ = 'Niyaz Nigmatullin'

if len(sys.argv) != 3:
    print("Usage: domjudgeimport <problem_directory> <polygon problem id>")
    print("Example: domjudgeimport bapc2022/adjustedaverage 123123")
    print("Version: " + __version__)
    exit(239)


def main():
    directory = sys.argv[1]
    polygon_pid = sys.argv[2]

    def upload_statement(prob, directory):
        for lang, lang_polygon in [('en', 'english')]:
            file = glob.glob(os.path.join(directory, "problem_statement/*%s*.tex" % lang))
            print(file)
            if len(file) == 0:
                continue
            file = file[0]
            with open(file) as statement_file:
                content = statement_file.read()
            print("problem.saveStatement language = " + lang_polygon)
            polygon_statement = Statement(encoding="UTF-8", legend=content)
            prob.save_statement(lang=lang_polygon, problem_statement=polygon_statement)

        solution_file = glob.glob(os.path.join(directory, "problem_statement/solution.tex"))
        if len(solution_file) > 0:
            solution_file = solution_file[0]
            with open(solution_file) as fs:
                content = fs.read()
            prob.save_statement(lang="english", problem_statement=Statement(tutorial=content))

    def upload_tests(prob, directory):
        def get_tests_from_directory(test_type):
            files = sorted(glob.glob(os.path.join(directory, "data/%s/*.in" % test_type)), key=lambda x: os.path.basename(x))
            return [FileTest(file, "domjudgeimport: %s/%s" % (test_type, os.path.basename(file))) for file in files]
        
        samples = get_tests_from_directory("sample")

        groups = [
            Group(0, get_tests_from_directory("sample"), GroupScoring.SUM),
            Group(100, get_tests_from_directory("secret"), GroupScoring.SUM),
        ]
        upload_groups(prob, groups)

    def upload_solutions(prob, directory):
        solution_types = [os.path.basename(x) for x in glob.glob(os.path.join(directory, "submissions/*"))]
        tags = { "accepted": SolutionTag.OK, "wrong_answer": SolutionTag.WA, "time_limit_exceeded": SolutionTag.TL, "run_time_error": SolutionTag.RE }
        for t in solution_types:
            tag = tags[t]
            solutions = list(glob.glob(os.path.join(directory, "submissions/%s/*" % t)))
            print(solutions)
            need_main = tag == SolutionTag.OK
            for file in solutions:
                with open(file) as source_file:
                    code = source_file.read()
                try:
                    fname = os.path.basename(file)
                    print('problem.saveSolution name = %s' % fname)
                    prob.save_solution(name=fname,
                                       file=code,
                                       source_type=None,
                                       tag=SolutionTag.MA if need_main else tag)
                except PolygonRequestFailedException as e:
                    print("API Error: " + e.comment)
                need_main = False

    api = authenticate()
    print("problems.list id = %s" % polygon_pid)
    prob = list(api.problems_list(name=polygon_pid))
    if len(prob) == 0:
        print("Problem %s not found" % polygon_pid)
        exit(1)
    prob = prob[0]
    # print("problem.enablePoints")
    # prob.enable_points(True)
    # print("problem.enableGroups")
    # prob.enable_groups('tests', True)

    # upload_tests(prob, directory)

    # upload_solutions(prob, directory)

    # upload_statement(prob, directory)

    
    # validators = glob.glob(os.path.join(directory, "output_validators/output_validator/*"))
    # if len(validators) > 0:
    #     for file in validators:
    #         with open(file) as fs:
    #             content = fs.read()
    #         print('problem.saveFile: ' + file)
    #         prob.save_file(type=FileType.RESOURCE,
    #                         name=os.path.basename(file),
    #                         file=content)
    # else:
    #     print("problem.setChecker std::wcmp.cpp")
    #     prob.set_checker('std::wcmp.cpp')

    description = """Imported by domjudge-import
The statement shouldn't compile, edit it
The checker is set to wcmp by default, if not set custom checker/validator should be implemented, the original ones are uploaded to resource files
"""

    info = ProblemInfo()
    info.interactive = False

    # time_limit_file = glob.glob(os.path.join(directory, ".timelimit"))
    # if len(time_limit_file) > 0:
    #     time_limit_file = time_limit_file[0]
    #     with open(time_limit_file) as fs:
    #         tl = int(float(fs.read().strip()) * 1000)
    #     info.time_limit = tl
    #     info.memory_limit = 512
    with open(os.path.join(directory, "problem.yaml")) as fs:
        s = fs.read()
        description += "\n\n" + s.strip()
        if "\nvalidation: custom interactive" in s:
            info.interactive = True
    prob.update_info(info)

    # print("problem.saveGeneralDescription: " + description)
    # prob.save_general_description(description)

#     tags = ['usaco']
#     print("problem.saveTags: " + str(tags))
#     prob.save_tags(tags)


if __name__ == "__main__":
    main()