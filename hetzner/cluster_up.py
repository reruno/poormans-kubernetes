import argparse
import subprocess
import os
import sys
import json
import time
import atexit

# ==========================================
# 1. Inventory Generation Logic
# ==========================================
def generate_inventory(input_file, output_file, ssh_key_path):
    """
    Generates an Ansible inventory INI file from a Terraform output JSON file.
    Includes logic for [volume-node].
    """
    print(f"Generating Ansible inventory: {output_file}...")
    
    try:
        with open(input_file, 'r') as f:
            tf_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}.")
        sys.exit(1)

    # 1. Extract Data
    dns_root_records = tf_data.get('dns_root_record_ip', {}).get('value', {})
    root_ip_address = next(iter(dns_root_records.values())) if dns_root_records else None
    
    private_ips = tf_data.get('server_private_ips', {}).get('value', {})
    public_ips = tf_data.get('server_public_ips', {}).get('value', {})
    
    # Extract Volume Node Info
    # This returns something like: {'node-2': '46.224.86.61'}
    volume_data = tf_data.get('volume_node_ip', {}).get('value', {})
    # We only care about the key (e.g., "node-2") to match it to the worker alias
    volume_node_name = next(iter(volume_data.keys())) if volume_data else None

    if not private_ips:
        print("Error: 'server_private_ips' data not found in Terraform output.")
        sys.exit(1)

    # 2. Determine Bastion Logic
    bastion_ip = None
    for node, ip in public_ips.items():
        if ip != root_ip_address:
            bastion_ip = ip
            break 
    
    if not bastion_ip and public_ips:
        bastion_ip = list(public_ips.values())[0]

    master_lines = []
    worker_lines = []
    volume_lines = []  # List to hold the alias for the volume node
    lines = []
    
    # 3. Build [all] Section and identify roles
    lines.append("[all]")
    node_names = sorted(private_ips.keys())
    worker_idx = 1
    
    for node_name in node_names:
        private_ip = private_ips[node_name]
        
        # Determine Alias
        if node_name in dns_root_records:
            host_alias = "k8s-control-plane"
            lines.append(f"{host_alias} ansible_host={private_ip}")
            master_lines.append(host_alias)
        else:
            host_alias = f"k8s-worker-node{worker_idx}"
            lines.append(f"{host_alias}  ansible_host={private_ip}")
            worker_lines.append(host_alias)
            worker_idx += 1
        
        # Check if this specific node is the volume node
        if node_name == volume_node_name:
            volume_lines.append(host_alias)
            
    lines.append("") 

    # [kube-master] Section
    lines.append("[kube-master]")
    lines.extend(master_lines)
    lines.append("")

    # [kube-node] Section
    lines.append("[kube-node]")
    lines.extend(worker_lines)
    lines.append("")

    # [volume-node] Section (NEW)
    lines.append("[volume-node]")
    lines.extend(volume_lines)
    lines.append("")

    # [all:vars] Section
    lines.append("[all:vars]")
    lines.append("ansible_user=root")
    lines.append(f"ansible_ssh_private_key_file={ssh_key_path}")
    
    # SSH Arguments
    if bastion_ip:
        lines.append(f"# bastion host (Using IP: {bastion_ip})")
        proxy_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -W %h:%p -q root@{bastion_ip}"
        lines.append(f"ansible_ssh_common_args='-o ProxyCommand=\"{proxy_cmd}\" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'")
    else:
        lines.append("# No suitable bastion host found")
        lines.append("ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'")

    # Write to File
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Inventory saved successfully to {output_file}")
    
