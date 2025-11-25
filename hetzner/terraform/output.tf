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