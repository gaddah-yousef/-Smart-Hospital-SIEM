#requires -Version 5.1
<#
  generate-network-traffic.ps1 - Genere du trafic reseau realiste pour Zeek

  Lance un generateur de trafic DANS le conteneur Zeek qui produit :
   - Trafic legitime vers tous les services hospitaliers (HTTP, MQTT, Kafka, etc.)
   - Scans de ports medicaux (1883 MQTT, 5000 API) -> declenche notice Medical_Device_Scan
   - Connexions repetees rapides -> declenche Possible_Brute_Force
   - Volumetrie variable -> alimente les histogrammes Zeek

  Usage :
    .\generate-network-traffic.ps1                # demarre le generateur (loop infini)
    .\generate-network-traffic.ps1 -Stop          # arrete le generateur
    .\generate-network-traffic.ps1 -Status        # voit s il tourne + dernieres lignes
    .\generate-network-traffic.ps1 -Burst 60      # burst de 60s puis arret
    .\generate-network-traffic.ps1 -Intensity high   # low|normal|high
#>

param(
  [switch]$Stop,
  [switch]$Status,
  [int]$Burst = 0,
  [ValidateSet('low','normal','high')]
  [string]$Intensity = 'normal'
)

$ErrorActionPreference = 'Continue'
$Container = 'hospital-zeek'