# ==========================================
# 2. Helper Functions
# ==========================================
def cleanup_known_hosts(tf_output_path):
    """
    Removes the cluster's public and private IPs from the user's known_hosts file
    to prevent 'Remote Host Identification Has Changed' errors.
    """
    print("\n--- Cleaning up known_hosts for cluster IPs ---")
    try:
        with open(tf_output_path, 'r') as f:
            data = json.load(f)
        
        ips_to_clean = set()
        
        # Collect Public IPs
        public_ips = data.get('server_public_ips', {}).get('value', {})
        for ip in public_ips.values():
            ips_to_clean.add(ip)
        
        # Collect Private IPs
        private_ips = data.get('server_private_ips', {}).get('value', {})
        for ip in private_ips.values():
            ips_to_clean.add(ip)
            
        for ip in ips_to_clean:
            # We clean both the raw IP and the IP with port 22 (common variation)
            subprocess.call(["ssh-keygen", "-R", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.call(["ssh-keygen", "-R", f"[{ip}]:22"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
    except Exception as e:
        print(f"Warning: Failed to clean known_hosts: {e}")

def wait_for_ssh(inventory_path, ansible_dir, retries=30, delay=10):
    """Polls the hosts using ansible ping until they are reachable."""
    print(f"\n--- Waiting for SSH to be ready on all nodes (max {retries*delay}s) ---")
    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    for i in range(retries):
        try:
            subprocess.check_call(
                ["ansible", "all", "-m", "ping", "-i", inventory_path],
                cwd=ansible_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env
            )
            print("\nSSH is ready on all nodes!")
            return True
        except subprocess.CalledProcessError:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(delay)
    print("\nTimeout: specific nodes are still unreachable.")
    return False

def get_cluster_info(tf_output_path):
    """
    Parses Terraform output to get Master Public IP (for MetalLB), 
    Master Private IP (for SCP), and Bastion IP.
    """
    with open(tf_output_path, 'r') as f:
        data = json.load(f)
    
    # Get Root/Master info
    dns_root = data.get('dns_root_record_ip', {}).get('value', {})
    master_public_ip = next(iter(dns_root.values())) if dns_root else None
    
    # Determine Master Private IP (Assuming the node name in dns_root matches a key in server_private_ips)
    private_ips = data.get('server_private_ips', {}).get('value', {})
    master_node_name = next(iter(dns_root.keys())) if dns_root else None
    master_private_ip = private_ips.get(master_node_name)
    
    # Determine Bastion IP
    public_ips = data.get('server_public_ips', {}).get('value', {})
    bastion_ip = None
    for node, ip in public_ips.items():
        if ip != master_public_ip:
            bastion_ip = ip
            break
    if not bastion_ip and public_ips:
        bastion_ip = list(public_ips.values())[0]
        
    return master_public_ip, master_private_ip, bastion_ip

def patch_kubeconfig(filepath, proxy_url="socks5://localhost:1080"):
    """
    Reads the kubeconfig file and inserts the proxy-url line into the cluster config.
    """
    print(f"Patching {filepath} with proxy-url: {proxy_url}")
    new_lines = []
    patched = False
    
    with open(filepath, 'r') as f:
        for line in f:
            new_lines.append(line)
            # Find the server definition and append proxy-url after it
            if "server: https://" in line and not patched:
                # Calculate indentation of the 'server' key to match it
                indentation = line[:line.find('server')]
                new_lines.append(f"{indentation}proxy-url: {proxy_url}\n")
                patched = True
                
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    print("Kubeconfig patched successfully.")

def start_socks_proxy(bastion_ip, master_ip, ssh_key_path):
    """
    Starts a background SSH SOCKS5 proxy on localhost:1080.
    Returns the subprocess object.
    """
    print("Establishing SOCKS5 tunnel for Terraform...")
    
    # Common SSH options to avoid prompts and suppress output
    # options are placed BEFORE arguments to ensure they are parsed correctly
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",     # Accept new keys automatically
        "-o", "UserKnownHostsFile=/dev/null", # Do not read or write to user's known_hosts
        "-o", "GlobalKnownHostsFile=/dev/null",
        "-o", "CheckHostIP=no",               # Do not verify IP address in known_hosts
        "-D", "1080",  # Dynamic forwarding (SOCKS)
        "-q",          # Quiet mode
        "-N"           # Do not execute a remote command (just forward ports)
    ]

    if bastion_ip:
        # We use ProxyCommand instead of -J to explicitly force StrictHostKeyChecking=no 
        # on the bastion connection as well.
        proxy_cmd = (
            f"ssh "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o GlobalKnownHostsFile=/dev/null "
            "-o CheckHostIP=no "
            f"-i {ssh_key_path} "
            "-W %h:%p "
            "-q "
            f"root@{bastion_ip}"
        )
        
        # Options first, then ProxyCommand, then Identity, then Target
        cmd = ["ssh"] + ssh_opts + [
            "-o", f"ProxyCommand={proxy_cmd}",
            "-i", ssh_key_path,
            f"root@{master_ip}"
        ]
    else:
        # Direct connection: Options first, then Identity, then Target
        cmd = ["ssh"] + ssh_opts + [
            "-i", ssh_key_path,
            f"root@{master_ip}"
        ]

    # Start the process in the background
    proc = subprocess.Popen(cmd)
    
    # Give it a moment to establish connection
    time.sleep(3)
    
    # Check if it died immediately
    if proc.poll() is not None:
        print("Error: SSH proxy failed to start.")
        sys.exit(1)
        
    print("SOCKS5 tunnel established on localhost:1080.")
    return proc

# ==========================================
# 3. Main Execution Flow
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Provision Hetzner Cluster, generate Inventory, run Ansible, and Setup K8s Apps.")
    
    parser.add_argument("--hetzner-zone-domain", required=True, help="The domain zone (e.g., example.com)")
    parser.add_argument("--hetzner-token", required=True, help="Hetzner Cloud API Token")
    parser.add_argument("--ssh-public-key-path", required=True, help="Path to SSH public key")
    parser.add_argument("--ssh-private-key-path", required=True, help="Path to SSH private key")
    parser.add_argument("--acme-email", required=True, help="Email for Let's Encrypt (ACME)")

    args = parser.parse_args()

    # Directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    terraform_infra_dir = os.path.join(script_dir, "terraform")
    terraform_k8s_dir = os.path.join(script_dir, "terraform-kubernetes")
    ansible_dir = os.path.abspath(os.path.join(script_dir, "..", "ansible"))
    ansible_playbook_path = os.path.join(ansible_dir, "cluster_setup.yaml")

    # Files
    tf_output_json_path = os.path.join(script_dir, "tmpfile_terraform_output.json")
    inventory_ini_path = os.path.join(script_dir, "tmpfile_inventory.ini")
    local_kubeconfig_path = os.path.join(script_dir, "tmpfile_kube_config")
    readme_path = os.path.join(script_dir, "tmpfile_readme.txt")
    
    # Nginx App Manifests
    nginx_manifest_src = os.path.join(script_dir, "example-kubernetes", "nginx-app-http-redirect.yaml")
    nginx_manifest_tmp = os.path.join(script_dir, "tmpfile_nginx-app-http-redirect.yaml")

    # Env Vars
    tf_env = os.environ.copy()
    tf_env["TF_VAR_hcloud_token"] = args.hetzner_token
    tf_env["TF_VAR_hetzner_zone_domain"] = args.hetzner_zone_domain
    tf_env["TF_VAR_ssh_public_key_path"] = args.ssh_public_key_path

    print(f"--- Phase 1: Infrastructure (Terraform) ---")
    
    # 1. Terraform Init (Infra)
    print("\n--- Initializing Terraform (Infra) ---")
    subprocess.check_call(["terraform", "init"], cwd=terraform_infra_dir, env=tf_env)

    # 2. Terraform Apply (Infra)
    print("\n--- Applying Terraform (Infra) ---")
    try:
        # Added -auto-approve flag here
        subprocess.check_call(["terraform", "apply", "-auto-approve"], cwd=terraform_infra_dir, env=tf_env)
    except subprocess.CalledProcessError:
        print("\nTerraform Infra Apply failed.")
        sys.exit(1)

    # 3. Capture Output
    try:
        output_bytes = subprocess.check_output(["terraform", "output", "-json"], cwd=terraform_infra_dir, env=tf_env)
        with open(tf_output_json_path, "wb") as f:
            f.write(output_bytes)
    except subprocess.CalledProcessError:
        print("Failed to get terraform output.")
        sys.exit(1)

    # 4. Generate Inventory
    generate_inventory(
        input_file=tf_output_json_path,
        output_file=inventory_ini_path,
        ssh_key_path=os.path.abspath(os.path.expanduser(args.ssh_private_key_path))
    )

    # 5. Clean known_hosts to prevent key mismatch errors
    cleanup_known_hosts(tf_output_json_path)

    print(f"\n--- Phase 2: Configuration (Ansible) ---")
    
    # 6. Wait for SSH
    if not wait_for_ssh(inventory_ini_path, ansible_dir):
        print("Error: Could not connect to nodes via SSH.")
        sys.exit(1)

    # 7. Run Ansible
    ansible_env = os.environ.copy()
    ansible_env["ANSIBLE_HOST_KEY_CHECKING"] = "False" 
    cmd = ["ansible-playbook", "-i", inventory_ini_path, ansible_playbook_path]
    try:
        subprocess.check_call(cmd, env=ansible_env, cwd=ansible_dir)
    except subprocess.CalledProcessError:
        print("\nAnsible Playbook execution failed.")
        sys.exit(1)

    print(f"\n--- Phase 3: Post-Configuration & Kubernetes Apps ---")

    # 8. Fetch Kubeconfig
    print("Retrieving kubeconfig from control plane...")
    master_pub_ip, master_priv_ip, bastion_ip = get_cluster_info(tf_output_json_path)
    
    scp_cmd = []
    
    # Construct SCP command based on Bastion presence
    if bastion_ip:
        # scp -o ProxyCommand="..." root@<priv_ip>:/root/.kube/config ./kubeconfig
        proxy_cmd = f"ssh -i {args.ssh_private_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -W %h:%p -q root@{bastion_ip}"
        scp_cmd = [
            "scp",
            "-i", args.ssh_private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ProxyCommand={proxy_cmd}",
            f"root@{master_priv_ip}:/root/.kube/config",
            local_kubeconfig_path
        ]
    else:
        # scp root@<pub_ip>:/root/.kube/config ./kubeconfig
        scp_cmd = [
            "scp",
            "-i", args.ssh_private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"root@{master_pub_ip}:/root/.kube/config",
            local_kubeconfig_path
        ]
        
    try:
        subprocess.check_call(scp_cmd)
        print(f"Kubeconfig downloaded to {local_kubeconfig_path}")
    except subprocess.CalledProcessError:
        print("Failed to download kubeconfig.")
        sys.exit(1)

    # 9. Patch Kubeconfig
    patch_kubeconfig(local_kubeconfig_path)

    # 10. START SOCKS5 PROXY (Fix for connection refused)
    # If we have a bastion, we target the master's private IP through the bastion.
    # If no bastion, we target the master's public IP.
    target_ip_for_proxy = master_priv_ip if bastion_ip else master_pub_ip
    
    proxy_proc = start_socks_proxy(
        bastion_ip=bastion_ip,
        master_ip=target_ip_for_proxy,
        ssh_key_path=args.ssh_private_key_path
    )
    
    # Ensure proxy is killed when script exits
    def cleanup_proxy():
        if proxy_proc and proxy_proc.poll() is None:
            print("\nShutting down SOCKS5 tunnel...")
            proxy_proc.terminate()
            
    atexit.register(cleanup_proxy)

    # 11. Terraform Kubernetes & Example App
    try:
        print("\n--- Applying Terraform (Kubernetes Apps) ---")
        
        # Update Env Vars for K8s phase
        tf_k8s_env = tf_env.copy()
        
        # --- NEW LOGIC START: Get NFS Private IP ---
        # We need to read the JSON again to get the private IP of the volume node
        with open(tf_output_json_path, 'r') as f:
            tf_data_for_nfs = json.load(f)

        volume_data_nfs = tf_data_for_nfs.get('volume_node_ip', {}).get('value', {})
        private_ips_nfs = tf_data_for_nfs.get('server_private_ips', {}).get('value', {})
        
        nfs_server_ip = ""
        if volume_data_nfs:
            # volume_node_ip output is { "node-name": "public_ip" }
            # We want the node-name key
            vol_node_name = next(iter(volume_data_nfs.keys()))
            # Look up its private IP
            nfs_server_ip = private_ips_nfs.get(vol_node_name, "")
            
        if not nfs_server_ip:
            print("Error: Could not determine NFS Server Private IP. Ensure Terraform output 'volume_node_ip' and 'server_private_ips' exist.")
            sys.exit(1)
            
        print(f"NFS Server IP determined as: {nfs_server_ip}")
        # --- NEW LOGIC END ---

        tf_k8s_env["TF_VAR_metallb_ip"] = f"{master_pub_ip}/32"
        tf_k8s_env["TF_VAR_acme_email"] = args.acme_email
        tf_k8s_env["TF_VAR_kube_config_path"] = local_kubeconfig_path
        tf_k8s_env["TF_VAR_nfs_server_ip"] = nfs_server_ip  # <--- Added Variable
        tf_k8s_env["KUBECONFIG"] = local_kubeconfig_path

        print(f"MetalLB IP set to: {master_pub_ip}/32")
        print(f"ACME Email set to: {args.acme_email}")
        print(f"Kubeconfig set to: {local_kubeconfig_path}")

        print("\n--- Initializing Terraform (K8s) ---")
        subprocess.check_call(["terraform", "init"], cwd=terraform_k8s_dir, env=tf_k8s_env)

        print("\n--- Applying Terraform (K8s) ---")
        # Removed stdout suppression so user can see output
        subprocess.check_call(
            ["terraform", "apply", "-auto-approve"], 
            cwd=terraform_k8s_dir, 
            env=tf_k8s_env
        )
        
        # 12. Deploy Nginx Example App
        print("\n--- Deploying Nginx Example App ---")
        try:
            # Read source manifest
            with open(nginx_manifest_src, 'r') as f:
                content = f.read()
            
            # Replace example.com with the provided domain
            content = content.replace("example.com", args.hetzner_zone_domain)
            
            # Write to temp file
            with open(nginx_manifest_tmp, 'w') as f:
                f.write(content)
            
            # Apply via kubectl
            subprocess.check_call(
                ["kubectl", "apply", "-f", nginx_manifest_tmp], 
                env=tf_k8s_env
            )
            print(f"Nginx example deployed from {nginx_manifest_tmp}")
            
        except FileNotFoundError:
             print(f"Warning: {nginx_manifest_src} not found. Skipping Nginx deployment.")
        except subprocess.CalledProcessError:
             print("Failed to deploy Nginx example.")
        
    finally:
        # Stop the proxy after terraform finishes (or fails)
        cleanup_proxy()
        # Unregister to avoid double calling
        atexit.unregister(cleanup_proxy)

    # 13. Summary Output (Console + File)
    
    # Reconstruct the command line string
    # We prepend 'python3' to make it a fully executable command string
    original_command = "python3 " + " ".join(sys.argv)

    summary_lines = [
        "\n==============================================",
        "       CLUSTER SETUP COMPLETE",
        "==============================================",
        f"MetalLB IP set to: {master_pub_ip}/32",
        f"ACME Email set to: {args.acme_email}",
        f"NFS Server is {nfs_server_ip}",
        f"0. You can up cluster again using your original command: {original_command}",
        f"1. Kubeconfig: {local_kubeconfig_path}",
        f"2. To remove the example app: kubectl delete -f {nginx_manifest_tmp}",
        "3. To access the cluster, open an SSH tunnel in a separate terminal:"
    ]
    
    if bastion_ip:
        summary_lines.append(f"   ssh -i {args.ssh_private_key_path} -D 1080 -q -N -J root@{bastion_ip} root@{master_priv_ip}")
    else:
        summary_lines.append(f"   ssh -i {args.ssh_private_key_path} -D 1080 -q -N root@{master_pub_ip}")
        
    summary_lines.append("\n4. Then use kubectl with the generated config:")
    summary_lines.append(f"   export KUBECONFIG={local_kubeconfig_path}")
    summary_lines.append("   kubectl get nodes")
    
    summary_text = "\n".join(summary_lines)
    
    # Print to console
    print(summary_text)
    
    # Save to file
    try:
        with open(readme_path, "w") as f:
            f.write(summary_text)
        print(f"\nSummary saved to: {readme_path}")
    except IOError as e:
        print(f"\nWarning: Failed to save summary file: {e}")

if __name__ == "__main__":
    main()