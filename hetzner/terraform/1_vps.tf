resource "hcloud_ssh_key" "default" {
  name       = "terraform-ssh-key"
  public_key = file(var.ssh_public_key_path) 
}

resource "hcloud_network" "private_net" {
  name     = "internal-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "private_subnet" {
  network_id   = hcloud_network.private_net.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

resource "hcloud_server" "node" {
  count       = 2
  name        = "node-${count.index + 1}" 
  server_type = "cx23"                    
  image       = "debian-13" # default user: root
  location    = "nbg1"
  ssh_keys    = [hcloud_ssh_key.default.id]

  network {
    network_id = hcloud_network.private_net.id
    ip         = "10.0.1.${10 + count.index}" 
  }

  depends_on = [
    hcloud_network_subnet.private_subnet
  ]
}