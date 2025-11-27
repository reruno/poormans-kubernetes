import argparse
import subprocess
import os
import sys
import json
import time
import atexit
import shutil

# ==========================================
# 1. Helper Functions
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
        # If the file doesn't exist yet or json is bad, just warn and move on
        print(f"Warning: Failed to clean known_hosts (might be expected if cluster is already gone): {e}")

def get_cluster_info(tf_output_path):
    """
    Parses Terraform output to get Master Public IP (for MetalLB), 
    Master Private IP (for SCP), and Bastion IP.
    """
    try:
        with open(tf_output_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None, None
    
    # Get Root/Master info
    dns_root = data.get('dns_root_record_ip', {}).get('value', {})
    master_public_ip = next(iter(dns_root.values())) if dns_root else None
    
    # Determine Master Private IP
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
        return None
        
    print("SOCKS5 tunnel established on localhost:1080.")
    return proc

# ==========================================
# 2. Main Execution Flow
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Destroy Hetzner Cluster and Kubernetes Resources.")
    
    parser.add_argument("--hetzner-zone-domain", required=True, help="The domain zone (e.g., example.com)")
    parser.add_argument("--hetzner-token", required=True, help="Hetzner Cloud API Token")
    parser.add_argument("--ssh-public-key-path", required=True, help="Path to SSH public key")
    parser.add_argument("--ssh-private-key-path", required=True, help="Path to SSH private key")
    parser.add_argument("--acme-email", required=True, help="Email for Let's Encrypt (ACME)")
    
    # Optional flag to skip K8s destroy if user knows cluster is already dead
    parser.add_argument("--force-infra-only", action="store_true", help="Skip K8s resource destroy and go straight to Infrastructure destroy")

    args = parser.parse_args()

    # Directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    terraform_infra_dir = os.path.join(script_dir, "terraform")
    terraform_k8s_dir = os.path.join(script_dir, "terraform-kubernetes")

    # Files
    tf_output_json_path = os.path.join(script_dir, "tmpfile_terraform_output.json")
    local_kubeconfig_path = os.path.join(script_dir, "tmpfile_kube_config")
    nginx_manifest_tmp = os.path.join(script_dir, "tmpfile_nginx-app-http-redirect.yaml")
    
    # Env Vars
    tf_env = os.environ.copy()
    tf_env["TF_VAR_hcloud_token"] = args.hetzner_token
    tf_env["TF_VAR_hetzner_zone_domain"] = args.hetzner_zone_domain
    tf_env["TF_VAR_ssh_public_key_path"] = args.ssh_public_key_path

    print(f"--- Starting Cluster Teardown ---")

    # ==========================================
    # Phase 1: Refresh Info (to enable K8s cleanup)
    # ==========================================
    print("\n--- Refreshing Terraform Output Information ---")
    try:
        # We run 'output' just in case the tmpfile is missing or stale
        # We need this to get IPs for the Proxy to clean up K8s resources
        output_bytes = subprocess.check_output(
            ["terraform", "output", "-json"], 
            cwd=terraform_infra_dir, 
            env=tf_env,
            stderr=subprocess.DEVNULL
        )
        with open(tf_output_json_path, "wb") as f:
            f.write(output_bytes)
            
        # Clean known_hosts immediately after getting new info
        cleanup_known_hosts(tf_output_json_path)
        
    except subprocess.CalledProcessError:
        print("Warning: Could not get Terraform output. Infrastructure might already be partially destroyed.")

    # ==========================================
    # Phase 2: Kubernetes Resources Destroy
    # ==========================================
    if not args.force_infra_only:
        print("\n--- Phase 1: Destroying Kubernetes Resources ---")
        
        # We need IPs and Kubeconfig to destroy K8s resources
        master_pub_ip, master_priv_ip, bastion_ip = get_cluster_info(tf_output_json_path)
        
        # Check if we have enough info to proceed
        if master_pub_ip and os.path.exists(local_kubeconfig_path):
            target_ip_for_proxy = master_priv_ip if bastion_ip else master_pub_ip
            
            # Start Proxy
            proxy_proc = start_socks_proxy(
                bastion_ip=bastion_ip,
                master_ip=target_ip_for_proxy,
                ssh_key_path=args.ssh_private_key_path
            )

            # Define cleanup for proxy
            def cleanup_proxy():
                if proxy_proc and proxy_proc.poll() is None:
                    print("Shutting down SOCKS5 tunnel...")
                    proxy_proc.terminate()

            if proxy_proc:
                atexit.register(cleanup_proxy)
                
                try:
                    # Update Env Vars for K8s phase
                    tf_k8s_env = tf_env.copy()
                    tf_k8s_env["TF_VAR_metallb_ip"] = f"{master_pub_ip}/32"
                    tf_k8s_env["TF_VAR_acme_email"] = args.acme_email
                    tf_k8s_env["TF_VAR_kube_config_path"] = local_kubeconfig_path
                    tf_k8s_env["KUBECONFIG"] = local_kubeconfig_path

                    print("\n--- Destroying Terraform (K8s) ---")
                    subprocess.call(
                        ["terraform", "destroy", "-auto-approve"], 
                        cwd=terraform_k8s_dir, 
                        env=tf_k8s_env
                    )
                    
                    # Try to delete the example app if it exists
                    # We use subprocess.call to not crash if it fails
                    if os.path.exists(nginx_manifest_tmp):
                         print("\n--- Deleting Nginx Example App ---")
                         subprocess.call(
                            ["kubectl", "delete", "-f", nginx_manifest_tmp, "--ignore-not-found=true"], 
                            env=tf_k8s_env
                         )

                except Exception as e:
                    print(f"Error during K8s destroy: {e}")
                    print("Proceeding to Infrastructure destroy anyway...")
                finally:
                    cleanup_proxy()
                    atexit.unregister(cleanup_proxy)
            else:
                print("Skipping K8s destroy: Could not establish SSH tunnel.")
        else:
            print("Skipping K8s destroy: Missing cluster IP info or kubeconfig file.")
    else:
        print("Skipping K8s destroy (--force-infra-only selected).")

    # ==========================================
    # Phase 3: Infrastructure Destroy
    # ==========================================
    print(f"\n--- Phase 2: Destroying Infrastructure (Terraform) ---")
    
    # 1. Terraform Destroy (Infra)
    try:
        subprocess.check_call(
            ["terraform", "destroy", "-auto-approve"], 
            cwd=terraform_infra_dir, 
            env=tf_env
        )
    except subprocess.CalledProcessError:
        print("\nTerraform Infra Destroy failed. You may need to clean up manually via Hetzner Console.")
        sys.exit(1)

    print("\n==============================================")
    print("       CLUSTER TEARDOWN COMPLETE")
    print("==============================================")

if __name__ == "__main__":
    main()