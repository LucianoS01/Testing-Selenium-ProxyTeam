# LogQL Cookbook para Scraper de Mercado Libre

Esta guía presenta consultas LogQL útiles para monitorear y analizar el comportamiento de tu scraper de Mercado Libre, asumiendo que los logs están en formato JSON y son recolectados por Loki.

**Contexto de Logs:**
Los logs son JSON y contienen campos como: `level`, `producto`, `message`, `resultados_página`, `delay_seconds`, `exc_info`, `timestamp`, `logger`.

**Selector de Stream Base:**
Para todas las consultas, asumimos que los logs del scraper se identifican con los labels `namespace="ml-scraper"` y `app="scraper"`.

---

## 1. Top errores por producto en las últimas 24h

**Pregunta de Negocio:** ¿Qué producto está generando la mayor cantidad de errores en el scraping, lo que podría indicar selectores rotos o problemas específicos del producto?

**Explicación Técnica:**
*   **Selector de Stream:** `{namespace="ml-scraper", app="scraper"}` selecciona todos los logs de tu scraper.
*   **Filtro de Log:** `| json` parsea la línea de log como JSON, permitiendo acceder a sus campos. `| level="ERROR"` filtra solo los logs con nivel de error.
*   **Agregación:** `count_over_time(...) [24h]` cuenta el número de logs de error en las últimas 24 horas para cada stream. `sum by (producto)` suma estos conteos, agrupándolos por el campo `producto` extraído del JSON, para obtener el total de errores por cada producto.

**Consulta LogQL:**
```logql
sum by (producto) (
  count_over_time(
    {namespace="ml-scraper", app="scraper"} | json | level="ERROR" [24h]
  )
)
```

---

## 2. Tasa de WARNINGs por minuto..

**Pregunta de Negocio:** ¿Existe inestabilidad reciente en los selectores o en la extracción de datos, manifestada por un aumento en los warnings?

**Explicación Técnica:**
*   **Selector de Stream:** `{namespace="ml-scraper", app="scraper"}`.
*   **Filtro de Log:** `| json` para parsear JSON. `| level="WARNING"` filtra los logs de advertencia.
*   **Agregación:** `rate(...) [1m]` calcula la tasa promedio de logs de advertencia por segundo en el último minuto para cada stream. `sum by (producto)` suma estas tasas, agrupándolas por `producto`, para mostrar la tasa total de warnings por producto.

**Consulta LogQL:**
```logql
sum by (producto) (
  rate({namespace="ml-scraper", app="scraper"} | json | level="WARNING" [1m])
)
```

---

## 3. Resultados totales por producto

**Pregunta de Negocio:** ¿Cuántos resultados se están obteniendo para cada producto en un período dado? Esto ayuda a verificar la efectividad del scraping y la paginación.

**Explicación Técnica:**
*   **Selector de Stream:** `{namespace="ml-scraper", app="scraper"}`.
*   **Filtro de Log:** `| json` para parsear JSON. `| message="Página completada"` filtra los logs que indican que una página ha sido procesada, los cuales contienen el campo `resultados_página`.
*   **Agregación:** `| unwrap resultados_página` extrae el valor numérico del campo `resultados_página`. `sum by (producto) (sum_over_time(... [1h]))` suma todos los valores de `resultados_página` para cada producto en la última hora.

**Consulta LogQL:**
```logql
sum by (producto) (
  sum_over_time({namespace="ml-scraper", app="scraper"} | json | message="Página completada" | unwrap resultados_página [1h])
)
```

---

## 4. Promedio de delay entre productos

**Pregunta de Negocio:** ¿Se está respetando el tiempo de espera configurado entre el procesamiento de diferentes productos, lo cual es crucial para evitar el bloqueo por parte de los servidores de Mercado Libre?

**Explicación Técnica:**
*   **Selector de Stream:** `{namespace="ml-scraper", app="scraper"}`.
*   **Filtro de Log:** `| json` para parsear JSON. `| message="Esperando antes del siguiente producto"` filtra los logs que registran la pausa entre productos.
*   **Agregación:** `| unwrap delay_seconds` extrae el valor numérico del campo `delay_seconds`. `avg_over_time(... [1h])` calcula el promedio de estos valores en la última hora.

**Consulta LogQL:**
```logql
avg_over_time({namespace="ml-scraper", app="scraper"} | json | message="Esperando antes del siguiente producto" | unwrap delay_seconds [1h])
```

---

## 5. Búsqueda de Timeouts

**Pregunta de Negocio:** ¿Con qué frecuencia ocurren `TimeoutException` y para qué productos, indicando posibles problemas de rendimiento de la red, carga de la página o selectores que tardan en aparecer?

**Explicación Técnica:**
*   **Selector de Stream:** `{namespace="ml-scraper", app="scraper"}`.
*   **Filtro de Log:** `| json` para parsear JSON. `| exc_info =~ "TimeoutException"` filtra los logs donde el campo `exc_info` contiene la cadena "TimeoutException".
*   **Agregación:** `count_over_time(...) [1h]` cuenta el número de ocurrencias de `TimeoutException` en la última hora. `by (producto)` agrupa estos conteos por el producto asociado.

**Consulta LogQL:**
```logql
count_over_time({namespace="ml-scraper", app="scraper"} | json | exc_info =~ "TimeoutException" [1h]) by (producto)
```