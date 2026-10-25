"""upload_groups against a fake Polygon problem that refuses duplicate test inputs like the real one."""
from polygon_api import PolygonRequestFailedException

from polygon_uploader.common import Group, GroupScoring, MemoryContents, upload_groups
from polygon_uploader.common import Test as UploadTest  # not Test*: pytest would collect it


class FakeProblem:
    def __init__(self):
        self.tests = {}

    def save_test(self, testset, index, content, **kwargs):
        for other, (other_content, _) in self.tests.items():
            if other != index and other_content == content:
                raise PolygonRequestFailedException("testInput: Test coincides with test #%d." % other)
        self.tests[index] = (content, kwargs)

    def save_test_group(self, testset, group, **kwargs):
        pass


def test_duplicates_leave_no_numbering_gaps():
    # NAC 2026 leakingsantassecrets: 18 duplicate inputs left gaps, and Polygon refused to build
    # ("Tests are enumerated incorrectly"); there is no API to delete tests
    contents = ["2\n0 1\n", "3\n0 1 2\n", "2\n0 1\n", "4\n0 1 2 3\n", "3\n0 1 2\n", "1\n0\n"]
    tests = [UploadTest(MemoryContents(c), "secret/%d.in" % i) for i, c in enumerate(contents)]
    prob = FakeProblem()
    upload_groups(prob, [Group(0, [], GroupScoring.SUM), Group(100, tests, GroupScoring.SUM)])
    assert sorted(prob.tests) == [1, 2, 3, 4]
    assert [prob.tests[i][1]["test_description"] for i in range(1, 5)] == [
        "secret/0.in", "secret/1.in", "secret/3.in", "secret/5.in"]
