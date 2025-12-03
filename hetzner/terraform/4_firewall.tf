resource "hcloud_firewall" "k8s_protection" {
  name = "k8s-security-group"

  # -----------------------------------------------------------
  # 1. PUBLIC INBOUND RULES (Exceptions for the Internet)
  # -----------------------------------------------------------

  # SSH: Allow from anywhere (so you can login)
  # Ideally, replace "0.0.0.0/0" with your own home IP for max security
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # HTTP/HTTPS: For your Ingress Controller (Web traffic)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # ICMP: Allow Ping (Optional, but useful for debugging)
  rule {
    direction = "in"
    protocol  = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # -----------------------------------------------------------
  # 2. INTERNAL RULES (Critical for NFS & K8s Networking)
  # -----------------------------------------------------------

  # This allows ALL traffic strictly between your servers on the private network.
  # This is safe because it only accepts traffic from 10.0.0.0/16
  # This effectively OPENS NFS internally, but BLOCKS it externally.
  
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "any"
    source_ips = ["10.0.0.0/16"] 
  }

  rule {
    direction = "in"
    protocol  = "udp"
    port      = "any"
    source_ips = ["10.0.0.0/16"]
  }

  # -----------------------------------------------------------
  # 3. APPLY TO SERVERS
  # -----------------------------------------------------------

  # Automatically apply this firewall to all nodes created in "hcloud_server.node"
  dynamic "apply_to" {
    for_each = hcloud_server.node
    content {
      server = apply_to.value.id
    }
  }
}