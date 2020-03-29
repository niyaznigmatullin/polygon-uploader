import requests
from polygon_client import Polygon, PointsPolicy, FeedbackPolicy, FileType, SolutionTag
import html
import sys
import tempfile
import atexit
import os
import shutil
import zipfile
import re
import yaml

__version__ = '1.0'
__author__ = 'Niyaz Nigmatullin'

if len(sys.argv) < 3 or len(sys.argv) > 4:
    print("Usage: python3 main.py <loj problem id> <polygon problem id> [<number of tests in groups separated by comma>]")
    print("Example: python3 main.py 3208 aplusb-light 1,1,3,2,3,3,4")
    exit(239)


def authenticate():
    global polygon_url, api_key, api_secret
    default_polygon_url = "https://polygon.codeforces.com"

    authentication_file = os.path.join(os.path.expanduser('~'), '.config', 'lojacimport', 'auth.yaml')
    if os.path.exists(authentication_file):
        with open(authentication_file, 'r') as fo:
            auth_data = yaml.load(fo, Loader=yaml.BaseLoader)
        polygon_url = auth_data.get('polygon_url')
        api_key = auth_data.get('api_key')
        api_secret = auth_data.get('api_secret')

    if not os.path.exists(authentication_file) or not api_key or not api_secret:
        print('WARNING: Authentication data will be stored in plain text in {}'.format(authentication_file))
        api_key = input('API Key: ')
        api_secret = input('API Secret: ')
        polygon_url = default_polygon_url
        os.makedirs(os.path.dirname(authentication_file), exist_ok=True)
        with open(authentication_file, 'w') as fo:
            auth_data = {
                'polygon_url': polygon_url,
                'api_key': api_key,
                'api_secret': api_secret
            }
            yaml.dump(auth_data, fo, default_flow_style=False)
        print('Authentication data is stored in {}'.format(authentication_file))
    polygon_url += '/api'

