#!/bin/bash
set -euo pipefail

echo "--- Creando el namespace 'elastic' ---"
kubectl apply -f manifests/namespace.yaml

echo "--- Instalando ECK Operator (2.16.x) ---"
# Agrega el repositorio de Helm de Elastic y actualiza
helm repo add elastic https://helm.elastic.co --force-update > /dev/null
# Instala o actualiza el ECK Operator en el namespace 'elastic-system'
helm upgrade --install elastic-operator elastic/eck-operator \
  --version 2.16.0 \
  --namespace elastic-system \
  --create-namespace \
  -f helm/eck-operator-values.yaml \
  --wait

echo "--- Aplicando manifiestos de Elasticsearch (8.17.x) y Kibana (8.17.x) ---"
# Aplica los CR de Elasticsearch y Kibana, esperando a que estén listos
kubectl apply -f manifests/elasticsearch.yaml --wait=true
kubectl apply -f manifests/kibana.yaml --wait=true
kubectl apply -f manifests/kibana-nodeport.yaml

echo "--- Esperando a que Elasticsearch esté saludable ---"
# Espera hasta que el clúster de Elasticsearch esté en estado Healthy
kubectl wait --namespace elastic \
  --for=condition=Healthy elasticsearch/elasticsearch-scraper \
  --timeout=600s

echo "--- Recuperando la contraseña del usuario 'elastic' ---"
# Obtiene la contraseña del usuario 'elastic' del Secret generado por el operador
ELASTIC_PASSWORD=$(kubectl get secret -n elastic elasticsearch-scraper-es-elastic-user -o go-template='{{.data.elastic | base64decode}}')

echo "--- Instalando Fluent Bit (3.2.x) ---"
# Agrega el repositorio de Helm de Fluent y actualiza
helm repo add fluent https://fluent.github.io/helm-charts --force-update > /dev/null
# Instala o actualiza Fluent Bit en el namespace 'elastic'
helm upgrade --install fluent-bit fluent/fluent-bit \
  --version 0.48.0 \
  --namespace elastic \
  --create-namespace \
  -f helm/fluent-bit-values.yaml \
  --set "fluentbit.config.outputs[0].HTTP_Passwd=${ELASTIC_PASSWORD}" \
  --wait

echo "--- Aplicando Política ILM y Index Template ---"
# Espera un poco más para asegurar que Elasticsearch y Kibana estén completamente inicializados
sleep 30

# Construye la URL de Elasticsearch con autenticación
ES_URL="https://elastic:${ELASTIC_PASSWORD}@elasticsearch-scraper-es-http.elastic.svc.cluster.local:9200"

# Aplica la Política ILM
echo "Aplicando política ILM 'scraper_ilm_policy'..."
curl -k -X PUT "${ES_URL}/_ilm/policy/scraper_ilm_policy" \
     -H 'Content-Type: application/json' \
     --data-binary "@manifests/ilm-policy.json" \
     --fail --silent --show-error || { echo "Error: Falló la aplicación de la política ILM."; exit 1; }
echo "Política ILM 'scraper_ilm_policy' aplicada correctamente."

# Aplica el Index Template
echo "Aplicando Index Template 'scraper_logs_template'..."
curl -k -X PUT "${ES_URL}/_index_template/scraper_logs_template" \
     -H 'Content-Type: application/json' \
     --data-binary "@manifests/index-template.json" \
     --fail --silent --show-error || { echo "Error: Falló la aplicación del Index Template."; exit 1; }
echo "Index Template 'scraper_logs_template' aplicado correctamente."

echo "--- Despliegue del Stack EFK completado! ---"
echo "Kibana debería ser accesible a través del NodePort 30001 en tu nodo k3s."
echo "Contraseña del usuario 'elastic' de Elasticsearch: ${ELASTIC_PASSWORD}"