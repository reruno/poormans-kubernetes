resource "helm_release" "cert_manager" {
    name             = "cert-manager"
    repository       = "https://charts.jetstack.io"
    chart            = "cert-manager"
    namespace        = "cert-manager"
    create_namespace = true
    version          = "v1.19.1" 
    values = [
        yamlencode({
        installCRDs = true
        config = {
            apiVersion       = "controller.config.cert-manager.io/v1alpha1"
            kind             = "ControllerConfiguration"
            enableGatewayAPI = true
        }
        })
    ]
    wait = true
}

resource "kubectl_manifest" "letsencrypt_cluster_issuer" {
  depends_on = [helm_release.cert_manager]

  yaml_body = <<YAML
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-issuer
spec:
  acme:
    email: ${var.acme_email}
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-issuer-account-key
    solvers:
    - http01:
        gatewayHTTPRoute:
          parentRefs:
          - name: nginx-gateway 
            namespace: default
YAML
}