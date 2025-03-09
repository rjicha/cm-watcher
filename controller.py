import hashlib
import logging
import threading
import time

from kubernetes import client, config, watch


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

def get_secret_hash(namespace, name):
    """ Generate a hash of the Secret to track changes """
    secret = v1.read_namespaced_secret(name, namespace)
    data_str = "".join([f"{k}:{v}" for k, v in secret.data.items()])
    return hashlib.sha256(data_str.encode()).hexdigest()



def restart_deployments(namespace, resource_name, resource_type):
    """ Restart deployments that reference the ConfigMap or Secret """
    deployments = apps_v1.list_namespaced_deployment(namespace)

    for dep in deployments.items:
        annotations = dep.spec.template.metadata.annotations or {}

        key = f"{resource_type}-hash/{resource_name}"  # eg. "configmap-hash/my-config" or "secret-hash/my-secret"
        if key in annotations:
            logger.info(f"Restarting deployment {dep.metadata.name} due to {resource_type} change...")
            new_hash = (
                get_configmap_hash(namespace, resource_name)
                if resource_type == "configmap"
                else get_secret_hash(namespace, resource_name)
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


def watch_configmaps(namespace):
    """ Watch for ConfigMap changes and trigger deployment restarts """
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_config_map, namespace):
        cm_name = event['object'].metadata.name
        event_type = event['type']
        
        if event_type in ["MODIFIED", "DELETED"]:
            print(f"Detected {event_type} event on ConfigMap {cm_name}")
            restart_deployments(namespace, cm_name, "configmap")


def watch_secrets(namespace):
    """ Watch for Secret changes and trigger deployment restarts """
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_secret, namespace):
        secret_name = event['object'].metadata.name
        event_type = event['type']

        if event_type in ["MODIFIED", "DELETED"]:
            logger.info(f"Detected {event_type} event on Secret {secret_name}")
            restart_deployments(namespace, secret_name, "secret")
            

if __name__ == "__main__":
    namespace = "default"  # todo: pick from env !
    logger.info(f"Watching for ConfigMap & Secret changes in namespace: {namespace} ....")

    # run both watchers in separate threads
    cm_thread = threading.Thread(target=watch_configmaps, args=(namespace,), daemon=True)
    secret_thread = threading.Thread(target=watch_secrets, args=(namespace,), daemon=True)

    cm_thread.start()
    secret_thread.start()

    # keep main thread alive
    while True:
        time.sleep(10)