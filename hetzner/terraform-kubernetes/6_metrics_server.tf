resource "helm_release" "metrics_server" {
  name             = "metrics-server"
  repository       = "https://kubernetes-sigs.github.io/metrics-server/"
  chart            = "metrics-server"
  namespace        = "kube-system" 
  create_namespace = true
  version          = "3.13.0"      

  values = [
    yamlencode({
      # Commonly required argument if you are using self-signed certs 
      # or a managed cluster (like EKS/AKS) where hostname verification might fail.
      # Remove this block if you have valid certificates set up for your nodes.
      args = [
        "--kubelet-insecure-tls"
      ]
    })
  ]
}