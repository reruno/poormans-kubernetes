### Setup the cluster

**important**: edit `inventory.ini` with values from terraform output 
```
ansible-playbook -i inventory.ini cluster_setup.yaml
```

### Access the cluster 
```
# -D 1080: Opens a SOCKS proxy on local port 1080
# -N: "No command" (just forwards ports, doesn't open a shell)
ssh -D 1080 -q -N user@bastion-host-ip
# in case of this project the command would look like this 
ssh -D 1080 -q -N -J admin@63.177.225.119 admin@10.0.2.180
```

In ~/.kube/config add proxy-url value
```
clusters:
- cluster:
    server: https://10.10.1.5:6443  # Keep the internal IP as is
    certificate-authority-data: ...
    proxy-url: socks5://localhost:1080  # Add this line
  name: my-cluster
```