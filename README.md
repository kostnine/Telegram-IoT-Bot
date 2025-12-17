# Telegram IoT Bot

IoT įrenginių stebėsenos ir valdymo sistema per Telegram botą ir MQTT protokolą.

## Projekto struktūra

```
Telegram-IoT-Bot/
├── run.py                      # Pagrindinis paleidimo failas
├── requirements.txt            # Python priklausomybės
├── .env                        # Konfigūracijos failas
│
├── config/
│   └── settings.py             # Bot ir MQTT nustatymai
│
├── src/
│   ├── bot/
│   │   └── main.py             # Telegram bot handleriai
│   ├── mqtt/
│   │   └── client.py           # MQTT klientas
│   ├── handlers/
│   │   ├── iot_commands.py     # IoT komandos
│   │   └── advanced_commands.py # Analitika ir grafikai
│   └── services/
│       ├── data_storage.py     # SQLite duomenų bazė
│       ├── analytics.py        # Grafikai ir ataskaitos
│       └── automation_engine.py # Automatizacijos taisyklės
│
└── simulators/                 # IoT įrenginių simuliatoriai
    ├── pc_monitor_free.py      # PC sistemos monitorius
    ├── phone_sensor_app.html   # Telefono sensorių app
    ├── https_server.py         # HTTPS serveris telefonui
    └── LibreHardwareMonitorLib.dll # Temperatūrų monitoringas
```

## Greitas paleidimas

### 1. Įdiegti priklausomybes
```bash
pip install -r requirements.txt
```

### 2. Sukonfigūruoti .env failą
```env
TELEGRAM_BOT_TOKEN=jusu_bot_token
MQTT_BROKER=jusu_brokeris.emqxsl.com
MQTT_PORT=8883
MQTT_USERNAME=vartotojo_vardas
MQTT_PASSWORD=slaptazodis
MQTT_USE_TLS=true
```

### 3. Paleisti botą
```bash
python run.py
```

### 4. Paleisti PC monitorių (neprivaloma)
```bash
cd simulators
python pc_monitor_free.py
```
**Pastaba:** Temperatūrų monitoringui reikia paleisti kaip administratorius.

### 5. Paleisti telefono app (neprivaloma)
```bash
cd simulators
python https_server.py
# Atidaryti telefone: https://<jusu_ip>:8443/phone_sensor_app.html
```

---

## Funkcionalumas

- 🤖 **Telegram Bot**: Inline klaviatūra, komandos, realaus laiko pranešimai
- 📡 **MQTT Protokolas**: TLS šifruota komunikacija per EMQX Cloud
- 💻 **PC Monitorius**: CPU, RAM, diskas, tinklas, temperatūra (LibreHardwareMonitor)
- 📱 **Telefono sensoriai**: GPS, akselerometras, giroskopas, kompasas, mikrofonas
- 🎛️ **Nuotolinis valdymas**: Lock, Sleep, Shutdown, Beep, Vibrate
- 🚨 **Įspėjimų sistema**: Kritinė temperatūra, aukštas CPU, žema baterija
- 📊 **Analitika**: Grafikai ir statistika (SQLite saugykla)

## Palaikomi įrenginiai

### PC Monitorius (Windows)
- **Sensoriai**: CPU %, RAM %, disko užimtumas, tinklo srautas, procesų skaičius, temperatūros
- **Komandos**: Lock, Screen Off, Sleep, Restart, Shutdown

### Telefono sensorių App (iOS/Android per HTTPS)
- **Sensoriai**: GPS, akselerometras, giroskopas, kompasas, garso lygis, baterija
- **Komandos**: Beep, Vibrate, Lock screen, Location request

## Architektūra

```
Telegram Bot ←→ MQTT Broker ←→ IoT Įrenginiai
     ↓              ↓              ↓
Vartotojo sąsaja  Žinučių eilė   Sensoriai/Valdikliai
```

## MQTT Temų struktūra

