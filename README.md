# Install minikube

```sh
$ sudo apt update
$ sudo apt install -y curl conntrack
$ curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
$ sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

# Start minikube
```sh
$ minikube start --driver=docker
```

# Force current shell to use minikube's docker env
```sh
$ eval $(minikube docker-env)
```

# Build the cm-watcher
```sh
$ docker build -t cm-watcher:latest .
```

# Install the chart
```sh
$ helm install/upgrade test-deploy -f ./config/values.yaml ./charts/
```

# Test the restart on cm patch
```sh
$ kubectl patch configmap watched-configmap -n default --type='merge' -p '{"data":{"LOG_LEVEL":"debug"}}'
```

# Test the restart on secret patch
```sh
$ kubectl patch secret watched-secret -n default --type='merge' -p '{"data":{"API_KEY":"'$(echo -n "newSecretValue" | base64)'"}}'
```