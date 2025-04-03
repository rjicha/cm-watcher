import unittest
from kube.matcher import hash_pattern_matcher 

class TestMatchesHashPattern(unittest.TestCase):

    def test_valid_configmap(self):
        result = hash_pattern_matcher("configmap-hash/my-config")
        self.assertTrue(result.is_match)
        self.assertEqual(result.resource_type, "configmap")
        self.assertEqual(result.resource_name, "my-config")

    def test_valid_secret(self):
        result = hash_pattern_matcher("secret-hash/my-secret")
        self.assertTrue(result.is_match)
        self.assertEqual(result.resource_type, "secret")
        self.assertEqual(result.resource_name, "my-secret")

    def test_invalid_format(self):
        result = hash_pattern_matcher("app/something")
        self.assertFalse(result.is_match)
        self.assertIsNone(result.resource_type)
        self.assertIsNone(result.resource_name)

    def test_completely_wrong_key(self):
        result = hash_pattern_matcher("random-key")
        self.assertFalse(result.is_match)
        self.assertIsNone(result.resource_type)
        self.assertIsNone(result.resource_name)

if __name__ == "__main__":
    unittest.main()