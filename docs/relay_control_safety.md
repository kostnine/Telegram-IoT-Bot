# 🔌 Relay Modulių Saugus Valdymas

## ⚠️ SAUGUMO PERSPĖJIMAI

### 🚨 KRITIŠKAI SVARBU:
- **NIEKADA** nedirbkite su 220V/240V įtampa be patirties
- **VISADA** išjunkite elektros grandinę prieš jungiant
- **NAUDOKITE** optocoupler relay modulius (4-channel)
- **PATIKRINKITE** visas jungtis du kartus
- **TURĖKITE** automatinį saugiklį grandinėje

### 🛡️ Saugumo Priemonės:
1. **Fused relay board** (su saugikliais)
2. **Optocoupler isolation** (apsauga mikrokontroleriams)
3. **Proper enclosure** (plastikinis korpusas)
4. **Circuit breakers** (automatiniai saugikliai)
5. **Ground fault protection** (žemės nuotėkio apsauga)

## 🔧 Relay Jungimo Schema

### ESP32 → Relay Board:
```
ESP32 GPIO    →    Relay Module
GPIO 5        →    IN1 (Channel 1)
GPIO 18       →    IN2 (Channel 2)  
GPIO 19       →    IN3 (Channel 3)
GPIO 21       →    IN4 (Channel 4)
GND           →    GND
5V (VIN)      →    VCC
```

### Relay Board → Prietaisai (240V):
```
RELAY 1 (Apšvietimas):
L (Live) → Relay COM → Relay NO → Lempa L
N (Neutral) → Tiesiogiai į Lempa N

RELAY 2 (Ventiliatorius):
L (Live) → Relay COM → Relay NO → Vent L  
N (Neutral) → Tiesiogiai į Vent N

RELAY 3 (Šildytuvas):
L (Live) → Relay COM → Relay NO → Šild L
N (Neutral) → Tiesiogiai į Šild N

RELAY 4 (Rezervas):
Neišnaudota
```

## 🏠 Smart Home Aplikacijos

### 💡 Apšvietimo Valdymas:
- Automatinis įjungimas/išjungimas pagal laiką
- Šviestumo reguliavimas (su dimmer relay)
- Judesio sensorių integracija
- "Namie/Ne namie" scenarijai

### 🌡️ Šildymo/Vėsinimo Valdymas:
- Temperatūros palaikymas
- Programuojami režimai
- Energijos taupymas
- Nuotolinė kontrolė

### 💧 Vandens Sistemos:
- Laistymo automatizavimas  
- Boilerio valdymas
- Nuotėkių aptikimas
- Siurblių kontrolė

### 🔐 Saugos Sistemos:
- Durų spynų valdymas
- Signalizacijos jungimai
- Kamerų maitinimas
- Sirenos valdymas

## 📱 Telegram Bot Komandos

Jūsų bot jau palaiko šias komandas:

### Relay Valdymas:
- `relay_on` - Įjungti relay
- `relay_off` - Išjungti relay  
- `relay_toggle` - Perjungti relay
- `relay1_on` / `relay1_off` - Konkretus relay

### Saugūs Režimai:
- **Manual Mode**: Tik rankiniai komandos
- **Automatic Mode**: Pagal sensor'ius
- **Schedule Mode**: Pagal tvarkaraštį
- **Emergency Mode**: Viską išjungti

## ⚡ Elektros Suvartojimo Kontrolė

### Galios Matavimas:
```python
# Pridėti į ESP32 kodą
#include <PZEM004Tv30.h>

PZEM004Tv30 pzem(Serial2, 16, 17); // RX, TX pins

void measurePower() {
    float voltage = pzem.voltage();
    float current = pzem.current();
    float power = pzem.power();
    float energy = pzem.energy();
    
    // Send power data to MQTT
    sendPowerData(voltage, current, power, energy);
}
```

### Energijos Taupymas:
- **Peak hours** aptikimas (brangūs elektros tarifai)
- **Automatic load shedding** (sumažinti apkrovą)
- **Priority devices** (svarbūs prietaisai pirmi)
- **Energy monitoring** (suvartojimo stebėjimas)

## 🔧 Praktinis Pavyzdys: Smart Lempa

### Aparatūra:
- ESP32 DevKit
- 4-Channel Relay Module
- DHT22 temperatūros sensorius
- PIR motion sensor
- Fotoresistorius (šviestumo)

### Funkcionalumas:
1. **Automatinis įjungimas**: Judesys + tamsu
2. **Programuojamas**: Įjungti 19:00, išjungti 23:00
3. **Nuotolinis valdymas**: Telegram komandos
4. **Energijos taupymas**: Išjungti jei niekas namie
5. **Saugumo režimas**: Blink režimas kai signalizacija

### Konfigūracija per Bot:
```
/relay1_schedule 19:00-23:00
/relay1_motion_enable
/relay1_brightness_threshold 20
/relay1_safety_mode on
```

## 🏭 Pramonės Aplikacijos

### Gamybos Linijos:
- Konvejerių valdymas
- Siurblių kontrolė  
- Ventiliatorių sistema
- Signalizacijos lempos

### Ūkio Automatizacija:
- Šiltnamių klimatas
- Laistymo sistemos
- Pašarų dozavimas
- Ventiliacijos valdymas

### Saugyklos:
- Apšvietimo valdymas
- Klimato kontrolė
- Saugos sistemos
- Prieigos kontrolė

## 🛠️ Troubleshooting

### Dažnos Problemos:

1. **Relay nereaguoja**:
   - Patikrinti maitinimą (5V)
   - Patikrinti GPIO jungtis
   - Išmatuoti signalą multimetru

2. **WiFi atsijungia**:
   - Patikrinti signalo stiprumą
   - Pridėti reconnection logic
   - Naudoti WiFiManager biblioteką

3. **Atsitiktinis išjungimas**:
   - Patikrinti maitinimo stabilumą
   - Pridėti kondensatorių
   - Naudoti UPS (nelabai mažai sistemos)

4. **MQTT žinutės praranda**:
   - Patikrinti QoS settings
   - Pridėti message buffering
   - Naudoti retained messages

## ⚙️ Rekomendacijos

### Pradedantiesiems:
1. Pradėti su **DC relay** (12V/24V prietaisai)
2. Išmokti **multimetro** naudojimą
3. **Modulinis dizainas** (vienas relay = viena funkcija)
4. **Testing suite** (automatiniai testai)

### Pažengusiems:
1. **Load balancing** (apkrovos paskirstymas)
2. **Predictive maintenance** (prognozuojamas remontas)
3. **Machine learning** (išmanusis valdymas)
4. **Industrial protocols** (Modbus, BACnet)

---

**🚨 ATMINKITE: Saugumas visada pirmoje vietoje!**
