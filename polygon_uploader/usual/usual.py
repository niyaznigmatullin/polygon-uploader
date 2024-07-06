import glob

from polygon_api import (
    SolutionTag,
    PolygonRequestFailedException,
    FileType,
)
import sys
import os
from polygon_uploader.common import *
import polygon_uploader

__version__ = polygon_uploader.__version__
__author__ = 'Niyaz Nigmatullin'

if len(sys.argv) != 3:
    print(
        "Usage: usual <directory> <polygon problem id>")
    # by comma>]
    print("Example: usual ~/Downloads/aplusb 123123")
    print("Version: " + __version__)
    exit(239)


def upload_tests(prob, tests_directory):
    files = list(os.listdir(tests_directory))
    files.sort(key=lambda name: os.path.splitext(name)[0])

    def file_to_test(name, use_in_statements=False):
        return Test(FileContents(os.path.join(tests_directory, name)), 'polygon_uploader: filename = %s' % name,
                    use_in_statements=use_in_statements)

    samples = list(filter(lambda name: os.path.splitext(name)[1].endswith("sample"), files))
    main_tests = list(filter(lambda name: not os.path.splitext(name)[1].endswith("sample"), files))

    groups = [
        Group(0, [file_to_test(x, use_in_statements=True) for x in samples],
              GroupScoring.SUM),
        Group(100, [file_to_test(x) for x in main_tests], GroupScoring.GROUP),
    ]

    upload_groups(prob, groups)


def take_all(directory, templates):
    all = []
    for x in templates:
        all += glob.glob(os.path.join(directory, x))
    return all


def upload_generator(prob, tests_directory):
    for path in take_all(tests_directory, ["*.java", "*.cpp", "*.py"]):
        with open(path, "rb") as source:
            try:
                name = os.path.basename(path)
                print('problem.saveFile name = %s' % name)
                prob.save_file(name=name,
                               file=source.read(),
                               type=FileType.SOURCE)
            except PolygonRequestFailedException as e:
                print("API Error: " + e.comment)


def get_source_type(name):
    if name.endswith("cpp"):
        return "cpp.g++17"
    if name.endswith("java"):
        return "java8"
    if name.endswith("py"):
        return "python3"
    return None


def upload_solutions(prob, solutions_directory):
    tag = SolutionTag.MA
    # for name in os.listdir(solutions_directory):
    for path in take_all(solutions_directory, ["*.java", "*.cpp", "*.py"]):
        with open(path, "rb") as solution:
            try:
                name = os.path.basename(path)
                source_type = get_source_type(name)
                print('problem.saveSolution name = %s' % name)
                prob.save_solution(name=name,
                                   file=solution.read(),
                                   source_type=source_type,
                                   tag=tag)
                tag = SolutionTag.OK
            except PolygonRequestFailedException as e:
                print("API Error: " + e.comment)


def save_file(prob, path, type):
    with open(path, "rb") as source:
        try:
            name = os.path.basename(path)
            print('problem.saveFile name = %s' % name)
            prob.save_file(name=name,
                           file=source.read(),
                           type=type)
        except PolygonRequestFailedException as e:
            print("API Error: " + e.comment)


def upload_sources(prob, directory):
    for path in take_all(directory, ["**/*testlib*"]):
        save_file(prob, path, FileType.RESOURCE)
    for path in take_all(directory, ["**/*gen*.", "**/*Gen*.", "**/*check*.", "**/*Check."]):
        save_file(prob, path, FileType.SOURCE)


def main():
    directory = sys.argv[1]
    polygon_pid = sys.argv[2]

    api = authenticate()
    print("problems.list id = %s" % polygon_pid)
    prob = list(api.problems_list(id=polygon_pid))
    if len(prob) == 0:
        print("Problem %s not found" % polygon_pid)
        exit(1)
    prob = prob[0]
    print("problem.enablePoints")
    prob.enable_points(True)
    print("problem.enableGroups")
    prob.enable_groups('tests', True)

    upload_tests(prob, os.path.join(directory, "src"))

    upload_sources(prob, directory)

    # upload_solutions(prob, directory)

    upload_solutions(prob, os.path.join(directory, "solutions"))

    # print("problem.setChecker std::wcmp.cpp")
    # prob.set_checker('std::wcmp.cpp')

    description = """Imported by polygon_uploader from local directory
The solution probably uses files, instead of stdin/stdout
"""
    print("problem.saveGeneralDescription: " + description)
    prob.save_general_description(description)


if __name__ == "__main__":
    main()
