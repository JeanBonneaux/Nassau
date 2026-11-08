/*
  roomba694_test1.ino
  Premier test de l'Open Interface (OI) d'un iRobot Roomba 694 avec un ESP32 classique (ESP32-WROOM, devkit 30 ou 38 broches).
  Version 1 — 2026-11-08. Compilé, téléversé et validé sur le robot le 2026-11-08 (arduino-cli 1.5.1, paquet esp32 3.3.7) : voir journal_tests.md.

  CÂBLAGE — valide pour le robot mesuré le 2026-11-08 (TXD robot = 3,3 V ; RXD et BRC tirés à 5 V ; masse sur 6 et 7)
    Robot broche 4 (TXD, 3,3 V)  -> GPIO16 (RX2)        1 kΩ en série conseillé, facultatif
    Robot broche 3 (RXD)         <- GPIO17 (TX2)        1 kΩ en série conseillé, facultatif
    Robot broche 5 (BRC)         <- GPIO4               1 kΩ en série conseillé, facultatif
    Robot broche 6 ou 7 (GND)    -- GND de l'ESP32      obligatoire
    Broches 1 et 2 du robot (Vpwr, 14 à 21 V) : NE PAS RELIER pour ce test. L'ESP32 est alimenté par son câble USB.

  POURQUOI BRC EST PILOTÉ EN SORTIE 3,3 V
    iRobot indique que les lignes RX et DD/BRC du robot acceptent 3,3 V comme niveau haut. Garder la broche en sortie
    (haute au repos, impulsion basse pour réveiller) évite de laisser une entrée de l'ESP32 flotter vers les 5 V du robot.

  UTILISATION
    Moniteur série à 115200 bauds. Taper une touche puis Entrée ('?' = aide). Les roues s'arrêtent seules après 1,5 s.
    Toujours finir par 's' (Passive) puis 'x' (Stop) : en mode Safe/Full le robot ne se recharge pas et ne dort jamais.
*/

#include <Arduino.h>

// ---------- Réglages ----------
constexpr int      PIN_RX  = 16;    // reçoit le TXD du robot (broche 4). Carte WROVER (PSRAM) : prendre 25 à la place.
constexpr int      PIN_TX  = 17;    // vers le RXD du robot (broche 3).  Carte WROVER (PSRAM) : prendre 26 à la place.
constexpr int      PIN_BRC = 4;     // BRC (broche 5)
constexpr int16_t  SPEED_MM_S        = 150;    // vitesse des essais (maximum autorisé par l'OI : 500)
constexpr uint32_t DRIVE_TIMEOUT_MS  = 1500;   // arrêt automatique des roues sans nouvel ordre
constexpr uint32_t KEEP_AWAKE_MS     = 60000;  // période de l'impulsion BRC anti-veille (touche 'a')
constexpr uint32_t ANSWER_TIMEOUT_MS = 200;    // attente maximale d'une réponse capteur

// ---------- Opcodes OI utilisés ----------
enum : uint8_t {
  OI_START = 128, OI_SAFE = 131, OI_FULL = 132, OI_POWER = 133, OI_CLEAN = 135,
  OI_LEDS = 139, OI_SONG = 140, OI_PLAY = 141, OI_SENSORS = 142, OI_DOCK = 143,
  OI_DRIVE_DIRECT = 145, OI_STOP = 173
};

HardwareSerial& robot = Serial2;

bool     driving = false;
uint32_t lastDriveMs = 0;
bool     keepAwake = false;
uint32_t lastKeepAwakeMs = 0;

// ---------- Utilitaires série ----------
void writeI16(int16_t v) {
  uint16_t u = (uint16_t)v;
  robot.write((uint8_t)(u >> 8));      // octet de poids fort d'abord (big-endian, comme l'exige l'OI)
  robot.write((uint8_t)(u & 0xFF));
}

void flushInput() { while (robot.available()) robot.read(); }

bool readExact(uint8_t* buf, size_t n) {
  uint32_t t0 = millis();
  size_t got = 0;
  while (got < n && millis() - t0 < ANSWER_TIMEOUT_MS) {
    if (robot.available()) buf[got++] = (uint8_t)robot.read();
  }
  return got == n;
}

