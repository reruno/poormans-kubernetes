data "http" "gateway_api_release" {
    url = "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml"
}

data "kubectl_file_documents" "gateway_api_docs" {
    content = data.http.gateway_api_release.response_body
}

resource "kubectl_manifest" "gateway_api_crds" {
    for_each  = data.kubectl_file_documents.gateway_api_docs.manifests
    yaml_body = each.value
    
    server_side_apply = true 
    
    wait = true
}