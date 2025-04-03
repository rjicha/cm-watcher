import time
import logging
from kubernetes import client, config, watch

logger = logging.getLogger(__name__)

config.load_incluster_config()
v1 = client.CoreV1Api()


class KubernetesResourceWatcher:
    def __init__(self, namespace, resource_type, restart_callback):
        """
        Generic Kubernetes resource watcher.
        
        :param namespace: Namespace to watch
        :param resource_type: "configmap" or "secret" (for logging)
        :param restart_callback: Function to call when a resource changes
        """
        self.namespace = namespace
        self.resource_type = resource_type
        self.list_func = v1.list_namespaced_config_map if resource_type == "configmap" else v1.list_namespaced_secret
        self.restart_callback = restart_callback
        self.running = True

    def watch(self):
        """ Watches the specified Kubernetes resource and triggers restart_callback on changes. """
        while self.running:
            w = watch.Watch()
            try:
                resource_version = "0"  # start from the latest state
                for event in w.stream(self.list_func, self.namespace, resource_version=resource_version):
                    resource_name = event['object'].metadata.name
                    event_type = event['type']

                    if event_type in ["MODIFIED", "DELETED"]:
                        logger.info(f"Detected {event_type} event on {self.resource_type} {resource_name}")
                        self.restart_callback(self.namespace, resource_name, self.resource_type)
            except client.exceptions.ApiException as e:
                if e.status == 410:
                    logger.warning(f"{self.resource_type.capitalize()} watch expired. Restarting watch...")
                    continue  # restart the loop
                else:
                    logger.error(f"Unexpected error watching {self.resource_type}: {e}")
                    time.sleep(5)  # short delay before retrying to prevent excessive API calls


    def stop(self):
        self.running = False
