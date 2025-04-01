{{- define "computeResourceHash" -}}
{{- $resource := fromYaml .resource -}}
{{- $data := get $resource "data" | default dict -}}
{{- $hashInput := list -}}
{{- range $key, $value := $data -}}
  {{- $hashInput = append $hashInput (printf "%s:%s" $key $value) -}}
{{- end -}}
{{- $sorted := sortAlpha $hashInput -}}
{{- $joined := join "" $sorted -}}
{{- sha256sum $joined }}
{{- end -}}