- `iot/devices/{device_id}/status` - Įrenginio būsena
- `iot/devices/{device_id}/data` - Sensorių duomenys
- `iot/devices/{device_id}/control` - Valdymo komandos
- `iot/alerts` - Sistemos įspėjimai
- `iot/system/status` - Sistemos būsena

## Diegimas

1. **Klonuoti projektą**
   ```bash
   git clone <repository-url>
   cd Telegram-IoT-Bot
   ```

2. **Įdiegti priklausomybes**
   ```bash
   pip install -r requirements.txt
   ```

3. **Sukonfigūruoti aplinkos kintamuosius**
   ```bash
   cp .env.example .env
   # Redaguoti .env su savo nustatymais
   ```

4. **Sukurti Telegram botą**
   - Sukurti naują botą su [@BotFather](https://t.me/botfather)
   - Gauti bot token
   - Įrašyti token į `.env` failą

5. **Sukonfigūruoti MQTT brokerį**
   - Užsiregistruoti [EMQX Cloud](https://www.emqx.com/en/cloud) (nemokamas planas)
   - Atnaujinti MQTT nustatymus `.env` faile

## Konfigūracija

### Aplinkos kintamieji

| Kintamasis | Aprašymas | Numatyta |
|------------|-----------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token iš BotFather | Privalomas |
| `MQTT_BROKER` | MQTT brokerio adresas | localhost |
| `MQTT_PORT` | MQTT brokerio portas | 8883 |
| `MQTT_USERNAME` | MQTT vartotojo vardas | - |
| `MQTT_PASSWORD` | MQTT slaptažodis | - |
| `MQTT_USE_TLS` | TLS šifravimas | true |
| `ADMIN_USER_IDS` | Administratorių Telegram ID | - |

## Naudojimas

### Bot komandos

- `/start` - Pagrindinis meniu
- `/help` - Pagalbos pranešimas
- `/status` - Visų įrenginių būsena
- `/devices` - Prijungtų įrenginių sąrašas
- `/alerts` - Paskutiniai įspėjimai

### Telegram meniu mygtukai

- 📱 **Įrenginiai** - Prijungtų įrenginių sąrašas
- 📈 **Grafikai** - Analitika ir statistika
- 🚨 **Alertai** - Kritinių įvykių sąrašas
- 🔄 **Atnaujinti** - Atnaujinti būseną

## MQTT žinučių formatas

### Įrenginio būsena
```json
{
  "device_id": "pc_desktop-abc123",
  "online": true,
  "type": "pc_system_monitor",
  "location": "PC - DESKTOP-ABC123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Sensorių duomenys
```json
{
  "device_id": "pc_desktop-abc123",
  "sensor_type": "cpu_percent",
  "value": 15.5,
  "unit": "%",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Valdymo komanda
```json
{
  "action": "lock",
  "timestamp": "2025-01-15T10:30:00Z",
  "source": "telegram_bot"
}
```

### Įspėjimas
```json
{
  "level": "CRITICAL",
  "message": "Aukšta CPU temperatūra: 85°C",
  "device_id": "pc_desktop-abc123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Saugumo aspektai

- 🔐 **Aplinkos kintamieji**: Jautrūs duomenys saugomi `.env` faile
- 🔒 **MQTT saugumas**: TLS šifravimas ir autentifikacija
- 👥 **Administratorių kontrolė**: Tik leistini vartotojai gali valdyti įrenginius

## Problemų sprendimas

### Dažnos problemos

1. **Botas neatsako**
   - Patikrinkite Telegram bot token
   - Patikrinkite interneto ryšį

2. **MQTT prisijungimas nepavyko**
   - Patikrinkite ar brokeris veikia
   - Patikrinkite prisijungimo duomenis
   - Patikrinkite ar TLS įjungtas

3. **Temperatūra nerodoma**
   - Paleiskite `pc_monitor_free.py` kaip administratorius
   - Įdiekite `pythonnet`: `pip install pythonnet`

4. **Įrenginiai nerasti**
   - Patikrinkite ar įrenginiai siunčia į teisingas MQTT temas
   - Patikrinkite įrenginių prisijungimą

## Licencija

MIT License
