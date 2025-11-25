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