// Interroge un paquet capteur (opcode 142). Renvoie false si le robot ne répond pas.
bool readSensor(uint8_t packetId, uint8_t* buf, size_t len) {
  delay(20);   // au moins 15 ms entre deux requêtes capteur (spec OI) : sans cette pause, une requête sur deux restait sans réponse sur le 694 (test du 2026-11-08)
  flushInput();
  robot.write(OI_SENSORS);
  robot.write(packetId);
  return readExact(buf, len);
}

uint16_t u16(const uint8_t* b) { return ((uint16_t)b[0] << 8) | b[1]; }
int16_t  i16(const uint8_t* b) { return (int16_t)u16(b); }

void noAnswer() {
  Serial.println(F("Pas de réponse du robot. Est-il réveillé et l'OI ouverte ? Essayez 'w' puis 's' ; sinon appuyez sur CLEAN."));
}

// ---------- Commandes robot ----------
void brcPulse() {
  digitalWrite(PIN_BRC, LOW);   // tire BRC à la masse
  delay(200);
  digitalWrite(PIN_BRC, HIGH);  // relâche : 3,3 V = niveau haut accepté par le robot
  delay(200);
}

void setMode(uint8_t opcode, const __FlashStringHelper* name) {
  robot.write(opcode);
  delay(50);
  Serial.print(F("Envoyé : "));
  Serial.println(name);
}

void driveDirect(int16_t right, int16_t left) {
  robot.write(OI_DRIVE_DIRECT);
  writeI16(right);   // roue droite d'abord, puis roue gauche (ordre imposé par l'OI)
  writeI16(left);
  driving = (right != 0 || left != 0);
  lastDriveMs = millis();
}

void stopWheels() {
  driveDirect(0, 0);
  Serial.println(F("Roues arrêtées."));
}

void playJingle() {
  // Chanson 0, 3 notes (do5, mi5, sol5), durées en 1/64 s. Définition possible en Passive, lecture en Safe/Full.
  const uint8_t song[] = { OI_SONG, 0, 3, 72, 16, 76, 16, 79, 24 };
  robot.write(song, sizeof(song));
  delay(20);
  robot.write(OI_PLAY);
  robot.write((uint8_t)0);
  Serial.println(F("Chanson envoyée (mode Safe requis : 'f' d'abord)."));
}

void ledDemo() {
  // Voyant Dock allumé, anneau CLEAN vert à pleine intensité. Mode Safe/Full requis.
  const uint8_t cmd[] = { OI_LEDS, 4, 0, 255 };
  robot.write(cmd, sizeof(cmd));
  Serial.println(F("LEDs envoyées (mode Safe requis)."));
}

void printBattery() {
  uint8_t b[2];
  if (!readSensor(22, b, 2)) { noAnswer(); return; }
  Serial.printf("Tension batterie : %u mV   (multimètre sur Vpwr : 14,66 V)\n", u16(b));
  if (readSensor(23, b, 2)) Serial.printf("Courant : %d mA   (négatif = décharge)\n", i16(b));
  if (readSensor(24, b, 1)) Serial.printf("Température : %d °C\n", (int8_t)b[0]);
  uint16_t charge = 0;
  if (readSensor(25, b, 2)) {
    charge = u16(b);
    if (readSensor(26, b, 2)) Serial.printf("Charge : %u / %u mAh\n", charge, u16(b));
  }
  if (readSensor(21, b, 1)) Serial.printf("État de charge : %u   (0 pas en charge, 1 reconditionnement, 2 pleine, 3 entretien, 4 attente, 5 défaut)\n", b[0]);
  if (readSensor(35, b, 1)) Serial.printf("Mode OI lu : %u   (0 Off, 1 Passive, 2 Safe, 3 Full ; sur 690/694 la valeur est souvent décalée de +1)\n", b[0]);
}

