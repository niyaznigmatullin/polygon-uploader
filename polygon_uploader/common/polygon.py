from enum import Enum
from polygon_api import (
    PointsPolicy,
    FeedbackPolicy,
    PolygonRequestFailedException,
)


class GroupScoring(Enum):
    SUM = 1
    GROUP = 2


class FileTest:
    def __init__(self, path, description):
        self.path = path
        self.description = description

    def __call__(self, *args, **kwargs):
        with open(self.path, 'r') as tf:
            return tf.read()


class MemoryTest:
    def __init__(self, content, description):
        self.content = content
        self.description = description

    def __call__(self, *args, **kwargs):
        return self.content


class Group:
    def __init__(self, score, tests, scoring):
        cnt = len(tests)
        self.score = score
        if scoring == GroupScoring.SUM:
            self.points = [score // cnt] * (cnt - score % cnt) + [score // cnt + 1] * (score % cnt)
        else:
            self.points = [score] + [0] * (cnt - 1)
        self.tests = tests
        self.scoring = scoring


def upload_groups(prob, groups):
    test_index = 0
    for gid, g in enumerate(groups):
        for t, cur_score in zip(g.tests, g.points):
            test_contents = t()
            test_index += 1
            print("problem.saveTest %d with group %d and score %s"
                  % (test_index, gid, str(cur_score)))
            while True:
                try:
                    prob.save_test('tests', test_index, test_contents,
                                   test_group=gid,
                                   test_points=cur_score,
                                   test_description=t.description,
                                   check_existing=True,
                                   test_use_in_statements=True if gid == 0 else None)
                    break
                except PolygonRequestFailedException as exc:
                    skip = False
                    while True:
                        repl = input("%s Retry, Skip or Terminate (r/s/t): " % exc.comment).lower()
                        if repl in ['r', 's', 't']:
                            if repl == 't':
                                raise exc
                            elif repl == 's':
                                skip = True
                                break
                    if skip:
                        break
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
