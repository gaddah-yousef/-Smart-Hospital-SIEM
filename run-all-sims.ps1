#requires -Version 5.1
<#
  run-all-sims.ps1 - Joue les 5 simulations Python de attack-simulations/
  en les copiant et les executant DANS les conteneurs adequats.

  Avantages :
   - Aucune dependance Python a installer sur l hote
   - Fonctionne meme si l IP de la machine change (les conteneurs utilisent
     le reseau interne Docker)
   - Fonctionne meme si les ports exposes changent (acces interne)
   - Couvre les 5 attaques: brute_force, unauthorized, lateral, ransomware, iot_critical

  Usage :
    .\run-all-sims.ps1                # joue toutes les simulations
    .\run-all-sims.ps1 -Only brute_force,iot
    .\run-all-sims.ps1 -BruteForceAttempts 12
#>

param(
  [string[]]$Only,
  [int]$BruteForceAttempts = 8
)

$ErrorActionPreference = 'Continue'
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SimDir     = Join-Path $ProjectDir 'attack-simulations'

function Step($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Info($m) { Write-Host "  ..  $m" -ForegroundColor Gray }

function Should-Run($name) {
  if (-not $Only -or $Only.Count -eq 0) { return $true }
  return ($Only -contains $name)
}

function Ensure-Container($name) {
  $status = docker ps --filter "name=^$name$" --format '{{.Status}}' 2>$null
  if (-not $status) {
    Warn "Conteneur '$name' non demarre. Lance d abord .\start.ps1"
    return $false
  }
  return $true
}

function Copy-And-Run {
  param(
    [string]$Container,
    [string]$LocalScript,
    [string[]]$Args
  )
  $dest = "/tmp/$(Split-Path -Leaf $LocalScript)"
  docker cp $LocalScript "${Container}:$dest" 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Warn "docker cp echec vers $Container"
    return $false
  }
  $cmd = @('exec', $Container, 'python', $dest) + $Args
  & docker @cmd 2>&1 | ForEach-Object { Info $_ }
  return ($LASTEXITCODE -eq 0)
}

Write-Host ''
Write-Host '======================================================' -ForegroundColor Magenta
Write-Host ' Smart Hospital SIEM - run-all-sims (Python sims)' -ForegroundColor Magenta
Write-Host '======================================================' -ForegroundColor Magenta

# Le conteneur hospital-api a Flask+requests installes, il sert d executeur
# pour les sims HTTP (brute_force, unauthorized, lateral, ransomware).
# Cible : http://hospital-api:5000 via le reseau interne Docker.
$ApiContainer = 'hospital-api'
$IotContainer = 'hospital-iot-simulator'
$ApiInternal  = 'http://hospital-api:5000'
$MqttHost     = 'mosquitto'

$apiUp = Ensure-Container $ApiContainer
$iotUp = Ensure-Container $IotContainer

# 1) Brute force
if ($apiUp -and (Should-Run 'brute_force')) {
  Step "1/5 Brute force ($BruteForceAttempts tentatives, IP 10.10.66.10)"
  $ok = Copy-And-Run $ApiContainer "$SimDir\sim_brute_force.py" @(
    '--url', $ApiInternal,
    '--source-ip', '10.10.66.10',
    '--attempts', "$BruteForceAttempts"
  )
  if ($ok) { Ok 'brute_force termine' } else { Warn 'brute_force echec' }
}

# 2) Acces non autorise
if ($apiUp -and (Should-Run 'unauthorized')) {
  Step '2/5 Acces patient non autorise (role=billing)'
  $ok = Copy-And-Run $ApiContainer "$SimDir\sim_unauthorized_access.py" @(
    '--url', $ApiInternal,
    '--source-ip', '10.10.77.20'
  )
  if ($ok) { Ok 'unauthorized termine' } else { Warn 'unauthorized echec' }
}

# 3) Lateral movement
if ($apiUp -and (Should-Run 'lateral')) {
  Step '3/5 Lateral movement (1 IP -> login + 2 patients + file-access)'
  $ok = Copy-And-Run $ApiContainer "$SimDir\sim_lateral_movement.py" @(
    '--url', $ApiInternal,
    '--source-ip', '10.10.88.30'
  )
  if ($ok) { Ok 'lateral termine' } else { Warn 'lateral echec' }
}

# 4) Ransomware
if ($apiUp -and (Should-Run 'ransomware')) {
  Step '4/5 Ransomware-like (FILE_ACCESS volumetrie elevee)'
  $ok = Copy-And-Run $ApiContainer "$SimDir\sim_ransomware.py" @(
    '--url', $ApiInternal,
    '--source-ip', '10.10.99.40'
  )
  if ($ok) { Ok 'ransomware termine' } else { Warn 'ransomware echec' }
}

# 5) IoT critical (MQTT) - execute dans le conteneur iot-simulator qui a paho-mqtt
if ($iotUp -and (Should-Run 'iot')) {
  Step '5/5 Anomalie IoT critique (EMERGENCY publie sur MQTT)'
  $ok = Copy-And-Run $IotContainer "$SimDir\sim_iot_critical.py" @(
    '--host', $MqttHost,
    '--port', '1883',
    '--device-id', 'ECG-ICU-CRITICAL'
  )
  if ($ok) { Ok 'iot_critical termine' } else { Warn 'iot_critical echec' }
}

Write-Host ''
Write-Host '======================================================' -ForegroundColor Magenta
Write-Host ' Toutes les simulations Python ont ete jouees.' -ForegroundColor Magenta
Write-Host ' Verifier les alertes dans Grafana > Alerting > Alert rules' -ForegroundColor Magenta
Write-Host ' ou via demo-attacks.ps1 pour les controles Loki/Telegram.' -ForegroundColor Magenta
Write-Host '======================================================' -ForegroundColor Magenta
Write-Host ''