void printSensors() {
  uint8_t b[1];
  if (!readSensor(7, b, 1)) { noAnswer(); return; }
  Serial.printf("Pare-chocs : droit %u, gauche %u | Roue levée : droite %u, gauche %u\n",
                b[0] & 1, (b[0] >> 1) & 1, (b[0] >> 2) & 1, (b[0] >> 3) & 1);
  const uint8_t cliffIds[4] = { 9, 10, 11, 12 };
  const char* cliffNames[4] = { "gauche", "avant gauche", "avant droit", "droit" };
  Serial.print(F("Vide (cliff) :"));
  for (int i = 0; i < 4; i++) {
    if (readSensor(cliffIds[i], b, 1)) Serial.printf(" %s %u", cliffNames[i], b[0]);
    else Serial.print(F(" ?"));
  }
  Serial.println();
  if (readSensor(45, b, 1)) {
    Serial.print(F("Light bumper (G, AvG, CG, CD, AvD, D) :"));
    for (int bit = 0; bit < 6; bit++) Serial.printf(" %u", (b[0] >> bit) & 1);
    Serial.println();
  }
  if (readSensor(18, b, 1)) Serial.printf("Boutons : CLEAN %u, SPOT %u, DOCK %u\n", b[0] & 1, (b[0] >> 1) & 1, (b[0] >> 2) & 1);
}

void printHelp() {
  Serial.println(F(
    "\n=== Roomba 694 — test OI v1 ===\n"
    " ?  aide                         w  impulsion BRC (réveil)\n"
    " s  Start -> Passive             f  Safe (contrôle, sécurités actives)\n"
    " c  Clean                        h  retour à la base\n"
    " b  batterie / mode OI           e  pare-chocs, vide, boutons\n"
    " m  jouer 3 notes (Safe)         l  LEDs (Safe)\n"
    " 8  avance   2  recule   4  tourne à gauche   6  tourne à droite   5 ou espace  stop\n"
    "    (chaque ordre dure 1,5 s puis les roues s'arrêtent seules)\n"
    " a  anti-veille BRC toutes les 60 s (on/off)\n"
    " o  Power (extinction)           x  Stop OI (à faire en fin de session)\n"));
}

void handle(char c) {
  switch (c) {
    case '?': printHelp(); break;
    case 'w': brcPulse(); Serial.println(F("Impulsion BRC envoyée.")); break;
    case 's': setMode(OI_START, F("Start (128) -> Passive")); break;
    case 'f': setMode(OI_SAFE,  F("Safe (131)")); break;
    case 'c': setMode(OI_CLEAN, F("Clean (135)")); break;
    case 'h': setMode(OI_DOCK,  F("Seek Dock (143)")); break;
    case 'b': printBattery(); break;
    case 'e': printSensors(); break;
    case 'm': playJingle(); break;
    case 'l': ledDemo(); break;
    case '8': driveDirect( SPEED_MM_S,  SPEED_MM_S); Serial.println(F("Avance.")); break;
    case '2': driveDirect(-SPEED_MM_S, -SPEED_MM_S); Serial.println(F("Recule.")); break;
    case '4': driveDirect( SPEED_MM_S, -SPEED_MM_S); Serial.println(F("Tourne à gauche.")); break;
    case '6': driveDirect(-SPEED_MM_S,  SPEED_MM_S); Serial.println(F("Tourne à droite.")); break;
    case '5': case ' ': stopWheels(); break;
    case 'a':
      keepAwake = !keepAwake;
      lastKeepAwakeMs = millis();
      Serial.println(keepAwake ? F("Anti-veille activé.") : F("Anti-veille désactivé."));
      break;
    case 'o': setMode(OI_POWER, F("Power (133)")); break;
    case 'x': setMode(OI_STOP,  F("Stop (173) -> OI fermée")); break;
    default:  Serial.printf("Touche inconnue : '%c' ('?' pour l'aide)\n", c); break;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BRC, OUTPUT);
  digitalWrite(PIN_BRC, HIGH);
  robot.begin(115200, SERIAL_8N1, PIN_RX, PIN_TX);   // réglage par défaut du Roomba 600 : 115200 bauds, 8N1
  delay(500);
  printHelp();
  Serial.println(F("Séquence conseillée : w, s, b  (la tension lue doit être proche de 14,66 V)."));
}

void loop() {
  if (driving && millis() - lastDriveMs > DRIVE_TIMEOUT_MS) stopWheels();
  if (keepAwake && millis() - lastKeepAwakeMs > KEEP_AWAKE_MS) { brcPulse(); lastKeepAwakeMs = millis(); }
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') continue;   // ignore les fins de ligne du moniteur série
    handle(c);
  }
}
