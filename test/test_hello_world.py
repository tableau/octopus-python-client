import unittest
from octopus_python_client import hello_world


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def test_text_compare_true(self):
        self.assertTrue(hello_world.text_compare("asdf", "asdf"))

    def test_text_compare_false(self):
        self.assertFalse(hello_world.text_compare("asdf", "foo"))


if __name__ == '__main__':
    unittest.main()