function Step($t) { Write-Host ''; Write-Host "==> $t" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Info($m) { Write-Host "  ..  $m" -ForegroundColor Gray }

# ---- Verification du conteneur ----
$containerState = docker ps --filter "name=^$Container$" --format '{{.Status}}' 2>$null
if (-not $containerState) {
  Warn "Conteneur '$Container' non demarre. Lance d abord la stack (.\start.ps1)"
  exit 1
}

# ---- ARRET ----
if ($Stop) {
  Step 'Arret du generateur de trafic'
  docker exec $Container sh -c 'pkill -f 'traffic_gen[.]sh$'; echo killed' 2>$null
  Ok 'Generateur arrete'
  exit 0
}

# ---- STATUT ----
if ($Status) {
  Step "Statut du generateur dans $Container"
  $pids = docker exec $Container sh -c 'pgrep -f 'traffic_gen[.]sh$'' 2>$null
  if ($pids) {
    Ok "Generateur actif (PID: $($pids -replace "`n",' '))"
  } else {
    Warn 'Generateur non actif'
  }

  Step '10 dernieres connexions vues par Zeek (conn.log)'
  $lines = docker exec $Container sh -c 'tail -n 10 /usr/local/zeek/logs/current/conn.log 2>/dev/null | cut -f3,5,7,8 || echo "(conn.log vide)"' 2>$null
  $lines | ForEach-Object { Info $_ }

  Step '5 dernieres notices Zeek (notice.log)'
  $notices = docker exec $Container sh -c 'tail -n 5 /usr/local/zeek/logs/current/notice.log 2>/dev/null | cut -f4,6,11 || echo "(notice.log vide)"' 2>$null
  $notices | ForEach-Object { Info $_ }
  exit 0
}

# ---- INTENSITE -> parametres injectes dans le script bash ----
switch ($Intensity) {
  'low'    { $sleepVal = '5';   $burstsVal = '2';  $scanVal = '5'  }
  'normal' { $sleepVal = '2';   $burstsVal = '5';  $scanVal = '15' }
  'high'   { $sleepVal = '0.5'; $burstsVal = '12'; $scanVal = '35' }
}

# ---- SCRIPT BASH LITTERAL (single-quoted here-string, aucune interpolation PS) ----
$bashGen = @'
#!/bin/bash
# zeek_traffic - generateur de trafic pour Zeek (Smart Hospital SIEM)
SLEEP_INTERVAL=__SLEEP__
BURSTS_PER_CYCLE=__BURSTS__
SCAN_CHANCE=__SCAN__

TARGETS=(
  "mosquitto:1883"
  "hospital-api:5000"
  "kafka:9092"
  "loki:3100"
  "mimir:9009"
  "grafana:3000"
  "prometheus:9090"
  "tempo:3200"
  "kafka-ui:8080"
  "zookeeper:2181"
  "hospital-siem-backend:8000"
  "alloy:12345"
)

HTTP_ENDPOINTS=(
  "hospital-api:5000:/health"
  "hospital-api:5000:/audit/recent"
  "grafana:3000:/api/health"
  "prometheus:9090:/-/healthy"
  "loki:3100:/ready"
  "mimir:9009:/ready"
)

connect_tcp() {
  local target=$1
  local host=${target%:*}
  local port=${target#*:}
  timeout 1 bash -c "exec 3<>/dev/tcp/$host/$port; printf 'GET / HTTP/1.0\r\nHost: %s\r\n\r\n' \"$host\" >&3; head -c 200 <&3" >/dev/null 2>&1
}

port_scan() {
  local host=$1
  for port in 22 23 80 443 1883 3306 5000 5432 6379 8080 9090; do
    timeout 0.3 bash -c "exec 3<>/dev/tcp/$host/$port" >/dev/null 2>&1
  done
}

brute_pattern() {
  local target=$1
  local i
  for i in 1 2 3 4 5 6 7 8; do
    connect_tcp "$target"
  done
}

http_get() {
  local entry=$1
  local h p path
  IFS=':' read -r h p path <<< "$entry"
  timeout 1 bash -c "exec 3<>/dev/tcp/$h/$p; printf 'GET %s HTTP/1.0\r\nHost: %s\r\n\r\n' \"$path\" \"$h\" >&3; head -c 500 <&3" >/dev/null 2>&1
}

echo "[$(date)] zeek_traffic demarre (intensite $BURSTS_PER_CYCLE bursts/cycle, scan $SCAN_CHANCE%)"

while true; do
  i=0
  while [ $i -lt $BURSTS_PER_CYCLE ]; do
    idx=$((RANDOM % ${#TARGETS[@]}))
    connect_tcp "${TARGETS[$idx]}"

    hidx=$((RANDOM % ${#HTTP_ENDPOINTS[@]}))
    http_get "${HTTP_ENDPOINTS[$hidx]}"

    i=$((i+1))
  done

  rand=$((RANDOM % 100))
  if [ $rand -lt $SCAN_CHANCE ]; then
    suspect_target=${TARGETS[$((RANDOM % ${#TARGETS[@]}))]}
    suspect_host=${suspect_target%:*}
    case $((RANDOM % 3)) in
      0) port_scan "$suspect_host" ;;
      1) brute_pattern "mosquitto:1883" ;;
      2) brute_pattern "hospital-api:5000" ;;
    esac
  fi

  sleep $SLEEP_INTERVAL
done
'@

# Substitution des parametres d intensite
$bashGen = $bashGen.Replace('__SLEEP__',  $sleepVal).
                   Replace('__BURSTS__', $burstsVal).
                   Replace('__SCAN__',   $scanVal)

# ---- INJECTION + LANCEMENT ----
Step "Injection du generateur de trafic dans $Container"
$running = docker exec $Container sh -c 'pgrep -fc 'traffic_gen[.]sh$'' 2>$null
if ($running -and $running.Trim() -ne '0') {
  Warn "Generateur deja actif - utilise -Stop pour l arreter d abord"
  exit 1
}

# Ecrit le script dans le conteneur via stdin
$bashGen | docker exec -i $Container sh -c 'cat > /tmp/traffic_gen.sh && chmod +x /tmp/traffic_gen.sh'
Ok "Script /tmp/traffic_gen.sh installe (intensite=$Intensity)"

# Lance en arriere-plan dans le conteneur
docker exec -d $Container bash /tmp/traffic_gen.sh
Start-Sleep -Seconds 2

$pids = docker exec $Container sh -c 'pgrep -f 'traffic_gen[.]sh$'' 2>$null
if ($pids) {
  Ok "Generateur demarre (PID: $($pids -replace "`n",' '))"
} else {
  Warn 'Echec de demarrage - verifier docker logs hospital-zeek'
  exit 1
}

# ---- MODE BURST ----
if ($Burst -gt 0) {
  Step "Mode burst : laisse tourner pendant $Burst secondes"
  for ($i = $Burst; $i -gt 0; $i--) {
    Write-Host "`r  .. $i s restantes        " -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
  }
  Write-Host ''
  docker exec $Container sh -c 'pkill -f 'traffic_gen[.]sh$'' 2>$null
  Ok 'Burst termine, generateur arrete'
} else {
  Write-Host ''
  Write-Host '======================================================' -ForegroundColor Green
  Write-Host ' Generateur de trafic actif dans hospital-zeek' -ForegroundColor Green
  Write-Host '======================================================' -ForegroundColor Green
  Write-Host ''
  Write-Host " Statut    : .\generate-network-traffic.ps1 -Status"
  Write-Host " Arreter   : .\generate-network-traffic.ps1 -Stop"
  Write-Host " Tail logs : docker exec $Container tail -f /usr/local/zeek/logs/current/conn.log"
  Write-Host " Dashboard : http://localhost:3000  (Network Security)"
  Write-Host ''
}
