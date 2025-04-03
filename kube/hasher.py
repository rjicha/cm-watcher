import hashlib
from kubernetes import client

v1 = client.CoreV1Api()


def get_resource_hash(namespace, name, get_func):
    """
    Generate a SHA-256 hash of a Kubernetes resource's data.
    
    :param namespace: Namespace of the resource
    :param name: Name of the resource
    :param get_func: Function to retrieve the resource (e.g., v1.read_namespaced_config_map)
    :return: SHA-256 hash of the resource's data
    """
    resource = get_func(name, namespace)
    if not resource.data:
        return None
    
    # convert data dictionary to a consistent string format
    data_str = "".join([f"{k}:{v}" for k, v in sorted(resource.data.items())])
    
    return hashlib.sha256(data_str.encode()).hexdigest()


def compute_actual_hash(namespace, resource_name, resource_type):
    """ Computes the hash of the given ConfigMap or Secret. """
    compute_func = v1.read_namespaced_config_map if resource_type == "configmap-hash" else v1.read_namespaced_secret
    return get_resource_hash(namespace, resource_name, compute_func)