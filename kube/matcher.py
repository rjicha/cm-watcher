import re


HASH_PATTERN = re.compile(r"^(configmap|secret)-hash/(.+)$")


class HashMatch:
    def __init__(self, is_match: bool, resource_type: str = None, resource_name: str = None):
        self.is_match = is_match
        self.resource_type = resource_type
        self.resource_name = resource_name

    def __repr__(self):
        return f"HashMatch(is_match={self.is_match}, resource_type={self.resource_type}, resource_name={self.resource_name})"


def hash_pattern_matcher(key) -> HashMatch:
    """ 
    Check if the key matches the hash pattern and extract the resource type and name. 
    Returns a HashMatch object with:
      - is_match (bool): Whether the key matches
      - resource_type (str): "configmap" or "secret" (without '-hash')
      - resource_name (str): The name of the resource
    """
    match = HASH_PATTERN.match(key)
    return HashMatch(True, match.group(1), match.group(2)) if match else HashMatch(False)