def main():
    loj_pid = sys.argv[1]
    polygon_pid = sys.argv[2]
    groupsizes = [] if len(sys.argv) < 4 else [int(x) for x in sys.argv[3].split(',')]

    problem_href = 'https://loj.ac/problem/%s' % loj_pid
    solutions_href = 'https://loj.ac/problem/%s/statistics/fastest' % loj_pid
    testdata_href = 'https://loj.ac/problem/%s/testdata/download' % loj_pid
    submission_href = 'https://loj.ac/submission/%s'

    dir = tempfile.mkdtemp(prefix='_loj_%s' % loj_pid)

    def cleaner(dir):
        def docleaner():
            shutil.rmtree(dir)
        return docleaner

    atexit.register(cleaner(dir))

    def http_get(link):
        r = requests.get(link)
        if r.status_code != 200:
            print(r.status_code, "error")
            exit(1)
        return r

    def download_file_to(link, path):
        r = http_get(link)
        print("Downloading file %s (%s bytes)" % (path, r.headers['Content-length']))
        with open(path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

    class TestCounter:
        test_index = 0

        def next(self):
            self.test_index += 1
            return self.test_index

    def download_sample_tests(counter):
        r = http_get(problem_href)
        reg_exp = re.compile(r"<pre[^<]*<code>([^<]*)[^<]</code>[^<]*</pre", re.DOTALL)
        z = reg_exp.findall(r.text)[0::2]
        for i in range(len(z)):
            prob.save_test('tests', counter.next(), z[i],
                           test_group='0',
                           test_description='lojac import: sample test from %s' % problem_href,
                           test_use_in_statements=True,
                           check_existing=True)

    def download_tests(dir, tests_dir, counter):
        tests_archive = os.path.join(dir, "tests.zip")
        download_file_to(testdata_href, tests_archive)
        print(tests_archive, "downloaded")
        zip_archive = zipfile.ZipFile(tests_archive, 'r')
        file_list = zip_archive.namelist()
        if 'data.yml' in file_list:
            zip_archive.extractall(path=tests_dir, members=["data.yml"])
            with open(os.path.join(tests_dir, 'data.yml'), "r", encoding="utf-8") as dy:
                f = yaml.load(dy.read())
            input_mask = f['inputFile'].replace('#', '%s')
            to_extract = []
            groups = {}
            need_sample = f['subtasks'][0]['score'] != 0
            if need_sample:
                print("No group with score = 0, downloading sample tests from the web page")
                download_sample_tests(counter)
            for group, sub in enumerate(f['subtasks'], start=1 if need_sample else 0):
                score = sub['score']
                if sub['type'] != 'min':
                    raise Exception("Only min is supported")
                groups[group] = {'score': score}
                tests = []
                for testId, t in enumerate(sub['cases'], start=1):
                    name = input_mask % t
                    to_extract.append(name)
                    tests.append(name)
                groups[group]['tests'] = tests
            print("Extracting %d tests to " % len(to_extract) + tests_dir)
            zip_archive.extractall(path=tests_dir, members=to_extract)
            for gid, g in groups.items():
                cur_score = g['score']
                for t in g['tests']:
                    with open(os.path.join(tests_dir, t), 'r') as tf:
                        testIndex = counter.next()
                        print("problem.saveTest %d with group %d and score %s"
                              % (testIndex, gid, str(cur_score) if cur_score is not None else "None"))
                        prob.save_test('tests', testIndex, tf.read(),
                                       test_group=gid,
                                       test_points=cur_score,
                                       test_description='lojac import: filename="%s"' % t,
                                       check_existing=True,
                                       test_use_in_statements=True if gid == 0 else None)
                    cur_score = None
                if gid == 0:
                    print("problem.saveTestGroup group %d, pointsPolicy=EACH_TEST, feedbackPolicy=COMPLETE" % gid)
                    prob.save_test_group('tests', gid,
                                         points_policy=PointsPolicy.EACH_TEST,
                                         feedback_policy=FeedbackPolicy.COMPLETE)
                else:
                    print("problem.saveTestGroup group %d, pointsPolicy=COMPLETE_GROUP, feedbackPolicy=ICPC" % gid)
                    prob.save_test_group('tests', gid,
                                         points_policy=PointsPolicy.COMPLETE_GROUP,
                                         feedback_policy=FeedbackPolicy.ICPC)
            if 'specialJudge' in f:
                checker = f['specialJudge']
                checker_name = checker['fileName']
                checker_language = checker['language']
                zip_archive.extract(checker_name, dir)
                with open(os.path.join(dir, checker_name), "r", encoding="utf-8") as cf:
                    prob.save_file(FileType.SOURCE, checker_name, cf.read())

        else:
            download_sample_tests(counter)
            testlist = [x for x in file_list if x.endswith('.in')]  # TODO parse table on the page
            print('tests = ', testlist)
            zip_archive.extractall(path=tests_dir, members=testlist)
            print(tests_archive, 'extracted to', tests_dir)
            for i in range(1, len(groupsizes)):
                groupsizes[i] += groupsizes[i - 1]
            for x in testlist:
                y = re.match(r'.*\D(\d+).in', x)
                tnum = int(y.group(1))
                group = 0
                while groupsizes[group] < tnum:
                    group += 1
                tnum -= 0 if group == 0 else groupsizes[group - 1]
                group += 1
                os.rename(os.path.join(tests_dir, x), os.path.join(tests_dir, '%02d-%02d.txt' % (int(group), int(tnum))))

    def download_solutions():
        r = http_get(solutions_href)
        submissions = list(set(int(x) for x in re.findall(r'href="/submission/(\d+)"', r.text)))[:3]
        tag = SolutionTag.MA
        for sub_id in submissions:
            r = http_get(submission_href % sub_id)
            code = [x for x in r.text.splitlines() if x.startswith("const format")][0]
            start = code.find('"')
            end = code.rfind('"')
            code = code[start + 1:end]
            code = re.sub(r'</?span[^>]*>', '', html.unescape(code.encode('ascii').decode('unicode-escape')))
            print("problem.saveSolution %s.cpp language cpp.g++17" % sub_id)
            prob.save_solution("%s.cpp" % sub_id, code, "cpp.g++17", tag)
            tag = SolutionTag.OK

    authenticate()
    api = Polygon(polygon_url, api_key, api_secret)
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
    download_tests(dir, tests_dir, TestCounter())

    download_solutions()


if __name__ == "__main__":
    main()