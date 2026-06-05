#!/usr/bin/env bash
# =============================================================================
#  traffic-gen.sh  -  Generateur de trafic reseau pour Zeek
# -----------------------------------------------------------------------------
#  En reseau bridge Docker, Zeek ne voit aucun trafic reel : il faut donc en
#  produire depuis le conteneur lui-meme. Ce script ouvre des connexions TCP
#  vers les services de la stack (par NOM de service -> resolu par le DNS
#  Docker, donc INDEPENDANT des adresses IP). Zeek capture ces connexions sur
#  eth0 et ecrit conn.log + notice.log.
#
#  Le port 1883 (MQTT) fait partie des "ports medicaux" surveilles par
#  scripts/hospital_detect.zeek -> declenche le notice "Medical_Device_Scan".
# =============================================================================

# Services TCP de la stack (nom:port). Modifiable sans souci.
TARGETS="mosquitto:1883 hospital-api:5000 siem-backend:8000 kafka:9092 \
loki:3100 mimir:9009 tempo:3200 prometheus:9090 grafana:3000 \
kafka-ui:8080 zookeeper:2181"

# Ports "medicaux" pour declencher des notices Zeek.
MED_TARGETS="mosquitto:1883 hospital-api:104 hospital-api:502"

connect() {
  local h="${1%:*}" p="${1#*:}"
  timeout 1 bash -c "exec 3<>/dev/tcp/$h/$p; printf 'GET / HTTP/1.0\r\n\r\n' >&3; head -c 16 <&3 >/dev/null 2>&1" >/dev/null 2>&1
}

echo "[traffic-gen] demarrage du generateur de trafic Zeek..."
while true; do
  for hp in $TARGETS;     do connect "$hp"; done
  for hp in $MED_TARGETS; do connect "$hp"; done
  sleep 2
done
