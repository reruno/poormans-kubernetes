output "server_public_ips" {
  value = {
    for server in hcloud_server.node : server.name => server.ipv4_address
  }
}

output "server_private_ips" {
  value = {
    for server in hcloud_server.node : server.name => "10.0.1.${10 + index(hcloud_server.node.*.id, server.id)}"
  }
}

output "dns_root_record_ip" {
  description = "The specific server IP used for the root @ DNS record"
  value = {
    (hcloud_server.node[0].name) = hcloud_server.node[0].ipv4_address
  }
}

output "volume_node_ip" {
  description = "The specific server IP that volume is attached to"
  value = {
    (hcloud_server.node[1].name) = hcloud_server.node[1].ipv4_address
  }
}

output "volume_id" {
  description = "The specific server IP that volume is attached to"
  value = hcloud_volume.data_vol.id
}