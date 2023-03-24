from enum import Enum
from polygon_api import (
    PointsPolicy,
    FeedbackPolicy,
    PolygonRequestFailedException,
)


class GroupScoring(Enum):
    SUM = 1
    GROUP = 2


class FileContents:
    def __init__(self, path):
        self.path = path

    def __call__(self, *args, **kwargs):
        with open(self.path, 'r') as tf:
            return tf.read()

    def __repr__(self):
        return "FileTest { path: %s, description: %s }" % self.path


class MemoryContents:
    def __init__(self, content):
        self.content = content

    def __call__(self, *args, **kwargs):
        return self.content


class Test:
    def __init__(self, content, description, use_in_statements=False, input_for_statements=None,
                 output_for_statements=None, verify=None):
        self.content = content
        self.description = description
        self.use_in_statements = use_in_statements
        self.input_for_statements = input_for_statements
        self.output_for_statements = output_for_statements
        self.verify = verify

    def __call__(self, *args, **kwargs):
        return self.content()


class Group:
    def __init__(self, score, tests, scoring):
        cnt = len(tests)
        self.score = score
        if cnt == 0:
            self.points = []
        elif scoring == GroupScoring.SUM:
            self.points = [score // cnt] * (cnt - score % cnt) + [score // cnt + 1] * (score % cnt)
        else:
            self.points = [score] + [0] * (cnt - 1)
        self.tests = tests
        self.scoring = scoring

    def __repr__(self):
        return "Group { score: %d, tests: %s, scoring: %s }" % (self.score, str(self.tests), str(self.scoring))


def upload_groups(prob, groups):
    test_index = 0
    for gid, g in enumerate(groups):
        if len(g.tests) == 0:
            continue
        for t, cur_score in zip(g.tests, g.points):
            test_contents = t()
            test_index += 1
            print("problem.saveTest %d with group %d and score %s"
                  % (test_index, gid, str(cur_score)))
            try:
                prob.save_test('tests', test_index, test_contents,
                               test_group=gid,
                               test_points=cur_score,
                               test_description=t.description,
                               check_existing=True,
                               test_use_in_statements=t.use_in_statements,
                               test_input_for_statements=t.input_for_statements,
                               test_output_for_statements=t.output_for_statements,
                               verify_input_output_for_statements=t.verify)
            except PolygonRequestFailedException as exc:
                print(exc.comment, "skipped")
        if g.scoring == GroupScoring.SUM:
            print("problem.saveTestGroup group %d, pointsPolicy=EACH_TEST, feedbackPolicy=COMPLETE" % gid)
            prob.save_test_group('tests', gid,
                                 points_policy=PointsPolicy.EACH_TEST,
                                 feedback_policy=FeedbackPolicy.COMPLETE)
        else:
            print("problem.saveTestGroup group %d, pointsPolicy=COMPLETE_GROUP, feedbackPolicy=ICPC" % gid)
            prob.save_test_group('tests', gid,
                                 points_policy=PointsPolicy.COMPLETE_GROUP,
                                 feedback_policy=FeedbackPolicy.ICPC)
