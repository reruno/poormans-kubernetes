# existing dns zone in hetzner
data "hcloud_zone" "main" {
    name = "ellieada.com"
}
# 2. Define the Existing A Record (e.g., for the root domain @)
resource "hcloud_zone_rrset" "root" {
    zone = data.hcloud_zone.main.id
    name    = "@"
    type    = "A"
    ttl     = 3600
    records = [ {
      value = hcloud_server.node[0].ipv4_address
    } ]
}