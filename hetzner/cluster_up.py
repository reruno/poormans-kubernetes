import argparse
import subprocess
import os
import sys
import json

# ==========================================
# 1. Inventory Generation Logic
# ==========================================
def generate_inventory(input_file, output_file, ssh_key_path):
    """
    Generates an Ansible inventory INI file from a Terraform output JSON file.
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

    # Extract Data
    dns_root_records = tf_data.get('dns_root_record_ip', {}).get('value', {})
    # Get the raw IP string of the root record for comparison
    root_ip_address = next(iter(dns_root_records.values())) if dns_root_records else None
    
    private_ips = tf_data.get('server_private_ips', {}).get('value', {})
    public_ips = tf_data.get('server_public_ips', {}).get('value', {})

    if not private_ips:
        print("Error: 'server_private_ips' data not found in Terraform output.")
        sys.exit(1)

    # Determine Bastion Logic
    # Logic: Find a bastion IP that is in the public list BUT is NOT the root IP
    bastion_ip = None
    for node, ip in public_ips.items():
        if ip != root_ip_address:
            bastion_ip = ip
            break 
    
    # Fallback if no specific bastion found
    if not bastion_ip and public_ips:
        bastion_ip = list(public_ips.values())[0]

    master_lines = []
    worker_lines = []
    lines = []
    
    # [all] Section
    lines.append("[all]")
    node_names = sorted(private_ips.keys())
    worker_idx = 1
    
    for node_name in node_names:
        private_ip = private_ips[node_name]
        
        if node_name in dns_root_records:
            host_alias = "k8s-control-plane"
            lines.append(f"{host_alias} ansible_host={private_ip}")
            master_lines.append(host_alias)
        else:
            host_alias = f"k8s-worker-node{worker_idx}"
            lines.append(f"{host_alias}  ansible_host={private_ip}")
            worker_lines.append(host_alias)
            worker_idx += 1
            
    lines.append("") 

    # [kube-master] Section
    lines.append("[kube-master]")
    lines.extend(master_lines)
    lines.append("")

    # [kube-node] Section
    lines.append("[kube-node]")
    lines.extend(worker_lines)
    lines.append("")

    # [all:vars] Section
    lines.append("[all:vars]")
    lines.append("ansible_user=root")
    lines.append(f"ansible_ssh_private_key_file={ssh_key_path}")
    
    if bastion_ip:
        lines.append(f"# bastion host (Using IP: {bastion_ip})")
        lines.append(f"ansible_ssh_common_args='-o ProxyCommand=\"ssh -W %h:%p -q root@{bastion_ip}\"'")
    else:
        lines.append("# No suitable bastion host found")

    # Write to File
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Inventory saved successfully to {output_file}")


# ==========================================
# 2. Main Execution Flow
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Provision Hetzner Cluster and generate Inventory.")
    
    # Arguments
    parser.add_argument("--hetzner-zone-domain", required=True, help="The domain zone (e.g., example.com)")
    parser.add_argument("--hetzner-token", required=True, help="Hetzner Cloud API Token")
    parser.add_argument("--ssh-public-key-path", required=True, help="Path to SSH public key")
    parser.add_argument("--ssh-private-key-path", required=True, help="Path to SSH private key")

    args = parser.parse_args()

    # Determine Directories
    # Assumes script is in /hetzner/ and terraform is in /hetzner/terraform/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    terraform_dir = os.path.join(script_dir, "terraform")
    
    # Output file paths
    tf_output_json_path = os.path.join(script_dir, "tmpfile_terraform_output.json")
    inventory_ini_path = os.path.join(script_dir, "tmpfile_inventory.ini")

    print(f"--- Starting Cluster Setup ---")
    print(f"Terraform Directory: {terraform_dir}")

    # Set Environment Variables for Terraform
    # Maps CLI args to TF_VAR_ variables for Terraform to pick them up
    tf_env = os.environ.copy()
    tf_env["TF_VAR_hcloud_token"] = args.hetzner_token
    tf_env["TF_VAR_hetzner_zone_domain"] = args.hetzner_zone_domain
    tf_env["TF_VAR_ssh_public_key_path"] = args.ssh_public_key_path

    # 1. Terraform Init (Quietly)
    print("\n--- Initializing Terraform ---")
    subprocess.check_call(["terraform", "init"], cwd=terraform_dir, env=tf_env)

    # 2. Terraform Apply (Interactive)
    # The user will see the plan and be asked for 'yes' or 'no'
    print("\n--- Applying Terraform ---")
    try:
        subprocess.check_call(["terraform", "apply"], cwd=terraform_dir, env=tf_env)
    except subprocess.CalledProcessError:
        print("\nTerraform Apply failed or was cancelled.")
        sys.exit(1)

    # 3. Capture Terraform Output
    print("\n--- Capturing Terraform Output ---")
    try:
        output_bytes = subprocess.check_output(
            ["terraform", "output", "-json"], 
            cwd=terraform_dir, 
            env=tf_env
        )
        
        # Save to file 
        with open(tf_output_json_path, "wb") as f:
            f.write(output_bytes)
            
        print(f"Terraform output saved to {tf_output_json_path}")
        
    except subprocess.CalledProcessError as e:
        print("Failed to get terraform output.")
        sys.exit(1)

    # 4. Generate Ansible Inventory
    print("\n--- Generating Ansible Inventory ---")
    generate_inventory(
        input_file=tf_output_json_path,
        output_file=inventory_ini_path,
        ssh_key_path=os.path.abspath(os.path.expanduser(args.ssh_private_key_path))
    )

    print("\n--- Phase 1 Complete: Infrastructure is Up & Inventory Generated ---")
    print(f"Inventory File: {inventory_ini_path}")
    print(f"Ready for next steps.")

if __name__ == "__main__":
    main()