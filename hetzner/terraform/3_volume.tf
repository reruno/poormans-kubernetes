resource "hcloud_volume" "data_vol" {
  name     = "data-volume"
  size     = 10
  location = hcloud_server.node[1].location
  server_id = hcloud_server.node[1].id
  automount = true
  format    = "ext4"
}

resource "hcloud_volume_attachment" "data_vol_attachment" {
  volume_id = hcloud_volume.data_vol.id
  server_id = hcloud_server.node[1].id
  automount = true
  depends_on = [hcloud_server.node]
}