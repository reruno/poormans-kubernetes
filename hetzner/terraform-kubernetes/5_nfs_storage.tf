resource "kubernetes_namespace" "nfs_system" {
  metadata {
    name = "nfs-storage"
  }
}

resource "helm_release" "nfs_provisioner" {
  name       = "nfs-provisioner"
  repository = "https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/"
  chart      = "nfs-subdir-external-provisioner"
  namespace  = "nfs-storage"
  # It is good practice to pin the version to ensure stability
  # version    = "4.0.18" 

  wait = true

  values = [
    yamlencode({
      nfs = {
        server = var.nfs_server_ip
        path   = "/mnt/data-vol"
      }
      storageClass = {
        name         = "nfs-storage"
        defaultClass = true
      }
    })
  ]

  depends_on = [
    kubernetes_namespace.nfs_system
  ]
}