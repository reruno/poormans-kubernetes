resource "kubernetes_namespace" "metallb_system" {
    metadata {
        name = "metallb-system"
    }
}

resource "helm_release" "metallb" {
    name       = "metallb"
    repository = "https://metallb.github.io/metallb"
    chart      = "metallb"
    namespace  = "metallb-system"
    version    = "0.15.2" 

    wait = true

    depends_on = [
        kubernetes_namespace.metallb_system
    ]
}
data "kubectl_file_documents" "metallb_manifests" {
  # Terraform allows variable interpolation inside EOF blocks automatically
  content = <<-EOF
    apiVersion: metallb.io/v1beta1
    kind: IPAddressPool
    metadata:
      name: default-pool
      namespace: metallb-system
    spec:
      addresses:
      - ${var.metallb_ip}
    ---
    apiVersion: metallb.io/v1beta1
    kind: L2Advertisement
    metadata:
      name: default-advertisement
      namespace: metallb-system
    spec:
      ipAddressPools:
      - default-pool
  EOF
}

resource "kubectl_manifest" "metallb_config" {
  for_each  = data.kubectl_file_documents.metallb_manifests.manifests
  yaml_body = each.value

  depends_on = [
    helm_release.metallb
  ]
}