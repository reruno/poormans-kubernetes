resource "null_resource" "kubernetes_gateway_api_crds" {
  provisioner "local-exec" {
    when = create
    command = <<-EOF
      kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml
    EOF
  }
  provisioner "local-exec" {
    when = destroy
    command = <<-EOF
      kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml
    EOF
  }
}