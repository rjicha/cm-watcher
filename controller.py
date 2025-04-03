import logging
import threading
import time
import signal

from kube.watcher import KubernetesResourceWatcher
from kube.deploy import startup_deployment_check, check_dependent_deployments


# setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


stop_event = threading.Event()

def signal_handler(signum, frame):
    logger.info("Received shutdown signal. Stopping watchers...")
    stop_event.set()
    cm_watcher.stop()
    secret_watcher.stop()


if __name__ == "__main__":
    namespace = "default"  # todo: pick from env !

    logger.info(f"Validating deployments before starting watchers in namespace: {namespace} ...")
    startup_deployment_check(namespace)

    logger.info(f"Watching for ConfigMap & Secret changes in namespace: {namespace} ....")
    cm_watcher = KubernetesResourceWatcher(namespace, "configmap", check_dependent_deployments)
    secret_watcher = KubernetesResourceWatcher(namespace, "secret", check_dependent_deployments)

    # run both watchers in separate threads
    cm_thread = threading.Thread(target=cm_watcher.watch, daemon=True)
    secret_thread = threading.Thread(target=secret_watcher.watch, daemon=True)

    cm_thread.start()
    secret_thread.start()

    # handle SIGTERM & SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # keep the main thread alive, but exit immediately on stop_event
    while not stop_event.is_set():
        time.sleep(1)

    logger.info("Shutdown complete.")