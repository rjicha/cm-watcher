import logging
from kubernetes import client, config
from kube.matcher import hash_pattern_matcher
from kube.hasher import get_resource_hash

logger = logging.getLogger(__name__)

config.load_incluster_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def get_deployments_with_hash_references(namespace):
    """ Returns deployments that contain 'configmap-hash' or 'secret-hash' annotations. """
    deployments = apps_v1.list_namespaced_deployment(namespace)
    filtered_deployments = []

    for dep in deployments.items:
        annotations = dep.spec.template.metadata.annotations or {}

        if any(hash_pattern_matcher(key).is_match for key in annotations):
            filtered_deployments.append(dep)

    return filtered_deployments


def patch_deployment(dep, namespace, annotations):
    """ Patches the deployment to trigger a restart by updating annotations. """
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": annotations
                }
            }
        }
    }
    logger.info(f"Patching deployment {dep.metadata.name} to update annotations.")
    apps_v1.patch_namespaced_deployment(dep.metadata.name, namespace, patch)


def startup_deployment_check(namespace):
    """ Ensure that existing deployment hashes match actual ConfigMap/Secret contents """
    for dep in get_deployments_with_hash_references(namespace):
        annotations = dep.spec.template.metadata.annotations or {}

        annotations_patch = annotations.copy()
        apply_patch = False
        for key, _ in annotations.items():
            hash_pattern_match_result = hash_pattern_matcher(key)
            if (hash_pattern_match_result.is_match is False):
                continue

            check_result = check_deployment(dep, namespace, hash_pattern_match_result.resource_name, hash_pattern_match_result.resource_type)
            if check_result[0] == True:
                apply_patch = True
                annotations_patch[key] = check_result[1][key]

        if (apply_patch == True):
            patch_deployment(dep, namespace, annotations)


def check_dependent_deployments(namespace, resource_name, resource_type):
    """ Restart deployments that reference the ConfigMap or Secret """
    for dep in get_deployments_with_hash_references(namespace):
        check_result = check_deployment(dep, namespace, resource_name, resource_type)
        if check_result[0] == True:
            patch_deployment(dep, namespace, check_result[1])


def check_deployment(deployment, namespace, resource_name, resource_type):
    key = f"{resource_type}-hash/{resource_name}"  # eg. "configmap-hash/my-config" or "secret-hash/my-secret"
    annotations = deployment.spec.template.metadata.annotations or {}

    if not key in annotations:
        return (False, annotations)
    
    logger.info(f"Found deployment {deployment.metadata.name} watching {resource_type} change...")

    compute_func = v1.read_namespaced_config_map if resource_type == "configmap" else v1.read_namespaced_secret
    actual_hash = get_resource_hash(namespace, resource_name, compute_func)

    if annotations[key] == actual_hash:
        logger.info(f"Computed hash for {resource_type} {resource_name} is unchanged. No action required.")
        return(False, annotations)
    else:
        logger.info(f"Mismatch detected for {resource_type} {resource_name} in {deployment.metadata.name}.")
        annotations[key] = actual_hash
        return(True, annotations)