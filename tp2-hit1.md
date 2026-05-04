## Evidencia

El stack se instaló correctamente.

```bash
valentin@Debian:~/Proyectos/testing/Testing-Selenium-ProxyTeam$ kubectl -n observability get pods
NAME                       READY   STATUS    RESTARTS   AGE
grafana-7b5fb5785f-pxf88   1/1     Running   0          11m
loki-0                     2/2     Running   0          177m
loki-canary-2db7w          1/1     Running   0          177m
promtail-rmqf4             1/1     Running   0          173m

valentin@Debian:~/Proyectos/testing/Testing-Selenium-ProxyTeam$ kubectl -n observability get svc
NAME              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
grafana           ClusterIP   10.43.23.11     <none>        80/TCP              11m
loki              ClusterIP   10.43.24.226    <none>        3100/TCP,9095/TCP   177m
loki-canary       ClusterIP   10.43.231.239   <none>        3500/TCP            177m
loki-headless     ClusterIP   None            <none>        3100/TCP            177m
loki-memberlist   ClusterIP   None            <none>        7946/TCP            177m
```

Grafana está disponible en `http://$(hostname -I | awk '{print $1}'):30000`.