from bs4 import BeautifulSoup
from polygon_api import (
    PointsPolicy,
    FeedbackPolicy,
    SolutionTag,
    Statement,
    PolygonRequestFailedException,
)
import sys
import os
import zipfile
import re
from polygon_uploader.common import *

__version__ = '1.0'
__author__ = 'Niyaz Nigmatullin'

if len(sys.argv) != 4:
    print("Usage: usacoimport <usaco_cp_id> <usaco_id> <polygon problem id>")  # [<number of tests in groups separated by comma>]
    print("Example: usacoimport 1020 deleg_platinum_feb20 123123")
    print("usaco_cp_id is taken from the problem description link: http://usaco.org/index.php?page=viewproblem2&cpid=1020, usaco_cp_id=1020")
    print("usaco_id is taken from testdata link: http://usaco.org/current/data/deleg_platinum_feb20.zip, usaco_id=deleg_platinum_feb20")
    exit(239)


def main():
    cpid = sys.argv[1]
    usaco_id = sys.argv[2]
    polygon_pid = sys.argv[3]
    # groupsizes = [] if len(sys.argv) < 5 else [int(x) for x in sys.argv[4].split(',')]
    dir = create_temporary_directory("__usaco")

    problem_href = 'http://usaco.org/index.php?page=viewproblem2&cpid=%s' % cpid
    solution_href = 'http://usaco.org/current/data/sol_%s.html' % usaco_id
    testdata_href = 'http://usaco.org/current/data/%s.zip' % usaco_id

    def latexify(statement):
        for e in statement.find_all_next('ul'):
            e.insert_before('\n\\begin{itemize}\n')
            e.insert_after('\n\\end{itemize}\n')
            e.unwrap()
        for e in statement.find_all_next('li'):
            e.insert_before('\n\\item{')
            e.insert_after('}\n')
            e.unwrap()
        for e in statement.find_all_next('strong'):
            e.insert_before('\\textbf{')
            e.insert_after('}')
            e.unwrap()

    def latexify_post(s, lang):
        s = re.sub(r"'(.)'", "`\\\\t{\\1}'", s, re.DOTALL)
        if lang == 'en':
            s = re.sub(r'"([^"])"', "``\\\\t{\\1}''", s, re.DOTALL)
        else:
            s = re.sub(r'"([^"])"', "<<\\\\t{\\1}>>", s, re.DOTALL)
        return s

    def download_statement():
        for lang, lang_polygon in [('en', 'english'), ('ru', 'russian')]:
            page = download_web_page(problem_href + "&lang=%s" % lang)
            reg = re.compile(r".*<h2>\s*Problem\s*\d+\.\s*(\S.*[^<])\s+</h2>.*", re.DOTALL)
            g = reg.match(page)
            name = g.group(1)
            parser = BeautifulSoup(page, "html.parser")
            statement = parser.find('div', attrs={'class', 'problem-text'})
            statement = statement.extract()
            latexify(statement)

            def extract_part(class_name):
                part = statement.find_all_next('div', attrs={'class', class_name})
                if len(part) == 0:
                    return None
                part = part[0]
                part.extract()
                part.find('h4').extract()
                return part

            scoring = extract_part('prob-section')
            input = extract_part('prob-in-spec')
            output = extract_part('prob-out-spec')
            for x in statement.find_all_next('h4'):
                x.extract()

            ps = statement.find_all_next('p')
            note = None
            for e in ps[::-1]:
                if len(e.find_all_next('pre', attrs={'class', 'in'})) > 0:
                    e.extract()
                    note = e
                    break

            for x in note.find_all_next('pre'):
                x.extract()

            # print("Legend: " + statement.text)
            # print("Input: " + input.text)
            # print("Output: " + output.text)
            # print("Scoring: " + scoring.text)
            # print("Note: " + note.text)
            print("problem.saveStatement language = " + lang_polygon)
            polygon_statement = Statement(encoding="UTF-8",
                                          name=name,
                                          legend=latexify_post(statement.text, lang),
                                          input=latexify_post(input.text, lang),
                                          output=latexify_post(output.text, lang) +
                                                 "\n\\Scoring\n" + latexify_post(scoring.text, lang),
                                          notes=latexify_post(note.text, lang))
            prob.save_statement(lang=lang_polygon, problem_statement=polygon_statement)

    def download_tests(dir, tests_dir):
        tests_archive = os.path.join(dir, "tests.zip")
        download_file_to(testdata_href, tests_archive)
        print(tests_archive, "downloaded")
        zip_archive = zipfile.ZipFile(tests_archive, 'r')
        file_list = zip_archive.namelist()
        to_extract = [x for x in file_list if x.endswith('.in')]
        zip_archive.extractall(path=tests_dir, members=to_extract)
        print(to_extract, 'extracted to', tests_dir)
        cnt = len(to_extract)
        scored_tests = cnt - 1
        for tid in range(1, cnt + 1):
            points = None
            if tid >= 2:
                points = 100 // scored_tests
                if tid - 2 >= 100 % scored_tests:
                    points += 1
            fname = '%d.in' % tid
            with open(os.path.join(tests_dir, fname), "r") as tf:
                group = '0' if tid == 1 else '1'
                print("problem.saveTest %d with group = %s, points = %s" % (tid, group, str(points)))
                prob.save_test('tests', tid, tf.read(),
                               test_group=group,
                               test_points=points,
                               test_description="Imported with usaco_import %s" % fname,
                               test_use_in_statements=True if tid == 1 else None
                )
        prob.save_test_group('tests', '0', points_policy=PointsPolicy.EACH_TEST,
                             feedback_policy=FeedbackPolicy.COMPLETE)
        prob.save_test_group('tests', '1', points_policy=PointsPolicy.EACH_TEST,
                             feedback_policy=FeedbackPolicy.COMPLETE, dependencies=['0'])
        prob.set_checker('std::wcmp.cpp')

    def download_solutions():
        solution_page = download_web_page(solution_href)
        parser = BeautifulSoup(solution_page, "html.parser")
        solutions = parser.find_all('pre', attrs={'class', 'prettyprint'})
        analysis = parser.find('body')
        latexify(analysis)
        id = 0
        tag = SolutionTag.MA
        for x in solutions:
            x.extract()
            code = x.text
            id += 1
            is_cpp = '#include' in code
            fname = 'sol%d.%s' % (id, 'cpp' if is_cpp else 'java')
            try:
                prob.save_solution(name=fname,
                                   file=code,
                                   source_type="cpp.g++17" if is_cpp else 'java8',
                                   tag=tag)
                tag = SolutionTag.OK
            except PolygonRequestFailedException as e:
                print("API Error: " + e.comment)
        for x in parser.find_all('p'):
            x.insert_before('\n')
            x.unwrap()
        for x in parser.find_all('span'):
            x.unwrap()
        prob.save_statement(lang="english", problem_statement=Statement(tutorial=latexify_post(analysis.text, 'en')))

    api = authenticate()
    print("problems.list")
    prob = list(api.problems_list(id=polygon_pid))
    if len(prob) == 0:
        print("Problem %s not found" % polygon_pid)
        exit(1)
    prob = prob[0]
    print("problem.enablePoints")
    prob.enable_points(True)
    print("problem.enableGroups")
    prob.enable_groups('tests', True)

    tests_dir = os.path.join(dir, "tests")
    os.mkdir(tests_dir)
    download_tests(dir, tests_dir)

    download_statement()
    download_solutions()

    description = """Imported by usaco-import from %s
The solution probably uses files, instead of stdin/stdout
""" % problem_href
    tutorial = solution_href
    print("problem.saveGeneralDescription: " + description)
    prob.save_general_description(description)
    prob.save_general_tutorial(tutorial=tutorial)
    prob.save_tags(['usaco'])


if __name__ == "__main__":
    main()