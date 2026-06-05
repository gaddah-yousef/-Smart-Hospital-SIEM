#requires -Version 5.1
<#
  start-and-simulate.ps1 - Tout-en-un : demarre la stack + joue les 5 sims Python.

  Ce script combine :
   1. Demarrage Docker Desktop si necessaire
   2. docker compose up -d (option -Rebuild)
   3. Auto-decouverte des ports exposes (adaptatif - fonctionne meme si tu
      changes les ports dans docker-compose.yml ou si l IP/subnet change)
   4. Relance du generateur de trafic Zeek (optionnel)
   5. Attente de Grafana
   6. Execution de TOUTES les simulations Python (attack-simulations/*.py)
      dans les conteneurs (zero dependance Python sur l hote)
   7. Verification Loki + etat des regles Grafana
   8. Affichage des URLs avec les bons ports detectes

  Usage :
    .\start-and-simulate.ps1                # demarrage + sims complet
    .\start-and-simulate.ps1 -Rebuild       # rebuild des images custom
    .\start-and-simulate.ps1 -NoTraffic     # ne relance pas le generateur Zeek
    .\start-and-simulate.ps1 -Only iot      # joue uniquement IoT critical
#>

param(
  [switch]$Rebuild,
  [switch]$NoTraffic,
  [string[]]$Only,
  [int]$BruteForceAttempts = 8
)

$ErrorActionPreference = 'Continue'
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir
$Project = 'smart-hospital-siem-grafana'

function Step($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Info($m) { Write-Host "  ..  $m" -ForegroundColor Gray }

# -----------------------------------------------------------------
# 1) Docker Desktop
# -----------------------------------------------------------------
Step 'Verification de Docker'
docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Warn 'Demon Docker indisponible, demarrage de Docker Desktop...'
  $exe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
  if (Test-Path $exe) { Start-Process $exe } else { Warn "Docker Desktop introuvable a $exe" }
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 5
    docker info *> $null
    if ($LASTEXITCODE -eq 0) { break }
  }
  if ($LASTEXITCODE -ne 0) { throw 'Demon Docker toujours indisponible apres 5 min.' }
}
Ok 'Docker pret'

# -----------------------------------------------------------------
# 2) docker compose up
# -----------------------------------------------------------------
Step 'Demarrage de la stack (docker compose up -d)'
$cmpArgs = @('-p', $Project, 'up', '-d', '--remove-orphans')
if ($Rebuild) { $cmpArgs += '--build' }
& docker compose @cmpArgs 2>&1 | Select-Object -Last 25 | ForEach-Object { Info $_ }

# -----------------------------------------------------------------
# 3) Detection adaptative des ports
# -----------------------------------------------------------------
Step 'Decouverte des ports exposes (adaptatif IP/port)'
function Get-MappedPort {
  param([string]$container, [int]$internalPort)
  try {
    $j = docker inspect $container --format '{{json .NetworkSettings.Ports}}' 2>$null | ConvertFrom-Json
    $key = "$internalPort/tcp"
    if ($j.$key) { return [int]$j.$key[0].HostPort }
  } catch {}
  return $internalPort
}
$ports = [ordered]@{
  grafana = Get-MappedPort 'hospital-grafana'      3000
  api     = Get-MappedPort 'hospital-api'          5000
  siem    = Get-MappedPort 'hospital-siem-backend' 8000
  loki    = Get-MappedPort 'hospital-loki'         3100
  mimir   = Get-MappedPort 'hospital-mimir'        9009
  tempo   = Get-MappedPort 'hospital-tempo'        3200
  kafkaui = Get-MappedPort 'hospital-kafka-ui'     8080
  alloy   = Get-MappedPort 'hospital-alloy'        12345
  prom    = Get-MappedPort 'hospital-prometheus'   9090
}
Ok ("grafana=$($ports.grafana) api=$($ports.api) siem=$($ports.siem) loki=$($ports.loki)")
$ports | ConvertTo-Json | Out-File "$ProjectDir\.runtime-ports.json" -Encoding utf8

# -----------------------------------------------------------------
# 4) Generateur de trafic Zeek
# -----------------------------------------------------------------
if (-not $NoTraffic) {
  Step 'Generateur de trafic Zeek'
  $zeekStatus = docker ps --filter 'name=hospital-zeek' --format '{{.Status}}'
  if ($zeekStatus -match '^Up') {
    $genScript = @'
while true; do
  for hp in mosquitto:1883 hospital-api:5000 kafka:9092 loki:3100 mimir:9009 grafana:3000 prometheus:9090 tempo:3200 kafka-ui:8080 zookeeper:2181 mosquitto:1883; do
    h=${hp%:*}; p=${hp#*:}
    timeout 1 bash -c "exec 3<>/dev/tcp/$h/$p; echo -e 'GET / HTTP/1.0\r\n\r\n' >&3" >/dev/null 2>&1
  done
  sleep 2
done
'@
    $running = (docker exec hospital-zeek sh -c 'pgrep -fc traffic_gen.sh' 2>$null).Trim()
    if (-not $running -or $running -eq '0') {
      $genScript | docker exec -i hospital-zeek sh -c 'cat > /tmp/traffic_gen.sh'
      docker exec -d hospital-zeek bash /tmp/traffic_gen.sh
      Ok 'Generateur Zeek lance'
    } else {
      Ok 'Generateur Zeek deja actif'
    }
  } else {
    Warn 'Conteneur Zeek non demarre'
  }
}

# -----------------------------------------------------------------
# 5) Attente Grafana
# -----------------------------------------------------------------
Step "Attente de Grafana sur http://localhost:$($ports.grafana) ..."
$grafanaReady = $false
for ($i=0; $i -lt 60; $i++) {
  try {
    $r = Invoke-WebRequest "http://localhost:$($ports.grafana)/api/health" -UseBasicParsing -TimeoutSec 4
    if ($r.StatusCode -eq 200) { $grafanaReady = $true; break }
  } catch {}
  Start-Sleep -Seconds 3
}
if ($grafanaReady) { Ok 'Grafana repond (HTTP 200)' } else { Warn 'Grafana ne repond pas encore' }

# Attente API hospital
Step "Attente de Hospital API sur http://localhost:$($ports.api) ..."
$apiReady = $false
for ($i=0; $i -lt 30; $i++) {
  try {
    $r = Invoke-WebRequest "http://localhost:$($ports.api)/health" -UseBasicParsing -TimeoutSec 4
    if ($r.StatusCode -eq 200) { $apiReady = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}
if ($apiReady) { Ok 'Hospital API repond' } else { Warn 'Hospital API pas prete' }

# -----------------------------------------------------------------
# 6) Execution des simulations Python (delegue a run-all-sims.ps1)
# -----------------------------------------------------------------
if ($apiReady) {
  Step 'Lancement des 5 simulations Python dans les conteneurs'
  $simArgs = @('-BruteForceAttempts', $BruteForceAttempts)
  if ($Only) { $simArgs += @('-Only') + $Only }
  & "$ProjectDir\run-all-sims.ps1" @simArgs
} else {
  Warn 'Sims non jouees car API pas prete'
}

# -----------------------------------------------------------------
# 7) Verification Loki
# -----------------------------------------------------------------
Step 'Verification dans Loki (10 dernieres minutes)'
function LokiSum {
  param($query)
  try {
    $r = Invoke-RestMethod "http://localhost:$($ports.loki)/loki/api/v1/query" -Body @{query=$query} -TimeoutSec 8
    if ($r.data.result) { return ($r.data.result | ForEach-Object { [int]$_.value[1] } | Measure-Object -Sum).Sum }
    return 0
  } catch { return -1 }
}
$checks = @(
  @{name='LOGIN_FAILED      '; q='count_over_time({job="hospital-api"} |= "LOGIN_FAILED" [10m])'}
  @{name='UNAUTHORIZED_ACCESS'; q='count_over_time({job="hospital-api"} |= "UNAUTHORIZED_ACCESS" [10m])'}
  @{name='FILE_ACCESS       '; q='count_over_time({job="hospital-api"} |= "FILE_ACCESS" [10m])'}
  @{name='EMERGENCY (IoT)   '; q='count_over_time({job="iot-gateway"} |= "EMERGENCY" [10m])'}
)
foreach ($c in $checks) {
  $n = LokiSum $c.q
  if ($n -gt 0)     { Ok   ("{0} = {1}" -f $c.name, $n) }
  elseif ($n -eq 0) { Warn ("{0} = 0 (relancer dans qqs s)" -f $c.name) }
  else              { Warn ("{0} = erreur Loki" -f $c.name) }
}

# -----------------------------------------------------------------
# 8) Etat des regles Grafana
# -----------------------------------------------------------------
Step 'Etat des regles d alerte Grafana'
$cred = 'admin:admin'
$b64  = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($cred))
$hdr  = @{Authorization = "Basic $b64"}
try {
  $r = Invoke-RestMethod "http://localhost:$($ports.grafana)/api/prometheus/grafana/api/v1/rules" -Headers $hdr -TimeoutSec 10
  foreach ($g in $r.data.groups) {
    foreach ($rule in $g.rules) {
      $color = if ($rule.state -eq 'firing') { 'Red' } elseif ($rule.state -eq 'pending') { 'Yellow' } else { 'Gray' }
      Write-Host ("  {0,-32} state={1,-8} health={2}" -f $rule.name, $rule.state, $rule.health) -ForegroundColor $color
    }
  }
} catch { Warn "Lecture regles impossible : $($_.Exception.Message)" }

# -----------------------------------------------------------------
# 9) URLs finales
# -----------------------------------------------------------------
Write-Host ''
Write-Host '======================================================' -ForegroundColor Green
Write-Host ' Smart Hospital SIEM - stack + simulations PRETES' -ForegroundColor Green
Write-Host '======================================================' -ForegroundColor Green
Write-Host ''
Write-Host " Grafana       : http://localhost:$($ports.grafana)  (admin / admin)"
Write-Host " Hospital API  : http://localhost:$($ports.api)"
Write-Host " SIEM API docs : http://localhost:$($ports.siem)/docs"
Write-Host " Loki          : http://localhost:$($ports.loki)"
Write-Host " Mimir         : http://localhost:$($ports.mimir)"
Write-Host " Tempo         : http://localhost:$($ports.tempo)"
Write-Host " Kafka UI      : http://localhost:$($ports.kafkaui)"
Write-Host " Prometheus    : http://localhost:$($ports.prom)"
Write-Host ''
Write-Host ' Rejouer les sims sans redemarrer : .\run-all-sims.ps1'
Write-Host ''
