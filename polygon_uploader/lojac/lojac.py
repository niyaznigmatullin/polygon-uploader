from polygon_api import (
    FileType,
    SolutionTag,
    ProblemInfo,
    Statement,
    PolygonRequestFailedException,
    ResourceAdvancedProperties,
    Stage,
    Asset
)
import html
import sys
import os
import zipfile
import re
import yaml
from polygon_uploader.common import *
import hashlib

__version__ = '1.0'
__author__ = 'Niyaz Nigmatullin'

if len(sys.argv) < 3 or len(sys.argv) > 4:
    print("Usage: lojacimport <loj problem id> <polygon problem id> [<number of tests in groups separated by comma>]")
    print("Example: lojacimport 3208 aplusb-light 1,1,3,2,3,3,4")
    exit(239)


def main():
    loj_pid = sys.argv[1]
    polygon_pid = sys.argv[2]
    groupsizes = [] if len(sys.argv) < 4 else [int(x) for x in sys.argv[3].split(',')]

    problem_href = 'https://loj.ac/problem/%s' % loj_pid
    solutions_href = 'https://loj.ac/problem/%s/statistics/fastest' % loj_pid
    testdata_href = 'https://loj.ac/problem/%s/testdata/download' % loj_pid
    submission_href = 'https://loj.ac/submission/%s'

    dir = create_temporary_directory(prefix='_loj_%s' % loj_pid)

    def get_main_page():
        nonlocal main_page
        if main_page is None:
            main_page = download_web_page(problem_href)
        return main_page

    def download_sample_tests():
        reg_exp = re.compile(r"<pre[^<]*<code>([^<]*)[^<]</code>[^<]*</pre", re.DOTALL)
        return reg_exp.findall(get_main_page())[0::2]

    def set_tl_and_ml():
        s = get_main_page()
        ml_rexp = re.compile(r"<span class[^>]*>[^0-9<]*(\d+)[^0-9<M]*MiB[^<]*</span>", re.DOTALL)
        ml = ml_rexp.findall(s)
        if len(ml) > 0:
            ml = int(ml[0])
        else:
            ml = None
        tl_rexp = re.compile(r"<span class[^>]*>[^0-9<]*(\d+)[^0-9<m]*ms[^<]*</span>", re.DOTALL)
        tl = tl_rexp.findall(s)
        if len(tl) > 0:
            tl = int(tl[0])
        else:
            tl = None
        print('Set ML = %s MiB and TL = %s ms' % (str(ml), str(tl)))
        prob.update_info(ProblemInfo(time_limit=tl, memory_limit=ml))

    def set_statement_scoring():
        for lang, subtask, points in [("russian", "Подзадача", "баллов"), ("english", "Subtask", "points")]:
            s = '\\begin{tabular}{ll}\n'
            for group, score in enumerate(group_scores, start=1):
                s += "\\textbf{%s %d (%d %s):} & \\\\\n" % (subtask, group, score, points)
            s += '\\end{tabular}\n'
            print("problem.saveStatement lang=%s" % lang)
            prob.save_statement(lang, Statement(output=s))

    def download_tests(dir, tests_dir):
        tests_archive = os.path.join(dir, "tests.zip")
        download_file_to(testdata_href, tests_archive)
        print(tests_archive, "downloaded")
        zip_archive = zipfile.ZipFile(tests_archive, 'r')
        file_list = zip_archive.namelist()

        def file_to_test(name):
            return FileTest(os.path.join(tests_dir, name), 'lojacimport: filename = %s' % name)

        if 'data.yml' in file_list:
            zip_archive.extractall(path=tests_dir, members=["data.yml"])
            with open(os.path.join(tests_dir, 'data.yml'), "r", encoding="utf-8") as dy:
                f = yaml.load(dy.read(), Loader=yaml.BaseLoader)
            input_mask = f['inputFile'].replace('#', '%s')

            for i, subtask in enumerate(f['subtasks']):
                if subtask['score'] == 0:
                    f['subtasks'] = [subtask] + f['subtasks'][:i] + f['subtasks'][i+1:]
                    break

            groups = []

            if int(f['subtasks'][0]['score']) != 0:
                print("No group with score = 0, downloading sample tests from the web page")
                description = 'lojacimport: parsed page %s' % problem_href
                sample_tests = [MemoryTest(x, description) for x in download_sample_tests()]
                groups.append(Group(0, sample_tests, GroupScoring.SUM))

            to_extract = []
            for group, sub in enumerate(f['subtasks'], start=len(groups)):
                score = sub['score']
                if sub['type'] != 'min':
                    raise Exception("Only min is supported")
                tests = []
                for t in sub['cases']:
                    name = input_mask % t
                    to_extract.append(name)
                    tests.append(file_to_test(name))
                groups.append(Group(int(score), tests, GroupScoring.GROUP))

            nonlocal group_scores
            group_scores = [g.score for gid, g in enumerate(groups) if gid != 0]

            print("Extracting %d tests to " % len(to_extract) + tests_dir)
            zip_archive.extractall(path=tests_dir, members=to_extract)
            upload_groups(prob, groups)

            if 'specialJudge' in f:
                checker = f['specialJudge']
                checker_name = checker['fileName']
                checker_language = checker['language']
                zip_archive.extract(checker_name, dir)
                print("Adding and setting checker file with name %s" % checker_name)
                with open(os.path.join(dir, checker_name), "r", encoding="utf-8") as cf:
                    prob.save_file(FileType.SOURCE, checker_name, cf.read())
                prob.set_checker(checker_name)
            else:
                print("No special judge, setting std::ncmp.cpp as checker")
                prob.set_checker("std::ncmp.cpp")
            if 'extraSourceFiles' in f:
                extra = [x for x in f['extraSourceFiles'] if x['language'] == 'cpp']
                if len(extra) == 0:
                    print("WARNING: No extra source files for C++")
                else:
                    extra = extra[0]
                    extra = extra['files']
                    print(extra)
                    for e_file in extra:
                        print(e_file)
                        e_name = e_file['name']
                        e_dest = e_file['dest']
                        zip_archive.extract(e_name, dir)
                        print("Adding extra source file %s" % e_dest)
                        with open(os.path.join(dir, e_name), "r", encoding="utf-8") as ef:
                            props = ResourceAdvancedProperties(for_types="cpp.*",
                                                               stages=[Stage.COMPILE],
                                                               assets=[Asset.SOLUTION])
                            prob.save_file(FileType.RESOURCE, e_dest, ef.read(), resource_advanced_properties=props)

        else:
            sample_tests = download_sample_tests()
            hashes = set(hashlib.md5(x) for x in sample_tests)
            groups = [Group(0, [lambda: x for x in sample_tests], GroupScoring.SUM)]
            testlist = [x for x in file_list if x.endswith('.in')]
            testlist.sort(key=lambda x: int(re.match(r'.*\D(\d+).in', x).group(1)))
            print('tests = ', testlist)
            zip_archive.extractall(path=tests_dir, members=testlist)
            print(tests_archive, 'extracted to', tests_dir)

            def is_sample(name):
                with os.path.join(tests_dir, name) as tf:
                    return hashlib.md5(tf.read()) in hashes

            testlist = list(filter(lambda x: not is_sample(x), testlist))

            if len(groupsizes) > 0:
                cnt = len(testlist)
                points = [100 // cnt] * (cnt - 100 % cnt) + [100 // cnt + 1] * (100 % cnt)
                for c in groupsizes:
                    score = sum(points[:c])
                    tests = [file_to_test(x) for x in testlist[:c]]
                    groups.append(Group(score, tests, GroupScoring.GROUP))
                    testlist = testlist[c:]
                    points = points[c:]
            else:
                groups.append(Group(100, [file_to_test(x) for x in testlist], GroupScoring.SUM))

    def download_solutions():
        page = download_web_page(solutions_href)
        submissions = list(set(int(x) for x in re.findall(r'href="/submission/(\d+)"', page)))
        tag = SolutionTag.MA
        uploaded = 0
        for sub_id in submissions:
            if uploaded >= 3:
                break
            try:
                submission_page = download_web_page(submission_href % sub_id)
                code = [x for x in submission_page.splitlines() if x.startswith("const format")][0]
                start = code.find('"')
                end = code.rfind('"')
                code = code[start + 1:end]
                code = re.sub(r'</?span[^>]*>', '', html.unescape(code.encode('ascii').decode('unicode-escape')))
                print("problem.saveSolution %s.cpp language cpp.g++17" % sub_id)
                prob.save_solution("%s.cpp" % sub_id, code, "cpp.g++17", tag)
                tag = SolutionTag.OK
                uploaded += 1
            except Exception as exc:
                print("Solution upload error: " + str(exc))

    api = authenticate()
    print("problems.list")
    prob = list(api.problems_list(id=polygon_pid))
    if len(prob) == 0:
        print("Problem %s not found" % polygon_pid)
        exit(1)
    prob = prob[0]
    group_scores = None
    main_page = None
    print("problem.enablePoints")
    prob.enable_points(True)
    print("problem.enableGroups")
    prob.enable_groups('tests', True)

    tests_dir = os.path.join(dir, "tests")
    os.mkdir(tests_dir)
    download_tests(dir, tests_dir)

    download_solutions()

    set_tl_and_ml()
    if group_scores is not None:
        set_statement_scoring()

    description = """Imported by lojacimport from %s
Statements, group dependencies should be imported manually
The solution is taken among random correct solutions on loj.ac
""" % problem_href
    print("problem.saveGeneralDescription: " + description)
    prob.save_general_description(description)


if __name__ == "__main__":
    main()