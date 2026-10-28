"""코어 단위 시험. / Core unit tests."""
import unicodedata
import unittest

import helpers  # noqa: F401  (sys.path 설정)
from habitree.core import io as hio
from habitree.core.markdown import anchors, digest, get_block, links, put_block, slug
from habitree.core.paths import glob_match, is_excluded, nfc
from habitree.core.schema import validate
from habitree.core.textsim import similarity, tokens


class TestPaths(unittest.TestCase):
    def test_nfc_hangul(self):
        nfd = unicodedata.normalize("NFD", "코딩")
        self.assertNotEqual(nfd, "코딩")
        self.assertEqual(nfc(nfd), "코딩")

    def test_glob(self):
        self.assertTrue(glob_match("src/a/b.py", "**/*.py"))
        self.assertTrue(glob_match("b.py", "**/*.py"))
        self.assertTrue(glob_match("src/b.py", "src/*.py"))
        self.assertFalse(glob_match("src/a/b.py", "src/*.py"))
        self.assertTrue(glob_match("docs/문서.md", "docs/*.md"))
        self.assertTrue(glob_match("x/README.md", "README.md"))

    def test_exclude(self):
        self.assertTrue(is_excluded("node_modules/x/y.js", ["node_modules"]))
        self.assertTrue(is_excluded(".habitree/state/s.json", [".habitree/state"]))
        self.assertFalse(is_excluded(".habitree/rules.json", [".habitree/state"]))


class TestMarkdown(unittest.TestCase):
    def test_slug_korean(self):
        self.assertEqual(slug("9. 결정 기록"), "9-결정-기록")
        self.assertEqual(slug("Hello, World!"), "hello-world")
        self.assertEqual(slug("지도 · Map"), "지도--map")

    def test_anchors_duplicates(self):
        a = anchors("# A\n## A\n```\n# not\n```\n")
        self.assertEqual(a, {"a", "a-1"})

    def test_links_skip_code(self):
        text = "[x](a.md)\n`[y](b.md)`\n```\n[z](c.md)\n```\n![i](img.png)"
        self.assertEqual([t for _, t in links(text)], ["a.md", "img.png"])

    def test_blocks(self):
        t = put_block("hello\n", "k", "one")
        self.assertIn("<!-- habitree:begin k -->\none\n<!-- habitree:end k -->", t)
        t2 = put_block(t, "k", "two")
        self.assertEqual(get_block(t2, "k"), "two")
        self.assertTrue(t2.startswith("hello"))
        t3 = put_block("body", "top", "first", where="start")
        self.assertTrue(t3.startswith("<!-- habitree:begin top -->"))
        self.assertEqual(digest(" a \n"), digest("a"))
        with self.assertRaises(ValueError):
            put_block("<!-- habitree:begin k -->\nbroken", "k", "x")


class TestText(unittest.TestCase):
    def test_korean_particles(self):
        self.assertIn("인증", tokens("인증을 확인한다"))
        self.assertGreater(similarity("같은 파일을 여러 번 고치지 않는다", "같은 파일을 조금씩 여러 번 고치지 말 것"), 0.4)
        self.assertLess(similarity("비밀번호를 커밋하지 않는다", "README에 지도를 둔다"), 0.1)

    def test_camel(self):
        self.assertTrue({"same", "call", "streak"} <= tokens("sameCallStreak same_call"))


class TestSchema(unittest.TestCase):
    def test_subset(self):
        schema = {"type": "object", "required": ["a"], "properties": {
            "a": {"type": "integer", "minimum": 1}, "b": {"enum": ["x", "y"]},
            "c": {"anyOf": [{"type": "string"}, {"type": "object"}]}}, "additionalProperties": False}
        self.assertEqual(validate({"a": 1, "b": "x", "c": "s"}, schema), [])
        self.assertTrue(validate({"a": 0}, schema))
        self.assertTrue(validate({"a": 1, "z": 1}, schema))
        self.assertTrue(validate({"a": 1, "c": 3}, schema))
        self.assertTrue(validate({"b": "x"}, schema))


class TestIO(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(hio.read_bytes_text("한글".encode("utf-8-sig")), "한글")
        self.assertEqual(hio.read_bytes_text("한글".encode("cp949")), "한글")


if __name__ == "__main__":
    unittest.main()
