import logging
from kubernetes import client, config, watch
import hashlib
import time


# setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# load cluster config
config.load_incluster_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def get_configmap_hash(namespace, name):
    """ Generate a hash of the ConfigMap to track changes """
    cm = v1.read_namespaced_config_map(name, namespace)
    data_str = "".join([f"{k}:{v}" for k, v in cm.data.items()])
    return hashlib.sha256(data_str.encode()).hexdigest()


def restart_deployments(namespace, configmap_name):
    """ Restart deployments that reference the ConfigMap """
    deployments = apps_v1.list_namespaced_deployment(namespace)
    
    for dep in deployments.items:
        annotations = dep.spec.template.metadata.annotations or {}
        
        # check the ref from deploy -> cm
        if f"configmap-hash/{configmap_name}" in annotations:
            logger.info(f"Restarting deployment {dep.metadata.name} due to ConfigMap change...")
            annotations[f"configmap-hash/{configmap_name}"] = get_configmap_hash(namespace, configmap_name)
            
            # the deployment patch should trigger restart & also persist the new hash
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": annotations
                        }
                    }
                }
            }
            apps_v1.patch_namespaced_deployment(dep.metadata.name, namespace, patch)

def watch_configmaps(namespace):
    """ Watch for ConfigMap changes and trigger deployment restarts """
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_config_map, namespace):
        cm_name = event['object'].metadata.name
        event_type = event['type']
        
        if event_type in ["MODIFIED", "DELETED"]:
            print(f"Detected {event_type} event on ConfigMap {cm_name}")
            restart_deployments(namespace, cm_name)

if __name__ == "__main__":
    namespace = "default"  # todo: pick from env !
    logger.info(f"Watching for ConfigMap changes in namespace: {namespace} ....")
    watch_configmaps(namespace)