resource "kubernetes_namespace" "istio_system" {
    metadata {
        name = "istio-system"
    }
}

resource "helm_release" "istio_base" {
    name             = "istio-base"
    repository       = "https://istio-release.storage.googleapis.com/charts"
    chart            = "base"
    namespace        = "istio-system"

    cleanup_on_fail = true
    depends_on = [ kubernetes_namespace.istio_system ]
}

resource "helm_release" "istiod" {
    name       = "istiod"
    repository = "https://istio-release.storage.googleapis.com/charts"
    chart      = "istiod"
    namespace  = "istio-system"

    depends_on = [ kubernetes_namespace.istio_system, helm_release.istio_base ]
    values = [
      yamlencode({
        pilot = {
          env = {
            PILOT_ENABLE_ALPHA_GATEWAY_API = "true"
          }
        }
      })
    ]
}

