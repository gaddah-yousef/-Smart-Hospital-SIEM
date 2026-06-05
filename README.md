# 🏥🛡️ Smart Hospital SIEM

> **Plateforme de supervision et détection de menaces pour environnement hospitalier intelligent**
> Projet fédérateur — École Nationale Supérieure des Mines de Rabat (ENSMR) — 2025/2026

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)]()
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)]()
[![Grafana](https://img.shields.io/badge/Grafana-stack-F46800.svg)]()
[![MITRE ATT&CK](https://img.shields.io/badge/MITRE-ATT%26CK-red.svg)]()

---

## 📖 Présentation

**Smart Hospital SIEM** est un système de **Security Information and Event Management (SIEM)** complet, conçu pour les environnements hospitaliers connectés. Il combine **observabilité moderne**, **streaming temps réel**, **règles MITRE ATT&CK** et **Machine Learning** pour détecter en moins de 3 secondes les attaques visant les applications métier, les dispositifs IoT médicaux et le réseau hospitalier.

Ce module fait partie d'un projet fédérateur plus large — le **Système Hospitalier Intelligent** — qui inclut également un module de prédiction du flux de patients et un assistant médical IA.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  SOURCES                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ Hospital   │  │ IoT médical│  │   Zeek     │             │
│  │    API     │  │ (ECG, pump,│  │  (réseau)  │             │
│  │  (Flask)   │  │ vent, CT)  │  │            │             │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘             │
│        │ logs+traces   │ MQTT          │ pcap                 │
│        ▼               ▼               ▼                      │
│  ┌──────────────────────────────────────────┐                │
│  │  Mosquitto  │  Alloy (OpenTelemetry)    │                │
│  └──────────────────────────────────────────┘                │
└─────────────┬────────────────────────────────────────────────┘
              ▼
       ┌──────────────────────────────────────────┐
       │   Apache Kafka (9 topics)                │
       └──────────────┬───────────────────────────┘
                      ▼
       ┌──────────────────────────────────────────┐
       │  SIEM Backend (FastAPI + Faust)          │
       │  ├─ Rule Engine (5 règles MITRE)         │
       │  ├─ Sliding Correlator                   │
       │  └─ ML : Isolation Forest + LSTM         │
       └────┬────────────┬───────────┬────────────┘
            ▼            ▼           ▼
       ┌────────┐  ┌────────┐  ┌────────┐
       │  Loki  │  │ Mimir  │  │ Tempo  │
       │ (logs) │  │(metric)│  │(traces)│
       └────┬───┘  └────┬───┘  └────┬───┘
            └───────────┼───────────┘
                        ▼
              ┌──────────────────┐
              │   Grafana        │
              │ + Telegram + SMTP│
              └──────────────────┘
```

---

## 🎯 Fonctionnalités

### Détection multi-couches alignée MITRE ATT&CK

| Règle | Technique MITRE | Sévérité |
|-------|-----------------|----------|
| `brute_force_login` | T1110 — Brute Force | HIGH |
| `unauthorized_patient_access` | T1078 — Valid Accounts | CRITICAL |
| `lateral_movement` | T1021 — Remote Services | HIGH |
| `ransomware_pattern` | T1486 — Data Encrypted for Impact | CRITICAL |
| `iot_critical_anomaly` | T0858 — Exploitation of ICS | EMERGENCY |

### Machine Learning hybride

- **Isolation Forest** (scikit-learn) — détection d'anomalies comportementales (6 features par IP source)
- **LSTM Autoencoder** (TensorFlow/Keras) — anomalies temporelles sur signaux IoT
- Réentraînement automatique via APScheduler (24h / 7j)

### Alerting multi-canal

- 📱 **Telegram Bot** — notifications instantanées au SOC
- 📧 **Email SMTP** — alertes formatées pour l'équipe
- 🪝 **Webhooks Grafana** — intégration avec systèmes tiers

---

## 🛠️ Stack technologique

| Catégorie | Technologies |
|-----------|--------------|
| **Observabilité** | Grafana, Loki, Mimir, Tempo, Alloy |
| **Streaming** | Apache Kafka, Apache Faust |
| **IoT** | MQTT (Mosquitto) |
| **NSM** | Zeek |
| **Backend** | Python 3.11, FastAPI, Flask |
| **ML/IA** | scikit-learn, TensorFlow/Keras, APScheduler |
| **Sécurité** | JWT (HS256), bcrypt, RBAC, OAuth2 |
| **Conteneurisation** | Docker, Docker Compose (16 services) |
| **Tracing** | OpenTelemetry (OTLP gRPC/HTTP) |

---

## 🚀 Démarrage rapide

### Pré-requis
- Docker Desktop (ou Docker Engine + Compose)
- 8 Go RAM minimum recommandés
- Ports 3000, 3100, 3200, 5000, 8000, 8080, 9009, 9090 disponibles

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/gaddah-yousef/-Smart-Hospital-SIEM.git
cd -Smart-Hospital-SIEM

# 2. Configurer les secrets
cp .env.example .env
# Editer .env et remplir TELEGRAM_BOT_TOKEN, SMTP_*, etc.

# 3. Lancer la stack
docker compose up -d --build

# 4. (Windows PowerShell - tout-en-un)
.\start-and-simulate.ps1
```

### Accès aux services

| Service | URL | Identifiants |
|---------|-----|--------------|
| Grafana | http://localhost:3000 | admin / (voir .env) |
| Hospital API | http://localhost:5000 | — |
| SIEM Backend API | http://localhost:8000/docs | admin / (voir .env) |
| Kafka UI | http://localhost:8080 | — |
| Prometheus | http://localhost:9090 | — |
| Loki | http://localhost:3100 | — |
| Mimir | http://localhost:9009 | — |
| Tempo | http://localhost:3200 | — |

---

## 🎯 Simulation d'attaques

5 scripts Python jouent des attaques réalistes :

```powershell
# Lancer toutes les simulations
.\run-all-sims.ps1

# Une attaque spécifique
.\run-all-sims.ps1 -Only ransomware
.\run-all-sims.ps1 -Only iot
.\run-all-sims.ps1 -Only brute_force -BruteForceAttempts 20

# Générer du trafic réseau pour Zeek
.\generate-network-traffic.ps1 -Intensity high
```

---

## 📊 Dashboards Grafana

4 dashboards provisionnés automatiquement dans le folder **Smart Hospital SIEM** :

1. **Hospital SIEM Overview** — supervision 24/7 (compteurs, top IPs, login failures)
2. **IoT Medical Devices Monitor** — ECG, SpO2, pompes à perfusion, scores LSTM
3. **ML Anomaly Scores** — Isolation Forest par IP + erreurs LSTM par appareil
4. **Advanced SIEM Analytics** — distribution sévérité, event types, top sources
5. **Network Security (Zeek)** — top IPs, ports, services, notices

---

## 📈 Résultats validés (test E2E APT)

| Métrique | Valeur |
|----------|--------|
| Alertes générées sur une APT complète | **182** |
| Latence détection-alerte | **< 3 secondes** |
| Reconstruction kill-chain ransomware | **20 secondes** |
| Notifications Telegram | **< 5 secondes** |
| Conformité réglementaire | **HIPAA, RGPD, ISO 27001** |

Détail par règle :

| Règle | Alertes | IPs distinctes |
|-------|---------|----------------|
| brute_force_login | 14 | 4 |
| unauthorized_patient_access | 45 | 3 |
| iot_critical_anomaly | 115 | 11 |
| lateral_movement | 2 | 2 |
| ransomware_pattern | 6 | 1 |

---

## 📁 Structure du projet

```
smart-hospital-siem-grafana/
├── docker-compose.yml          # Orchestration des 16 services
├── .env.example                # Template de configuration
├── README.md
│
├── hospital-api/               # API Flask hospitalière
├── siem-backend/               # FastAPI + Faust + ML
│   ├── api/                    # Routers REST + auth JWT
│   ├── stream/                 # Faust consumer + rule engine
│   ├── ml/                     # Isolation Forest + LSTM
│   └── alerting/               # Telegram, Email, Webhooks
├── iot-simulator/              # Capteurs IoT simulés
├── attack-simulations/         # 5 scripts d'attaque Python
├── detection-rules/            # Règles YAML SIGMA-like
│
├── grafana/                    # Dashboards + alerting provisionnés
├── loki/                       # Config Loki
├── mimir/                      # Config Mimir
├── tempo/                      # Config Tempo
├── alloy/                      # Config Alloy (collecteur)
├── prometheus/                 # Config Prometheus
├── mosquitto/                  # Config MQTT
└── zeek/                       # Scripts Zeek de détection
```

---

## 🔒 Sécurité

### À faire AVANT de déployer en production
- [ ] Régénérer `JWT_SECRET_KEY` (32+ caractères aléatoires)
- [ ] Changer tous les `SIEM_ADMIN_PASSWORD` et `GRAFANA_ADMIN_PASSWORD`
- [ ] Créer un nouveau bot Telegram dédié
- [ ] Migrer les secrets vers HashiCorp Vault ou AWS Secrets Manager
- [ ] Activer le TLS entre services internes (mTLS recommandé)
- [ ] Configurer une politique de rotation des credentials

---

## 👥 Équipe

| Rôle | Membre |
|------|--------|
| **Cybersécurité & SIEM** | **Yousef GADDAH** ([@gaddah-yousef](https://github.com/gaddah-yousef)) |
| Prédiction ML | El Makrini Khalid |
| Assistant médical IA | Addou Basma |
| Backend & Architecture | Amguine Marouane |
| Frontend & UX | Chtibi Ghizlane |
| **Encadrement** | Pr. Hayat ZAYDI |
| **Jury** | Pr. Kawtar TIKITO (Présidente), Pr. Hamza TOULNI (Rapporteur) |

---

## 📜 Licence

Projet académique — ENSMR 2025/2026. Code libre d'utilisation à des fins éducatives.

---

## 🙏 Remerciements

Un grand merci à **Pr. Hayat ZAYDI** pour son encadrement précieux, et au jury pour leurs retours constructifs lors de la soutenance du **5 juin 2026**.

---

*"La cybersécurité hospitalière n'est plus une option — c'est un acte de patient safety."*
