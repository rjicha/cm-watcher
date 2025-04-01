import hashlib
import logging
import threading
import time

from kubernetes import client, config
from kube.watcher import KubernetesResourceWatcher
from kube.hasher import get_resource_hash


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


def restart_deployments(namespace, resource_name, resource_type):
    """ Restart deployments that reference the ConfigMap or Secret """
    deployments = apps_v1.list_namespaced_deployment(namespace)

    for dep in deployments.items:
        annotations = dep.spec.template.metadata.annotations or {}

        key = f"{resource_type}-hash/{resource_name}"  # eg. "configmap-hash/my-config" or "secret-hash/my-secret"
        if key in annotations:
            logger.info(f"Restarting deployment {dep.metadata.name} due to {resource_type} change...")
            new_hash = get_resource_hash(namespace, resource_name,
                v1.read_namespaced_config_map if resource_type == "configmap" else v1.read_namespaced_secret
            )

            annotations[key] = new_hash

            # patch deployment to trigger restart
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
            

if __name__ == "__main__":
    namespace = "default"  # todo: pick from env !
    logger.info(f"Watching for ConfigMap & Secret changes in namespace: {namespace} ....")

    cm_watcher = KubernetesResourceWatcher(namespace, "configmap", v1.list_namespaced_config_map, restart_deployments)
    secret_watcher = KubernetesResourceWatcher(namespace, "secret", v1.list_namespaced_secret, restart_deployments)

    # run both watchers in separate threads
    cm_thread = threading.Thread(target=cm_watcher.watch, daemon=True)
    secret_thread = threading.Thread(target=secret_watcher.watch, daemon=True)

    cm_thread.start()
    secret_thread.start()

    # keep main thread alive
    while True:
        time.sleep(10)