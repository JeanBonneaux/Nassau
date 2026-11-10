/*
  roomba694_wifi.ino — Roomba 694 piloté par un ESP32 : console et page web par Wi-Fi, gyroscope, mises à jour du firmware par Wi-Fi.
  Version 4 — 2026-11-09 (soir) :
    - lecture des capteurs par une seule requête (142 puis 100 : paquets 7 à 58, 80 octets, réponse en 13 ms) à la place
      de la liste 149 et de la lecture paquet par paquet (22 requêtes par cycle) : voir plus bas « Lecture des capteurs » ;
    - les ordres de roues ne partent plus que si le robot est en mode Safe (voir wheelsAllowed) ;
    - un texte envoyé par le robot (il en envoie en redémarrant) est reconnu, compté et affiché (touche v pour écouter la ligne) ;
    - position du robot (x, y, cap) calculée avec les compteurs des roues et le gyroscope, tracé sur la page
      (fichier position.ino, /api/pose, touche 0) : étape 2 de la cartographie (notes/H_cartographie_strategie.md).
  Version 3 — 2026-11-09 : « radar » à ultrasons, capteur HC-SR04 sur servo SG90 (fichier radar.ino : modes arrêt / fixe /
    balayage, carte polaire sur la page web, arrêt automatique devant un obstacle, /api/radar, touches r et u, colonne us_mm
    du CSV) et tour sur place (tour.ino). Essayés sur le matériel le 2026-11-09.
  Version 2 — 2026-11-08. Dérivé de roomba694_test1 (mêmes touches, même câblage, mêmes sécurités), avec en plus :
    - un point d'accès Wi-Fi « Roomba694 » toujours actif (adresse 192.168.4.1), et en option la connexion au réseau
      de la maison, enregistré depuis la page /wifi (identifiants stockés dans la carte, jamais dans le code ni affichés) ;
    - une console TCP sur le port 23 : mêmes touches qu'en USB, la sortie va à la fois sur l'USB et vers le client TCP ;
    - une page web sur le port 80 (fichier web.ino) : pavé de pilotage « maintenir pour rouler », vitesse réglable,
      batterie, capteurs dessinés, cap du gyroscope, console intégrée (/api/log), état en JSON (/api/state), /wifi, /update ;
    - une lecture périodique des capteurs (toutes les 200 ms ; par le groupe de paquets 100 depuis la version 4) ;
    - un gyroscope MPU-6050 (module GY-521) lu à 100 Hz sur le second cœur : cap intégré (touches g, z) ;
    - un journal CSV (touche j) ;
    - deux voies de mise à jour sans câble : la page /update (fichier .bin compilé) et ArduinoOTA (arduino-cli upload -p <adresse IP>).

  CÂBLAGE : identique à roomba694_test1. Robot trou 4 (TXD, 3,3 V) -> GPIO16 (RX2) ; trou 3 (RXD) <- GPIO17 (TX2) ;
  trou 5 (BRC) <- GPIO4 ; trou 6 ou 7 (GND) -- GND. Broches 1-2 du robot (batterie, 14 à 21 V) : jamais reliées.
  L'ESP32 est alimenté par son USB (PC ou batterie portable).
  Radar (v3) : signal du servo SG90 sur D18, HC-SR04 Trig sur D19 et Echo sur D23 à travers un diviseur 1 kΩ / 2 kΩ ; les deux
  modules en 5 V pris sur la broche VIN de la carte (environ 4,7 V sur USB) par un fil posé par l'utilisateur jusqu'à la ligne
  rouge de la bande d'alimentation libre du côté VIN de la plaque (décision du 2026-11-09), jamais sur 3V3 ni sur la ligne rouge
  du côté 3V3. Détail : radar.ino et notes/G_radar_ultrason_servo.md.

  SÉCURITÉ : vitesse plafonnée à 150 mm/s, pas de mode Full, arrêt automatique des roues 1,5 s après chaque ordre,
  arrêt des roues si le client TCP se déconnecte ou si une mise à jour commence. Rien n'est envoyé au robot au démarrage.
  Toujours finir par 's' puis 'x' (en Safe/Full le robot ne se recharge pas et ne dort jamais).

  MOT DE PASSE : « roomba694 » par défaut (point d'accès et ArduinoOTA). Pour le changer, copier
  secrets.example.h en secrets.h (ignoré par git), modifier AP_PASS (8 caractères minimum) et recompiler.
  La page /update n'en demande plus depuis le 2026-11-09 (décision de l'utilisateur, réseau de la maison jugé sûr) : elle
  accepte tout envoi adressé à la carte depuis son réseau, sauf ceux venus d'une page d'un autre site (web.ino,
  updateRequestIsLocal). Tout appareil du réseau de la maison ou du point d'accès peut donc mettre la carte à jour.

  PIÈGES MESURÉS SUR CE 694 (voir journal_tests.md) : au moins 15 ms entre deux requêtes capteur ; mode OI lu décalé de +1 ;
  paquet 19 (distance) faux, se fier aux encodeurs 43/44 ; après un réveil par BRC, octets parasites possibles et
  rendormissement rapide : préférer un appui sur CLEAN, ou envoyer 's' puis un ordre dans la minute.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Update.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <Wire.h>
#include "driver/gpio.h"
#include "esp_system.h"   // esp_reset_reason() : pourquoi la carte a redémarré

#if __has_include("secrets.h")
#include "secrets.h"
#endif
#ifndef AP_SSID
#define AP_SSID "Roomba694"
#endif
#ifndef AP_PASS
#define AP_PASS "roomba694"
#endif
#ifndef HOSTNAME
#define HOSTNAME "roomba694"
#endif

// ---------- Réglages ----------
constexpr int      PIN_RX  = 16;    // reçoit le TXD du robot (trou 4)
constexpr int      PIN_TX  = 17;    // vers le RXD du robot (trou 3)
constexpr int      PIN_BRC = 4;     // BRC (trou 5)
constexpr int16_t  SPEED_MM_S        = 150;    // plafond des essais (maximum de l'OI : 500)
constexpr uint32_t DRIVE_TIMEOUT_MS  = 1500;   // arrêt automatique des roues sans nouvel ordre
constexpr uint32_t KEEP_AWAKE_MS     = 45000;  // période de l'impulsion BRC anti-veille (touche 'a') ; d'autres montages constatent qu'il en faut plus d'une par minute
constexpr uint32_t ANSWER_TIMEOUT_MS = 200;    // attente maximale d'une réponse capteur
constexpr uint32_t INTER_QUERY_MS    = 20;     // pause minimale entre deux requêtes capteur (spec : 15 ms)
constexpr uint32_t POLL_PERIOD_MS    = 200;    // période de la lecture périodique des capteurs
constexpr uint32_t POLL_BACKOFF_MS   = 2000;   // période quand le robot ne répond plus (endormi, OI fermée)

// ---------- Opcodes OI utilisés ----------
enum : uint8_t {
  OI_START = 128, OI_SAFE = 131, OI_FULL = 132, OI_POWER = 133, OI_CLEAN = 135,
  OI_LEDS = 139, OI_SONG = 140, OI_PLAY = 141, OI_SENSORS = 142, OI_DOCK = 143,
  OI_DRIVE_DIRECT = 145, OI_QUERY_LIST = 149, OI_STREAM_PAUSE = 150, OI_STOP = 173
};

HardwareSerial& robot = Serial2;
WebServer   http(80);
WiFiServer  tcpServer(23);
WiFiClient  tcpClient;
Preferences prefs;

bool     driving = false;
uint32_t lastDriveMs = 0;
bool     keepAwake = false;
uint32_t lastKeepAwakeMs = 0;
bool     csvEnabled = false;
bool     tcpWasConnected = false;
bool     staWasConnected = false;
uint32_t lastPollMs = 0;
int16_t  driveSpeed = SPEED_MM_S;   // vitesse des touches 8/2/4/6, réglable depuis la page web (plafond SPEED_MM_S)
uint32_t lastStopMs = 0;
volatile bool driveForward = false;  // dernier ordre de roues = marche avant (lu par la tâche radar et par la sécurité du radar)
volatile uint8_t staReason = 0;     // dernière cause de déconnexion du réseau de la maison (événement Wi-Fi), 0 = aucune
volatile bool    staGotIp = false;

// Pages web et API HTTP : définies dans web.ino (second fichier du sketch), déclarées ici pour setupWifi()
void handleRoot();  void handleState();  void handleCmd();  void handleSpeed();  void handleLog();  void handleScan();
void handleWifiGet();  void handleWifiPost();  void handleWifiForget();
void handleUpdateGet();  void handleUpdateDone();  void handleUpdateUpload();  void handleRadar();  void handleEssai();
// Radar à ultrasons (HC-SR04 sur servo SG90) : défini dans radar.ino (troisième fichier du sketch), déclaré ici pour la boucle
void radarSetup();  void radarTick();  bool radarForwardBlocked();  void radarCycleMode();  void radarPrintStatus();
int  radarFrontMm();  void radarStateJson(String& j);
// Tour sur place (rotation du robot avec mesure des distances) : défini dans tour.ino (quatrième fichier du sketch)
void tourStart();  void tourTick();  bool tourActive();  void tourEnd(bool ok, const char* raison);  void handleTour();
// Position du robot (x, y, cap) : définie dans position.ino (deuxième fichier du sketch)
void poseUpdate();  void poseReset(bool annonce);  void posePrint();  void poseStateJson(String& j);  void handlePose();
float poseX();  float poseY();  float poseCap();

// ---------- Gyroscope et accéléromètre MPU-6050 (module GY-521, I2C) ----------
// Câblage : VCC -> 3V3, GND -> GND, SCL -> D22 (GPIO22), SDA -> D21 (GPIO21) ; AD0, XDA, XCL, INT libres.
// Le module peut être monté dans n'importe quel sens : l'axe qui voit la gravité au repos est pris comme axe vertical,
// et la vitesse de rotation autour de cet axe est intégrée en un cap (degrés, sens anti-horaire positif comme l'OI).
// La lecture tourne à 100 Hz dans une tâche sur le second cœur, indépendante des attentes de la liaison robot.
constexpr int     PIN_SDA = 21;
constexpr int     PIN_SCL = 22;
constexpr uint8_t MPU_ADDR = 0x68;   // AD0 à la masse ou en l'air (0x69 si AD0 relié à 3,3 V)

struct ImuState {
  bool     present = false;
  uint8_t  whoami = 0;
  int      vertAxis = -1;              // 0 = X, 1 = Y, 2 = Z : axe du module qui voit la gravité
  float    vertSign = 1.0f;            // +1 si cet axe pointe vers le haut
  float    bias[3] = { 0, 0, 0 };      // biais du gyroscope au repos, °/s
  volatile float yawDeg = 0;           // cap intégré depuis le démarrage de la carte, degrés ; jamais remis à zéro (la position en dépend)
  volatile float yawZero = 0;          // valeur de yawDeg à la dernière remise à zéro (touche z) : le cap affiché est yawDeg - yawZero
  volatile float rateDps = 0;          // vitesse de rotation autour de la verticale, °/s
  volatile float acc[3] = { 0, 0, 0 }; // g
  volatile float gyr[3] = { 0, 0, 0 }; // °/s, biais retiré
  volatile uint32_t samples = 0, errors = 0;
  volatile bool calibRequested = false, calibrating = false;
} imu;

bool mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool mpuRead(uint8_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, (int)n) != (int)n) return false;
  for (size_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

bool imuSample(float acc[3], float gyr[3]) {
  uint8_t b[14];
  if (!mpuRead(0x3B, b, 14)) return false;   // ACCEL_XOUT_H … GYRO_ZOUT_L
  for (int i = 0; i < 3; i++) acc[i] = (int16_t)((b[2 * i] << 8) | b[2 * i + 1]) / 16384.0f;   // ±2 g
  for (int i = 0; i < 3; i++) gyr[i] = (int16_t)((b[8 + 2 * i] << 8) | b[9 + 2 * i]) / 65.5f;  // ±500 °/s
  return true;
}

bool imuInit() {
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  uint8_t w = 0;
  if (!mpuRead(0x75, &w, 1)) return false;   // WHO_AM_I : 0x68 pour un MPU-6050
  imu.whoami = w;
  mpuWrite(0x6B, 0x01);   // PWR_MGMT_1 : sortie de veille, horloge sur le gyroscope X
  delay(50);
  mpuWrite(0x1A, 0x03);   // CONFIG : filtre passe-bas 44 Hz
  mpuWrite(0x1B, 0x08);   // GYRO_CONFIG : ±500 °/s
  mpuWrite(0x1C, 0x00);   // ACCEL_CONFIG : ±2 g
  mpuWrite(0x19, 0x09);   // SMPLRT_DIV : 1 kHz / 10 = 100 Hz
  imu.present = true;
  return true;
}

// Robot immobile : moyenne de 200 échantillons (1 s) pour le biais du gyroscope et l'axe vertical, remise du cap à zéro.
void imuCalibrate() {
  float sa[3] = { 0, 0, 0 }, sg[3] = { 0, 0, 0 };
  int n = 0;
  for (int i = 0; i < 200; i++) {
    float a[3], g[3];
    if (imuSample(a, g)) { for (int k = 0; k < 3; k++) { sa[k] += a[k]; sg[k] += g[k]; } n++; }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
  if (n < 50) return;
  for (int k = 0; k < 3; k++) { sa[k] /= n; imu.bias[k] = sg[k] / n; }
  int v = 0;
  for (int k = 1; k < 3; k++) if (fabsf(sa[k]) > fabsf(sa[v])) v = k;
  imu.vertAxis = v;
  imu.vertSign = (sa[v] >= 0) ? 1.0f : -1.0f;
  imu.yawZero = imu.yawDeg;   // cap affiché remis à zéro ; yawDeg lui-même continue, pour que la position ne saute pas
}

// Cap affiché (touche g, page, CSV) : degrés depuis la dernière remise à zéro, positif vers la gauche.
float imuCap() { return imu.yawDeg - imu.yawZero; }

void imuTask(void*) {
  uint32_t last = micros();
  imu.calibRequested = true;
  for (;;) {
    if (imu.calibRequested) {
      imu.calibrating = true;
      imuCalibrate();
      imu.calibrating = false;
      imu.calibRequested = false;
      last = micros();
    }
    float a[3], g[3];
    if (imuSample(a, g)) {
      uint32_t now = micros();
      float dt = (now - last) * 1e-6f;
      last = now;
      for (int k = 0; k < 3; k++) { imu.acc[k] = a[k]; imu.gyr[k] = g[k] - imu.bias[k]; }
      if (imu.vertAxis >= 0) {
        float r = imu.vertSign * imu.gyr[imu.vertAxis];
        imu.rateDps = r;
        if (fabsf(r) > 0.3f) imu.yawDeg += r * dt;   // zone morte de 0,3 °/s contre la dérive au repos
      }
      imu.samples = imu.samples + 1;
    } else {
      imu.errors = imu.errors + 1;
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// ---------- Sortie dupliquée : USB série + client TCP + journal pour la page web ----------
// Les dernières lignes affichées sont gardées en mémoire et servies par /api/log (console de la page web).
constexpr size_t LOG_LINES = 40;
constexpr size_t LOG_WIDTH = 120;
char     logBuf[LOG_LINES][LOG_WIDTH];
uint32_t logSeq = 0;   // numéro de la ligne en cours d'écriture ; les lignes 0 .. logSeq-1 sont terminées
size_t   logPos = 0;

void logAppend(uint8_t c) {
  if (c == '\r') return;
  char* line = logBuf[logSeq % LOG_LINES];
  if (c == '\n') { line[logPos] = 0; logSeq++; logPos = 0; logBuf[logSeq % LOG_LINES][0] = 0; return; }
  if (logPos >= LOG_WIDTH - 1) return;
  size_t need = (c >= 0xF0) ? 4 : (c >= 0xE0) ? 3 : (c >= 0xC0) ? 2 : 1;   // ne jamais couper un caractère UTF-8 en deux
  if (logPos + need > LOG_WIDTH - 1) { logPos = LOG_WIDTH - 1; return; }
  line[logPos++] = (char)c;
}

class TeeOut : public Print {
 public:
  size_t write(uint8_t c) override {
    Serial.write(c);
    if (tcpClient && tcpClient.connected()) tcpClient.write(c);
    logAppend(c);
    return 1;
  }
  size_t write(const uint8_t* b, size_t n) override {
    Serial.write(b, n);
    if (tcpClient && tcpClient.connected()) tcpClient.write(b, n);
    for (size_t i = 0; i < n; i++) logAppend(b[i]);
    return n;
  }
};
TeeOut out;

// ---------- Utilitaires série ----------
void writeI16(int16_t v) {
  uint16_t u = (uint16_t)v;
  robot.write((uint8_t)(u >> 8));      // octet de poids fort d'abord (big-endian, comme l'exige l'OI)
  robot.write((uint8_t)(u & 0xFF));
}

// ---------- Le robot vient-il de redémarrer ? ----------
// Un Roomba qui redémarre (batterie retirée puis remise, ou ordre Reset) envoie quelques lignes de texte sur sa prise.
// Vu le 2026-11-09 sur ce 694 : « rtc configured: LSI » à chaque réveil par la ligne BRC.
// Tous les octets reçus en dehors d'une réponse valable passent par sniffByte() : une suite d'au moins 12 caractères
// lisibles est comptée comme un démarrage (ou un réveil) du robot et signalée ; le texte est affiché quand il
// s'arrête (sniffTick). Les suites plus courtes sont ignorées : des octets binaires ressemblent parfois à des lettres.
constexpr uint8_t TEXT_RUN_MIN = 12;
uint32_t robotBoots = 0;          // démarrages ou réveils du robot vus depuis le démarrage de la carte
char     robotText[161];          // début du texte reçu
size_t   robotTextLen = 0;
char     runBuf[TEXT_RUN_MIN];    // caractères de la suite en cours, tant qu'elle est trop courte pour compter
uint8_t  textRun = 0;             // longueur de la suite en cours (plafonnée à TEXT_RUN_MIN)
bool     textActive = false;      // un texte est en cours de réception
bool     textAnnounce = false;    // démarrage vu, pas encore signalé sur la console
uint32_t textLastMs = 0;

void textAppend(char c) {
  if (c == '\r' || c == '\n') c = ' ';
  if (robotTextLen >= sizeof(robotText) - 1) return;
  if (c == ' ' && (robotTextLen == 0 || robotText[robotTextLen - 1] == ' ')) return;
  robotText[robotTextLen++] = c;
}

void sniffByte(uint8_t c) {
  bool texte = (c >= 0x20 && c < 0x7F) || c == '\r' || c == '\n';
  if (!texte) { textRun = 0; return; }                 // octet binaire : la suite en cours est abandonnée
  if (textRun < TEXT_RUN_MIN) {
    runBuf[textRun++] = (char)c;
    if (textRun < TEXT_RUN_MIN) return;                // suite encore trop courte pour compter
    if (!textActive) { textActive = true; textAnnounce = true; robotBoots++; robotTextLen = 0; }
    else textAppend(' ');
    for (uint8_t i = 0; i < TEXT_RUN_MIN; i++) textAppend(runBuf[i]);
  } else {
    textAppend((char)c);
  }
  textLastMs = millis();
}

// Appelée par la boucle principale : signale le démarrage du robot, puis affiche le texte reçu 2 s après son dernier caractère.
void sniffTick();

void flushInput() { while (robot.available()) sniffByte((uint8_t)robot.read()); }

// Au moins INTER_QUERY_MS entre deux échanges avec le robot (spécification OI : 15 ms ; mesuré sur ce 694 : sinon une
// requête sur deux reste sans réponse), sans attendre pour rien quand le dernier échange est ancien.
uint32_t lastExchangeMs = 0;      // dernière requête envoyée ou dernière réponse reçue
void waitInterQuery() {
  uint32_t since = millis() - lastExchangeMs;
  if (since < INTER_QUERY_MS) delay(INTER_QUERY_MS - since);
}

bool readExact(uint8_t* buf, size_t n) {
  uint32_t t0 = millis();
  size_t got = 0;
  while (got < n && millis() - t0 < ANSWER_TIMEOUT_MS) {
    if (robot.available()) buf[got++] = (uint8_t)robot.read();
  }
  lastExchangeMs = millis();
  if (got != n) for (size_t i = 0; i < got; i++) sniffByte(buf[i]);   // réponse incomplète : du texte du robot, peut-être
  return got == n;
}

void finishPendingRead();
bool pollFinish(bool ok, const uint8_t* buf);

// Interroge un seul paquet capteur (opcode 142). Renvoie false si le robot ne répond pas. Ne sert plus qu'à la
// question simple « quelle tension ? » (paquet 22) ; tout le reste se lit par le groupe 100.
bool readSensor(uint8_t packetId, uint8_t* buf, size_t len) {
  finishPendingRead();   // ne jamais mélanger une réponse encore attendue avec cette lecture
  waitInterQuery();
  flushInput();
  robot.write(OI_SENSORS);
  robot.write(packetId);
  lastExchangeMs = millis();
  return readExact(buf, len);
}

uint16_t u16(const uint8_t* b) { return ((uint16_t)b[0] << 8) | b[1]; }
int16_t  i16(const uint8_t* b) { return (int16_t)u16(b); }

void noAnswer() {
  out.println(F("Pas de réponse du robot. Est-il réveillé et l'OI ouverte ? Essayez 'w' puis 's' ; sinon appuyez sur CLEAN, ou 'y' (essai à 19200 bauds)."));
}

// Touche 'y' : le robot est-il passé à 19200 bauds ? Un Roomba 600 quitte ses 115200 bauds si l'on garde CLEAN appuyé
// une dizaine de secondes en l'éteignant (il joue alors une suite de notes descendantes), ou s'il reçoit trois impulsions
// basses sur BRC après son allumage (les redémarrages de la carte n'y sont pour rien : essai du 2026-11-09,
// journal_wifi.md § 17). Il garde ensuite 19200 bauds jusqu'au retrait de sa batterie, jusqu'à l'ordre Baud
// (opcode 129) ou, vraisemblablement, jusqu'à un Reset. Symptômes vus le 2026-11-09 :
// robot allumé, fils reliés, aucun ordre exécuté, et des octets reçus de la forme 00 / E0 (un bit à 19200 bauds dure
// exactement six bits à 115200). Cette fonction parle au robot à 19200 bauds ; s'il répond, elle lui ordonne de
// revenir à 115200 bauds (code 11), puis vérifie la liaison. Elle est appelée par la touche 'y', et d'elle-même dans
// deux cas (depuis le 2026-11-09, à la demande de l'utilisateur) : un Start ('s') resté sans réponse, et des octets
// qui arrivent sans avoir de sens trois lectures de suite. Jamais pendant que les roues tournent.
uint32_t baudRescues = 0;            // nombre de fois où le robot a été retrouvé à 19200 bauds depuis le démarrage de la carte
uint32_t lastBaudRescueMs = 0;       // date du dernier essai (réussi ou non)
bool     baudRescuePending = false;  // essai demandé par la lecture périodique, fait par la boucle principale
bool     tourActive();

bool baudRescue(bool automatique) {
  if (driving || tourActive()) {
    if (!automatique) out.println(F("Essai à 19200 bauds refusé : les roues tournent. Arrêtez-les d'abord (5)."));
    return false;
  }
  finishPendingRead();
  lastBaudRescueMs = millis();
  out.println(automatique ? F("Robot muet ou incompréhensible : essai automatique de la liaison à 19200 bauds...")
                          : F("Essai de la liaison à 19200 bauds (Start, puis lecture de la tension)..."));
  robot.flush();
  robot.updateBaudRate(19200);
  delay(60);
  flushInput();
  robot.write(OI_START);
  delay(120);
  uint8_t b[2];
  bool lent = readSensor(22, b, 2);
  uint16_t mv = lent ? u16(b) : 0;
  if (lent && mv >= 8000 && mv <= 22000) {
    out.printf("Le robot répond à 19200 bauds : batterie %u mV. Ordre de revenir à 115200 bauds (opcode 129, code 11).\n", mv);
    delay(INTER_QUERY_MS);
    robot.write((uint8_t)129);
    robot.write((uint8_t)11);
    robot.flush();
    delay(350);                      // la spécification demande 100 ms avant de parler au nouveau débit ; marge prise le 2026-11-09
  } else if (lent) {
    out.printf("Deux octets reçus à 19200 bauds, mais sans signification (%02X %02X) : pas de changement.\n", b[0], b[1]);
    lent = false;
  } else {
    out.println(F("Pas de réponse à 19200 bauds non plus : le robot dort, ou un fil manque."));
  }
  robot.updateBaudRate(115200);
  delay(60);
  flushInput();
  if (!lent) return false;
  baudRescues++;
  for (int essai = 0; essai < 3; essai++) {   // le premier essai juste après le changement de débit peut rester sans réponse
    robot.write(OI_START);
    delay(150);
    if (readSensor(22, b, 2)) {
      out.printf("Liaison rétablie à 115200 bauds : batterie %u mV (retour numéro %lu depuis le démarrage de la carte).\n",
                 u16(b), (unsigned long)baudRescues);
      return true;
    }
    delay(250);
  }
  out.println(F("Ordre envoyé, mais pas encore de réponse à 115200 bauds : la lecture périodique dira si la liaison est revenue ; sinon 'y'."));
  return false;
}

// ---------- État du robot, rafraîchi par la lecture périodique ----------
struct RobotState {
  bool     ok = false;        // dernière lecture complète réussie et plausible
  uint32_t lastOkMs = 0;
  uint32_t failures = 0;
  uint16_t voltage = 0;       // mV
  int16_t  current = 0;       // mA, négatif = décharge
  int8_t   temp = 0;          // °C
  uint16_t charge = 0, capacity = 0;   // mAh
  uint8_t  charging = 0, mode = 0;
  uint8_t  bumpsDrops = 0, buttons = 0, lightBits = 0;
  uint16_t cliff[4] = {0, 0, 0, 0};
  uint16_t light[6] = {0, 0, 0, 0, 0, 0};
  int16_t  encL = 0, encR = 0;
  // lus depuis la version 4 (groupe 100)
  uint8_t  wall = 0, virtualWall = 0, overcur = 0, dirt = 0, irOmni = 0, irLeft = 0, irRight = 0, chargeSrc = 0, stasis = 0;
  uint16_t wallSignal = 0;
  int16_t  curL = 0, curR = 0, curBrush = 0, curSide = 0;   // courants des moteurs, mA
} st;

// ---------- Lecture des capteurs : un seul groupe de paquets ----------
// Jusqu'au 2026-11-09, la lecture périodique demandait une liste de 22 paquets (opcode 149), ou, le plus souvent, les
// mêmes paquets un par un (22 requêtes « 142, numéro » par cycle de 0,6 s). Désormais une seule requête : 142 puis
// 100, le groupe des paquets 7 à 58 (80 octets, réponse complète en 13 ms sur ce 694). Si le robot n'y répond pas
// alors qu'il répond à une question simple, repli sur deux groupes : 6 (paquets 7 à 42, 52 octets) puis 101
// (paquets 43 à 58, 28 octets), soit les mêmes 80 octets dans le même ordre.
// Moins d'octets envoyés au robot, c'est aussi moins d'occasions qu'il en comprenne un de travers.
// Piste écartée le 2026-11-09 : l'ancienne lecture envoyait souvent l'octet 7, qui est l'ordre Reset d'après la
// documentation du Create 2. Essais faits (journal_wifi.md § 18) : sur ce 694, un 7 ne provoque rien, ni liaison
// ouverte (Passive), ni liaison fermée par Stop.
// Défaut corrigé au passage : l'ancienne lecture notait l'heure d'envoi « | 1 » pour qu'elle ne vaille jamais
// zéro ; cette heure pouvait donc être en avance d'une milliseconde, et un passage de la boucle dans la même
// milliseconde calculait une attente de 4 milliards de ms : faux « délai dépassé », zéro octet reçu, puis abandon
// définitif de la lecture groupée au profit de la lecture paquet par paquet. Le journal de la carte du 2026-11-09
// (20 h 57) montre ce message « 0 octet(s) sur 38 » moins de 40 s après un démarrage. Cause probable de l'échec
// « non élucidé » du journal_wifi.md § 7 et § 9. Un drapeau séparé (allPending) remplace cette astuce.
constexpr size_t   ALL_LEN        = 80;    // paquets 7 à 58
constexpr size_t   ALL_SPLIT      = 52;    // paquets 7 à 42 (groupe 6)
constexpr uint32_t ALL_TIMEOUT_MS = 300;   // attente maximale d'un groupe
uint8_t  allBuf[ALL_LEN];
size_t   allGot = 0, allWant = 0;
bool     allPending = false;       // une réponse est attendue
uint32_t allSentMs = 0;            // heure d'envoi du groupe en cours
uint32_t allStartMs = 0;           // heure d'envoi de la première requête de la lecture en cours
uint8_t  allGroupe = 100;          // groupe demandé en dernier : 100, 6 ou 101
bool     useSplitGroups = false;   // vrai si le robot ne répond pas au groupe 100
uint8_t  fails100 = 0;             // délais dépassés de suite sur le groupe 100 alors que le robot répond à une question simple
uint32_t allFirstAnswerMs = 0;     // durée de la première réponse complète (affichée une fois)
float    pollYaw = 0;              // cap du gyroscope (yawDeg) relevé à l'envoi de la requête qui lit les compteurs des roues

void pollSend(uint8_t groupe) {    // 100, 6, ou 101 (suite du 6)
  waitInterQuery();
  if (groupe != 101) { flushInput(); allGot = 0; }
  allWant = (groupe == 6) ? ALL_SPLIT : ALL_LEN;
  allGroupe = groupe;
  pollYaw = imu.yawDeg;
  robot.write(OI_SENSORS);
  robot.write(groupe);
  allSentMs = millis();
  lastExchangeMs = allSentMs;
  if (groupe != 101) allStartMs = allSentMs;
  allPending = true;
}

// Ramasse les octets de la réponse : 1 si complète, -1 si délai dépassé, 0 si encore en attente.
int pollCollect() {
  while (robot.available() && allGot < allWant) allBuf[allGot++] = (uint8_t)robot.read();
  if (allGot >= allWant) {
    if (allGroupe == 6) { lastExchangeMs = millis(); pollSend(101); return 0; }   // première partie reçue : on demande la seconde
    return 1;
  }
  if (millis() - allSentMs >= ALL_TIMEOUT_MS) return -1;
  return 0;
}

// Clôt la lecture en cours. r : 1 réponse complète, -1 délai dépassé. Renvoie vrai si la lecture est bonne.
bool pollEnd(int r) {
  allPending = false;
  lastExchangeMs = millis();
  if (r != 1) for (size_t i = 0; i < allGot; i++) sniffByte(allBuf[i]);   // octets inattendus : du texte du robot, peut-être
  return pollFinish(r == 1, allBuf);
}

// Si une réponse est attendue, l'attend (au plus ALL_TIMEOUT_MS par groupe) et la traite : appelée avant toute
// autre requête, pour ne jamais mélanger deux réponses.
void finishPendingRead() {
  if (!allPending) return;
  int r;
  while ((r = pollCollect()) == 0) delay(1);
  pollEnd(r);
}

// Lecture immédiate et complète (touches b, e, k) : vrai si le robot a répondu et que la réponse est plausible.
bool readAll() {
  finishPendingRead();
  pollSend(useSplitGroups ? 6 : 100);
  int r;
  while ((r = pollCollect()) == 0) delay(1);
  return pollEnd(r);
}

// Touche q : essai des groupes 100, puis 6 et 101, avec les premiers octets reçus et le temps de réponse.
void testGroups() {
  finishPendingRead();
  const uint8_t groupes[3] = { 100, 6, 101 };
  const size_t  tailles[3] = { 80, 52, 28 };
  bool complet[3] = { false, false, false };
  for (int g = 0; g < 3; g++) {
    waitInterQuery();
    flushInput();
    robot.write(OI_SENSORS);
    robot.write(groupes[g]);
    uint8_t buf[ALL_LEN];
    size_t got = 0;
    uint32_t t0 = millis(), tDone = t0;
    while (millis() - t0 < 800 && got < tailles[g]) {
      if (robot.available()) { buf[got++] = (uint8_t)robot.read(); tDone = millis(); }
    }
    lastExchangeMs = millis();
    complet[g] = (got == tailles[g]);
    out.printf("Groupe %u : %u octet(s) reçu(s) sur %u en %lu ms", (unsigned)groupes[g], (unsigned)got, (unsigned)tailles[g],
               (unsigned long)((got ? tDone : millis()) - t0));
    if (got) { out.print(F(" :")); for (size_t i = 0; i < got && i < 24; i++) out.printf(" %02X", buf[i]); if (got > 24) out.print(F(" …")); }
    out.println();
    if (!complet[g]) for (size_t i = 0; i < got; i++) sniffByte(buf[i]);
    if (g == 0 && complet[0]) break;
  }
  if (complet[0]) { useSplitGroups = false; fails100 = 0; out.println(F("Lecture des capteurs par le groupe 100 (80 octets en une requête).")); }
  else if (complet[1] && complet[2]) { useSplitGroups = true; out.println(F("Le groupe 100 ne répond pas en entier : lecture par les groupes 6 puis 101.")); }
  else out.println(F("Aucun groupe ne répond en entier : liaison fermée ou robot endormi (CLEAN sur le robot, puis s)."));
}

// Touche v : écoute la ligne du robot sans rien envoyer et affiche ce qui arrive (octets et texte).
// Un robot qui redémarre envoie quelques lignes de texte ; un robot qui parle à 19200 bauds donne des 00, E0, F8.
void listenRobot(uint32_t dureeMs) {
  if (driving || tourActive()) { out.println(F("Écoute refusée : les roues tournent. Arrêtez-les d'abord (5).")); return; }
  finishPendingRead();
  static uint8_t buf[400];
  size_t got = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < dureeMs) {
    if (robot.available()) { uint8_t c = (uint8_t)robot.read(); sniffByte(c); if (got < sizeof(buf)) buf[got++] = c; }
    else delay(1);
  }
  lastExchangeMs = millis();
  out.printf("Écoute du robot pendant %.1f s : %u octet(s) reçu(s)%s\n", dureeMs / 1000.0f, (unsigned)got, got ? " :" : ".");
  for (size_t i = 0; i < got && i < 64; i += 32) {       // les 64 premiers octets, en hexadécimal
    out.print(F("  "));
    for (size_t k = i; k < got && k < i + 32; k++) out.printf("%02X ", buf[k]);
    out.println();
  }
  for (size_t i = 0; i < got; ) {                        // puis tout ce qui est lisible, ligne par ligne
    char ligne[100];
    size_t n = 0;
    while (i < got && n < sizeof(ligne) - 1) {
      uint8_t c = buf[i++];
      if (c == '\n') break;
      if (c == '\r') continue;
      ligne[n++] = (c >= 0x20 && c < 0x7F) ? (char)c : '.';
    }
    ligne[n] = 0;
    if (n) out.printf("  | %s\n", ligne);
  }
}

// b : les 80 octets des paquets 7 à 58, dans l'ordre de la spécification OI (numéro de chaque paquet en commentaire)
void parseState(const uint8_t* b) {
  st.bumpsDrops  = b[0];                                             // 7  pare-chocs et roues levées
  st.wall        = b[1];                                             // 8  mur (capteur de droite)
  st.virtualWall = b[6];                                             // 13 mur virtuel
  st.overcur     = b[7];                                             // 14 surintensités des moteurs
  st.dirt        = b[8];                                             // 15 capteur de saleté
  st.irOmni      = b[10];                                            // 17 infrarouge reçu, capteur du dessus
  st.buttons     = b[11];                                            // 18 boutons
  st.charging    = b[16];                                            // 21 état de charge
  st.voltage     = u16(b + 17);                                      // 22 tension
  st.current     = i16(b + 19);                                      // 23 courant
  st.temp        = (int8_t)b[21];                                    // 24 température
  st.charge      = u16(b + 22);                                      // 25 charge
  st.capacity    = u16(b + 24);                                      // 26 capacité
  st.wallSignal  = u16(b + 26);                                      // 27 signal du capteur de mur
  for (int i = 0; i < 4; i++) st.cliff[i] = u16(b + 28 + 2 * i);     // 28 à 31 signaux des capteurs de vide
  st.chargeSrc   = b[39];                                            // 34 sources de charge présentes (bit 1 : base)
  st.mode        = b[40];                                            // 35 mode OI
  st.encL        = i16(b + 52);                                      // 43 compteur de la roue gauche
  st.encR        = i16(b + 54);                                      // 44 compteur de la roue droite
  st.lightBits   = b[56];                                            // 45 capteurs optiques du pare-chocs, en bits
  for (int i = 0; i < 6; i++) st.light[i] = u16(b + 57 + 2 * i);     // 46 à 51 leurs six signaux
  st.irLeft      = b[69];                                            // 52 infrarouge reçu à gauche
  st.irRight     = b[70];                                            // 53 infrarouge reçu à droite
  st.curL        = i16(b + 71);                                      // 54 courant du moteur de la roue gauche
  st.curR        = i16(b + 73);                                      // 55 courant du moteur de la roue droite
  st.curBrush    = i16(b + 75);                                      // 56 courant de la brosse principale
  st.curSide     = i16(b + 77);                                      // 57 courant de la brosse latérale
  st.stasis      = b[79];                                            // 58 roulette avant : le robot avance-t-il ?
}

void printCsvHeader() {
  out.println(F("csv,ms,enc_g,enc_d,pc_g,pc_d,roue_g,roue_d,vide_g,vide_avg,vide_avd,vide_d,lb_g,lb_avg,lb_cg,lb_cd,lb_avd,lb_d,mv,ma,mode,cap_deg,rot_dps,us_mm,x_mm,y_mm,cap_pos"));
}

void printCsvLine() {
  out.printf("csv,%lu,%d,%d,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%d,%u,%.1f,%.1f,%d,%.0f,%.0f,%.1f\n",
             (unsigned long)millis(), st.encL, st.encR,
             (st.bumpsDrops >> 1) & 1, st.bumpsDrops & 1, (st.bumpsDrops >> 3) & 1, (st.bumpsDrops >> 2) & 1,
             st.cliff[0], st.cliff[1], st.cliff[2], st.cliff[3],
             st.light[0], st.light[1], st.light[2], st.light[3], st.light[4], st.light[5],
             st.voltage, st.current, st.mode, imuCap(), imu.rateDps, radarFrontMm(),      // us_mm : -1 inconnu, 0 rien à portée
             poseX(), poseY(), poseCap());                                                 // position calculée (position.ino)
}

void printImu() {
  if (!imu.present) { out.println(F("Gyroscope : MPU-6050 non détecté (vérifier VCC->3V3, GND, SCL->D22, SDA->D21).")); return; }
  const char axes[3] = { 'X', 'Y', 'Z' };
  out.printf("Gyroscope MPU-6050 : WHO_AM_I 0x%02X, %lu lectures, %lu erreurs%s\n", imu.whoami, (unsigned long)imu.samples, (unsigned long)imu.errors,
             imu.calibrating ? ", calibration en cours" : "");
  out.printf("Accéléromètre (g) : X %.2f  Y %.2f  Z %.2f   | gyroscope (°/s) : X %.1f  Y %.1f  Z %.1f\n",
             imu.acc[0], imu.acc[1], imu.acc[2], imu.gyr[0], imu.gyr[1], imu.gyr[2]);
  if (imu.vertAxis >= 0) out.printf("Axe vertical : %c (vers le %s). Cap intégré : %.1f°   vitesse de rotation : %.1f °/s   (z pour remettre à zéro, robot immobile)\n",
                                    axes[imu.vertAxis], imu.vertSign > 0 ? "haut" : "bas", imuCap(), imu.rateDps);
  else out.println(F("Axe vertical pas encore déterminé : envoyer z, robot immobile."));
}

// Met en pause un éventuel flux continu de capteurs (opcode 148 « Stream ») et vide le tampon. Vu le 2026-11-08 :
// le robot s'est mis à diffuser notre liste de paquets toutes les 15 ms (en-tête 0x13, 60 octets), et toutes les
// lectures suivantes renvoyaient ces octets décalés (tension « 4924 mV », mode « 19 »...).
void pauseStream() {
  finishPendingRead();
  waitInterQuery();
  robot.write(OI_STREAM_PAUSE);
  robot.write((uint8_t)0);
  delay(40);
  flushInput();
  lastExchangeMs = millis();
  out.println(F("Flux continu de capteurs (opcode 148) mis en pause (150, 0), tampon vidé."));
}

// Fin d'une lecture : contrôle de plausibilité, mise à jour de l'état et de la position, ligne CSV éventuelle.
// Renvoie vrai si la lecture est complète et plausible.
bool pollFinish(bool ok, const uint8_t* buf) {
  static uint8_t implausible = 0;
  if (ok) {                                     // rejette les lectures polluées par des octets parasites (réveil par BRC, flux 148...)
    uint16_t v = u16(buf + 17);                 // tension
    int8_t   t = (int8_t)buf[21];               // température
    if (v < 8000 || v > 22000 || buf[16] > 5 || t < -20 || t > 80 || buf[40] > 4) {   // buf[16] état de charge, buf[40] mode OI
      ok = false;
      for (size_t i = 0; i < ALL_LEN; i++) sniffByte(buf[i]);   // 80 octets qui ne sont pas des capteurs : du texte du robot ?
      if (++implausible >= 3) {      // des octets arrivent mais n'ont pas de sens : flux 148, ou robot passé à 19200 bauds
        implausible = 0;
        pauseStream();
        // Essai à 19200 bauds (fait par la boucle principale) seulement si aucune bonne lecture n'est passée depuis 5 s :
        // un robot qui répond juste entre deux lectures brouillées n'a pas changé de débit (vu le 2026-11-09 après un
        // réveil par BRC : il envoie alors des octets à lui, B0 02 01 15 34, qui brouillent une lecture sur trois).
        if (millis() - lastBaudRescueMs > 30000 && millis() - st.lastOkMs > 5000) baudRescuePending = true;
      }
    } else {
      implausible = 0;
    }
  }
  if (ok) {
    parseState(buf);
    st.ok = true;
    st.lastOkMs = millis();
    st.failures = 0;
    poseUpdate();                               // position du robot (position.ino)
    if (csvEnabled) printCsvLine();
  } else {
    st.failures++;
    if (st.failures >= 3) st.ok = false;
  }
  return ok;
}

// Appelée en boucle : demande les capteurs à la cadence voulue et ramasse la réponse sans bloquer.
void pollTick() {
  if (allPending) {                // réponse attendue : on ramasse ce qui est arrivé
    int r = pollCollect();
    if (r == 0) return;
    if (r == 1) {
      uint32_t took = millis() - allStartMs;
      fails100 = 0;
      bool bonne = pollEnd(1);
      if (bonne && !allFirstAnswerMs) {
        allFirstAnswerMs = took ? took : 1;
        out.printf("Lecture des capteurs (%s, 80 octets) : première réponse complète en %lu ms.\n",
                   useSplitGroups ? "groupes 6 puis 101" : "groupe 100", (unsigned long)took);
      }
      return;
    }
    size_t got = allGot;
    pollEnd(-1);
    // Délai dépassé. Si le robot répond à une question simple, c'est le groupe 100 qu'il n'aime pas : après trois
    // fois de suite, repli sur les groupes 6 et 101. La question n'est posée qu'au début d'un silence, puis une fois
    // sur dix (elle bloque la boucle 200 ms quand le robot dort).
    if (!useSplitGroups && (st.failures <= 3 || st.failures % 10 == 0)) {
      uint8_t b[2];
      if (readSensor(22, b, 2)) {
        if (++fails100 >= 3) {
          useSplitGroups = true;
          out.printf("Groupe 100 : %u octet(s) sur 80 en %lu ms, trois fois de suite ; lecture par les groupes 6 puis 101 désormais (q pour réessayer).\n",
                     (unsigned)got, (unsigned long)ALL_TIMEOUT_MS);
        }
      } else {
        fails100 = 0;
      }
    }
    return;
  }
  uint32_t now = millis();
  uint32_t period = (st.failures >= 3) ? POLL_BACKOFF_MS : POLL_PERIOD_MS;
  if (now - lastPollMs < period) return;
  lastPollMs = now;
  pollSend(useSplitGroups ? 6 : 100);
}

// Appelée par la boucle principale : signale un démarrage du robot vu par sniffByte(), puis affiche le début du
// texte reçu 2 s après son dernier caractère.
void sniffTick() {
  if (textAnnounce) {
    textAnnounce = false;
    out.printf("Le robot envoie du texte : il vient de démarrer ou de se réveiller (fois numéro %lu). Pour reprendre la main : s, puis f.\n",
               (unsigned long)robotBoots);
  }
  if (textActive && millis() - textLastMs > 2000) {
    robotText[robotTextLen] = 0;
    for (size_t i = 0; i < robotTextLen; i += 90) out.printf("  texte du robot : %.90s\n", robotText + i);
    textActive = false;
    robotTextLen = 0;
  }
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
  out.print(F("Envoyé : "));
  out.println(name);
}

void driveDirect(int16_t right, int16_t left) {
  right = constrain(right, -SPEED_MM_S, SPEED_MM_S);   // plafond de sécurité
  left  = constrain(left,  -SPEED_MM_S, SPEED_MM_S);
  robot.write(OI_DRIVE_DIRECT);
  writeI16(right);   // roue droite d'abord, puis roue gauche (ordre imposé par l'OI)
  writeI16(left);
  driving = (right != 0 || left != 0);
  driveForward = (right > 0 && left > 0);
  lastDriveMs = millis();
}

// Les ordres de roues des touches 8, 2, 4, 6 ne partent que si le robot est en mode Safe et vient de répondre.
// En Passive le robot n'obéit pas aux roues, et deux fois (2026-11-08 et 2026-11-09, 20 h 57) il a cessé de répondre
// juste après des flèches envoyées dans ce mode ; la cause exacte n'est pas établie (journal_wifi.md § 18).
// L'ordre d'arrêt (vitesses nulles), lui, part toujours : essayé en Passive le 2026-11-09, sans effet sur le robot.
constexpr uint8_t OI_MODE_SAFE_LU = 3;   // valeur du paquet 35 lue sur ce 694 en mode Safe (décalée de +1, voir journal_tests.md)
bool wheelsAllowed() {
  if (st.ok && st.mode == OI_MODE_SAFE_LU && millis() - st.lastOkMs < 1500) return true;
  static uint32_t lastMsgMs = 0;
  if (millis() - lastMsgMs > 2000) {      // la page répète l'ordre toutes les 400 ms : un message toutes les 2 s suffit
    lastMsgMs = millis();
    out.println(st.ok ? F("Ordre de roues refusé : le robot n'est pas en mode Safe (touche f, ou bouton Safe de la page).")
                      : F("Ordre de roues refusé : le robot ne répond pas (CLEAN sur le robot, puis s, puis f)."));
  }
  return false;
}

// Arrêt des roues : touche stop, garde-fou de 1,5 s, déconnexion d'un client ou mise à jour.
// L'ordre et le message ne sont répétés que si les roues tournaient, ou au plus une fois par seconde,
// pour ne jamais inonder la console ni la liaison robot si des touches stop arrivent en rafale.
void stopWheels() {
  uint32_t now = millis();
  if (driving || now - lastStopMs > 1000) {
    driveDirect(0, 0);
    out.println(F("Roues arrêtées."));
    lastStopMs = now;
  }
}

void playJingle() {
  const uint8_t song[] = { OI_SONG, 0, 3, 72, 16, 76, 16, 79, 24 };
  robot.write(song, sizeof(song));
  delay(20);
  robot.write(OI_PLAY);
  robot.write((uint8_t)0);
  out.println(F("Chanson envoyée (mode Safe requis : 'f' d'abord)."));
}

void ledDemo() {
  const uint8_t cmd[] = { OI_LEDS, 4, 0, 255 };
  robot.write(cmd, sizeof(cmd));
  out.println(F("LEDs envoyées (mode Safe requis)."));
}

// Touches b, e, k : une lecture complète et fraîche (readAll), puis affichage. Plus aucune lecture paquet par paquet.
void printBattery() {
  if (!readAll()) { noAnswer(); return; }
  out.printf("Tension batterie : %u mV\n", st.voltage);
  out.printf("Courant : %d mA   (négatif = décharge)\n", st.current);
  out.printf("Température : %d °C\n", (int)st.temp);
  out.printf("Charge : %u / %u mAh\n", st.charge, st.capacity);
  out.printf("État de charge : %u   (0 pas en charge, 1 reconditionnement, 2 charge à pleine puissance, 3 entretien, 4 attente, 5 défaut)\n", st.charging);
  out.printf("Mode OI lu : %u   (0 Off, 1 Passive, 2 Safe, 3 Full ; sur ce 694 la valeur est décalée de +1)\n", st.mode);
}

void printSensors() {
  if (!readAll()) { noAnswer(); return; }
  out.printf("Pare-chocs : droit %u, gauche %u | Roue levée : droite %u, gauche %u\n",
             st.bumpsDrops & 1, (st.bumpsDrops >> 1) & 1, (st.bumpsDrops >> 2) & 1, (st.bumpsDrops >> 3) & 1);
  out.printf("Vide (signaux) : gauche %u, avant gauche %u, avant droit %u, droit %u\n", st.cliff[0], st.cliff[1], st.cliff[2], st.cliff[3]);
  out.print(F("Capteurs optiques du pare-chocs (G, AvG, CG, CD, AvD, D) :"));
  for (int i = 0; i < 6; i++) out.printf(" %u", st.light[i]);
  out.println();
  out.printf("Boutons : CLEAN %u, SPOT %u, DOCK %u | mur %u (signal %u), mur virtuel %u\n",
             st.buttons & 1, (st.buttons >> 1) & 1, (st.buttons >> 2) & 1, st.wall, st.wallSignal, st.virtualWall);
  out.printf("Infrarouge reçu : dessus %u, gauche %u, droite %u | saleté %u | roulette avant %u | sur la base : %s\n",
             st.irOmni, st.irLeft, st.irRight, st.dirt, st.stasis, (st.chargeSrc & 2) ? "oui" : "non");
  out.printf("Moteurs (mA) : roue gauche %d, roue droite %d, brosse %d, brosse latérale %d | surintensités (bits) %u\n",
             st.curL, st.curR, st.curBrush, st.curSide, st.overcur);
}

// Compteurs des roues (paquets 43 et 44, signés) et position calculée. Le paquet 19 (distance) est faux sur ce robot.
void printEncoders() {
  if (!readAll()) { noAnswer(); return; }
  out.printf("Compteurs des roues : gauche %d, droit %d   (508,8 pas par tour, roue de 72 mm : 1 pas = 0,445 mm)\n", st.encL, st.encR);
  posePrint();
}

// ---------- Test de continuité des trois fils (repris de roomba694_diag) ----------
int countHigh(int pin) {
  int highs = 0;
  for (int i = 0; i < 400; i++) { if (digitalRead(pin)) highs++; delayMicroseconds(50); }
  return highs;   // sur 400 échantillons, soit 20 ms
}

void describe(int up, int down, int none) {
  if (up == 400 && down == 400)                    out.println(F("  -> tenu HAUT par le robot : fil relié."));
  else if (up == 0 && down == 0)                   out.println(F("  -> tenu à 0 V : fil sur une masse (trou 6 ou 7), ou sur le TXD d'un robot endormi."));
  else if (up == 400 && down == 0 && none >= 390)  out.println(F("  -> relié à travers un rappel FAIBLE : fil probablement relié."));
  else if (up == 400 && down == 0 && none <= 10)   out.println(F("  -> en l'air : RIEN de relié (pion qui ne touche pas, fil absent, ou masse absente)."));
  else                                             out.println(F("  -> instable : le robot parle, ou faux contact."));
}

void printLevels() {
  gpio_set_pull_mode((gpio_num_t)PIN_RX, GPIO_PULLUP_ONLY);   delay(2); int rxUp   = countHigh(PIN_RX);
  gpio_set_pull_mode((gpio_num_t)PIN_RX, GPIO_PULLDOWN_ONLY); delay(2); int rxDown = countHigh(PIN_RX);
  gpio_set_pull_mode((gpio_num_t)PIN_RX, GPIO_FLOATING);      delay(2); int rxNone = countHigh(PIN_RX);
  gpio_set_pull_mode((gpio_num_t)PIN_RX, GPIO_PULLUP_ONLY);
  out.printf("RX2 (GPIO%d, fil du trou 4) : haut %d/400 rappel haut, %d/400 rappel bas, %d/400 sans rappel\n", PIN_RX, rxUp, rxDown, rxNone);
  describe(rxUp, rxDown, rxNone);

  robot.end();
  pinMode(PIN_TX, INPUT_PULLUP);   delay(2); int txUp   = countHigh(PIN_TX);
  pinMode(PIN_TX, INPUT_PULLDOWN); delay(2); int txDown = countHigh(PIN_TX);
  pinMode(PIN_TX, INPUT);          delay(2); int txNone = countHigh(PIN_TX);
  robot.begin(115200, SERIAL_8N1, PIN_RX, PIN_TX);
  out.printf("TX2 (GPIO%d, fil du trou 3) : haut %d/400 rappel haut, %d/400 rappel bas, %d/400 sans rappel\n", PIN_TX, txUp, txDown, txNone);
  describe(txUp, txDown, txNone);

  pinMode(PIN_BRC, INPUT_PULLUP);   delay(2); int brcUp   = countHigh(PIN_BRC);
  pinMode(PIN_BRC, INPUT_PULLDOWN); delay(2); int brcDown = countHigh(PIN_BRC);
  pinMode(PIN_BRC, INPUT);          delay(2); int brcNone = countHigh(PIN_BRC);
  digitalWrite(PIN_BRC, HIGH); pinMode(PIN_BRC, OUTPUT);   // retour à l'état normal : sortie haute
  out.printf("D4  (GPIO%d, fil du trou 5) : haut %d/400 rappel haut, %d/400 rappel bas, %d/400 sans rappel\n", PIN_BRC, brcUp, brcDown, brcNone);
  describe(brcUp, brcDown, brcNone);
}

// ---------- Informations ----------
void printInfo() {
  out.printf("Point d'accès « %s » : adresse %s, %d appareil(s) connecté(s)\n", AP_SSID, WiFi.softAPIP().toString().c_str(), WiFi.softAPgetStationNum());
  if (WiFi.status() == WL_CONNECTED) out.printf("Réseau de la maison « %s » : connecté, adresse %s (http://%s.local)\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(), HOSTNAME);
  else {
    prefs.begin("wifi", true);
    String ssid = prefs.getString("ssid", "");
    prefs.end();
    if (ssid.length()) out.printf("Réseau de la maison « %s » : enregistré, pas connecté pour l'instant\n", ssid.c_str());
    else out.println(F("Réseau de la maison : aucun enregistré (page /wifi)"));
  }
  out.printf("Console TCP (port 23) : %s | Robot : %s (dernier contact il y a %lu ms, %s) | Roues : %s, vitesse %d mm/s | Anti-veille : %s | CSV : %s\n",
             (tcpClient && tcpClient.connected()) ? "client connecté" : "libre",
             st.ok ? "joignable" : "sans réponse", (unsigned long)(millis() - st.lastOkMs),
             useSplitGroups ? "lecture par les groupes 6 et 101" : "lecture par le groupe 100",
             driving ? "en mouvement" : "arrêtées", driveSpeed, keepAwake ? "actif" : "inactif", csvEnabled ? "actif" : "inactif");
  out.printf("Firmware roomba694_wifi v4, compilé le %s %s, en marche depuis %lu s, dernier redémarrage : %s\n",
             __DATE__, __TIME__, (unsigned long)(millis() / 1000), resetReasonText());
  out.printf("Depuis le démarrage de la carte : robot vu redémarrer %lu fois ; retrouvé à 19200 bauds et ramené à 115200 : %lu fois.\n",
             (unsigned long)robotBoots, (unsigned long)baudRescues);
  posePrint();
}

void printHelp() {
  out.println(F(
    "\n=== Roomba 694 — console Wi-Fi v4 ===\n"
    " ?  aide                         w  impulsion BRC (réveil)\n"
    " s  Start -> Passive             f  Safe (contrôle, sécurités actives)\n"
    " c  Clean                        h  retour à la base\n"
    " b  batterie / mode OI           e  pare-chocs, vide, boutons, moteurs\n"
    " k  compteurs des roues et position   0  position remise à zéro (le robot devient le point de départ)\n"
    " n  test de continuité des trois fils\n"
    " m  jouer 3 notes (Safe)         l  LEDs (Safe)\n"
    " 8  avance   2  recule   4  tourne à gauche   6  tourne à droite   5 ou espace  stop\n"
    "    (mode Safe requis ; chaque ordre dure 1,5 s puis les roues s'arrêtent seules ; 150 mm/s au plus)\n"
    " a  anti-veille BRC toutes les 45 s (on/off)\n"
    " j  journal CSV toutes les 200 ms (on/off)   i  informations Wi-Fi et état\n"
    " g  gyroscope MPU-6050 (cap, vitesse)   z  recalibrer le gyroscope et remettre le cap à zéro (robot immobile)\n"
    " r  radar à ultrasons : arrêt -> fixe devant -> balayage (on tourne)   u  état du radar et carte des distances\n"
    " t  tour sur place : le robot tourne sur lui-même en mesurant les distances (Safe requis ; 5 ou espace pour l'arrêter)\n"
    " y  robot muet alors qu'il est allumé : essai à 19200 bauds et retour à 115200 bauds\n"
    " q  essayer la lecture des capteurs (groupes 100, 6, 101) et afficher les octets reçus\n"
    " v  écouter le robot 2 s sans rien lui envoyer (texte de démarrage, octets parasites)\n"
    " p  mettre en pause un flux continu de capteurs (opcode 150) si les lectures sont devenues incohérentes\n"
    " o  Power (extinction)           x  Stop OI (à faire en fin de session)\n"));
}

void handle(char c) {
  // Un tour sur place en cours s'arrête dès qu'arrive une touche d'arrêt, de roues, de mode ou de recalibration.
  if (tourActive() && strchr("5 8246sfxohcz", c) != nullptr) tourEnd(false, "arrêt demandé par une touche");
  switch (c) {
    case '?': printHelp(); break;
    case 'w': brcPulse(); out.println(F("Impulsion BRC envoyée.")); break;
    case 's': {
      setMode(OI_START, F("Start (128) -> Passive"));
      // Le robot a-t-il entendu ? Sans réponse à une question simple, il dort, ou il est passé à 19200 bauds :
      // un essai à ce débit le ramène à 115200 (voir baudRescue). Pas plus d'un essai automatique toutes les 5 s.
      // Trois questions avant de conclure : juste après un réveil, le robot met un moment à répondre.
      uint8_t b[2];
      delay(100);
      bool repond = false;
      for (int essai = 0; essai < 3 && !repond; essai++) repond = readSensor(22, b, 2);
      if (!repond && !driving && millis() - lastBaudRescueMs > 5000) baudRescue(true);
      break;
    }
    case 'f': setMode(OI_SAFE,  F("Safe (131)")); break;
    case 'c': setMode(OI_CLEAN, F("Clean (135)")); break;
    case 'h': setMode(OI_DOCK,  F("Seek Dock (143)")); break;
    case 'b': printBattery(); break;
    case 'e': printSensors(); break;
    case 'k': printEncoders(); break;
    case 'n': printLevels(); break;
    case 'p': pauseStream(); break;
    case 'm': playJingle(); break;
    case 'l': ledDemo(); break;
    // Le message n'est affiché qu'au départ : la page web répète l'ordre toutes les 400 ms tant que le bouton est maintenu.
    case '8': if (!wheelsAllowed()) break;        // mode Safe requis
              if (radarForwardBlocked()) break;   // obstacle devant à moins du seuil (radar à ultrasons, arrêt auto actif)
              if (!driving) out.printf("Avance (%d mm/s).\n", driveSpeed);          driveDirect( driveSpeed,  driveSpeed); break;
    case '2': if (!wheelsAllowed()) break;
              if (!driving) out.printf("Recule (%d mm/s).\n", driveSpeed);          driveDirect(-driveSpeed, -driveSpeed); break;
    case '4': if (!wheelsAllowed()) break;
              if (!driving) out.printf("Tourne à gauche (%d mm/s).\n", driveSpeed); driveDirect( driveSpeed, -driveSpeed); break;
    case '6': if (!wheelsAllowed()) break;
              if (!driving) out.printf("Tourne à droite (%d mm/s).\n", driveSpeed); driveDirect(-driveSpeed,  driveSpeed); break;
    case '5': case ' ': stopWheels(); break;
    case 'a':
      keepAwake = !keepAwake;
      lastKeepAwakeMs = millis();
      out.println(keepAwake ? F("Anti-veille activé.") : F("Anti-veille désactivé."));
      break;
    case 'j':
      csvEnabled = !csvEnabled;
      if (csvEnabled) { out.println(F("Journal CSV activé (une ligne toutes les 200 ms tant que le robot répond).")); printCsvHeader(); }
      else out.println(F("Journal CSV désactivé."));
      break;
    case 'i': printInfo(); break;
    case 'q': testGroups(); break;
    case 'v': listenRobot(2000); break;
    case '0': poseReset(true); break;
    case 'g': printImu(); break;
    case 'z':
      if (imu.present) { imu.calibRequested = true; out.println(F("Calibration du gyroscope pendant 1 s : ne pas bouger le robot. Cap remis à zéro.")); }
      else out.println(F("Gyroscope non détecté."));
      break;
    case 'r': if (tourActive()) { out.println(F("Tour sur place en cours : le radar reste en mode fixe.")); break; }
              radarCycleMode(); break;
    case 'u': radarPrintStatus(); break;
    case 't': tourStart(); break;
    case 'y': baudRescue(false); break;
    case 'o': setMode(OI_POWER, F("Power (133)")); break;
    case 'x': setMode(OI_STOP,  F("Stop (173) -> OI fermée")); break;
    default: {
      static uint32_t lastUnknownMs = 0;   // au plus un message par seconde, même si des octets parasites arrivent en rafale
      if (millis() - lastUnknownMs > 1000) { out.printf("Touche inconnue : '%c' ('?' pour l'aide)\n", c); lastUnknownMs = millis(); }
      break;
    }
  }
}

// ---------- Wi-Fi, serveurs, OTA ----------
// Connexion (ou nouvelle connexion) au réseau de la maison, sans redémarrer la carte. Le mot de passe n'est jamais affiché.
void staConnect(const String& ssid, const String& pass) {
  staReason = 0;
  staGotIp = false;
  WiFi.disconnect(false, false);
  delay(100);
  WiFi.setAutoReconnect(true);
  if (pass.length()) WiFi.begin(ssid.c_str(), pass.c_str());
  else WiFi.begin(ssid.c_str());
  out.printf("Connexion au réseau de la maison « %s » en cours...\n", ssid.c_str());
}

// Événements Wi-Fi : exécutés dans la tâche Wi-Fi, on se contente de noter un code lu ensuite par la boucle principale
void onWifiEvent(WiFiEvent_t ev, WiFiEventInfo_t info) {
  if (ev == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) staReason = info.wifi_sta_disconnected.reason;
  else if (ev == ARDUINO_EVENT_WIFI_STA_GOT_IP) { staReason = 0; staGotIp = true; }
}

// Cause de la dernière déconnexion du réseau de la maison, en clair
const char* staReasonText(uint8_t r) {
  static char other[40];
  switch (r) {
    case 0:                                return "";
    case WIFI_REASON_ASSOC_LEAVE:          return "";   // déconnexion demandée par la carte
    case WIFI_REASON_NO_AP_FOUND:          return "réseau introuvable (nom exact ? réseau 2,4 GHz ?)";
    case WIFI_REASON_AUTH_FAIL:
    case WIFI_REASON_AUTH_EXPIRE:
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
    case WIFI_REASON_HANDSHAKE_TIMEOUT:    return "mot de passe refusé";
    case WIFI_REASON_BEACON_TIMEOUT:       return "signal perdu";
    default: snprintf(other, sizeof(other), "déconnecté (code %u)", (unsigned)r); return other;
  }
}

void setupWifi() {
  prefs.begin("wifi", true);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  prefs.end();

  WiFi.persistent(false);
  WiFi.onEvent(onWifiEvent);
  WiFi.setHostname(HOSTNAME);
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID, AP_PASS);
  out.printf("Point d'accès « %s » démarré, adresse %s, mot de passe par défaut : voir en-tête du sketch.\n", AP_SSID, WiFi.softAPIP().toString().c_str());
  if (ssid.length()) staConnect(ssid, pass);

  http.on("/", HTTP_GET, handleRoot);
  http.on("/api/state", HTTP_GET, handleState);
  http.on("/api/cmd", HTTP_GET, handleCmd);
  http.on("/api/speed", HTTP_GET, handleSpeed);
  http.on("/api/log", HTTP_GET, handleLog);
  http.on("/api/scan", HTTP_GET, handleScan);
  http.on("/api/radar", HTTP_GET, handleRadar);
  http.on("/api/tour", HTTP_GET, handleTour);
  http.on("/api/pose", HTTP_GET, handlePose);
  http.on("/api/essai", HTTP_GET, handleEssai);
  http.on("/wifi", HTTP_GET, handleWifiGet);
  http.on("/wifi", HTTP_POST, handleWifiPost);
  http.on("/wifi/forget", HTTP_POST, handleWifiForget);
  http.on("/update", HTTP_GET, handleUpdateGet);
  http.on("/update", HTTP_POST, handleUpdateDone, handleUpdateUpload);
  http.onNotFound([]() { http.send(404, "text/plain; charset=utf-8", "Page inconnue"); });
  static const char* HTTP_HEADERS[] = { "Origin" };   // en-tête lu par updateRequestIsLocal() (web.ino) avant d'accepter une mise à jour
  http.collectHeaders(HTTP_HEADERS, 1);
  http.begin();

  tcpServer.begin();
  tcpServer.setNoDelay(true);

  ArduinoOTA.setHostname(HOSTNAME);
  ArduinoOTA.setPassword(AP_PASS);
  ArduinoOTA.onStart([]() { tourEnd(false, "mise à jour du programme"); if (driving) stopWheels(); out.println(F("Mise à jour OTA (arduino-cli) en cours...")); });
  ArduinoOTA.onEnd([]() { out.println(F("Mise à jour OTA terminée, redémarrage.")); });
  ArduinoOTA.onError([](ota_error_t e) { out.printf("Erreur OTA %u\n", (unsigned)e); });
  ArduinoOTA.begin();          // déclare aussi le nom roomba694.local (mDNS)
  MDNS.addService("http", "tcp", 80);
}

void wifiTick() {
  static uint8_t reportedReason = 0;
  bool connected = (WiFi.status() == WL_CONNECTED);
  if (connected && !staWasConnected) {
    staWasConnected = true;
    reportedReason = 0;
    out.printf("Réseau de la maison « %s » : connecté, adresse %s (ou http://%s.local)\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(), HOSTNAME);
  } else if (!connected && staWasConnected) {
    staWasConnected = false;
    out.println(F("Réseau de la maison : déconnecté, nouvelle tentative automatique."));
  }
  uint8_t r = staReason;
  if (!connected && r != 0 && r != reportedReason) {   // échec d'une tentative : une seule ligne par cause
    reportedReason = r;
    if (staReasonText(r)[0]) out.printf("Réseau de la maison : %s (nouvelle tentative automatique)\n", staReasonText(r));
  }
}

void tcpTick() {
  if (tcpServer.hasClient()) {
    WiFiClient nc = tcpServer.accept();
    if (tcpClient && tcpClient.connected()) {
      nc.println("Un client est déjà connecté à la console.");
      nc.stop();
    } else {
      tcpClient = nc;
      tcpClient.setNoDelay(true);
      tcpWasConnected = true;
      tcpClient.println("Console Roomba 694 par Wi-Fi. Une touche puis Entrée, '?' pour l'aide.");
      out.printf("Client TCP connecté : %s\n", tcpClient.remoteIP().toString().c_str());
    }
  }
  if (tcpClient && tcpClient.connected()) {
    while (tcpClient.available()) {
      char c = (char)tcpClient.read();
      if (c < 0x20 || c > 0x7E) continue;   // fins de ligne, séquences telnet et octets parasites ignorés
      handle(c);
    }
  } else if (tcpWasConnected) {
    tcpWasConnected = false;
    Serial.println(F("Client TCP déconnecté."));
    tourEnd(false, "console TCP déconnectée");   // sans effet si aucun tour sur place n'est en cours
    if (driving) stopWheels();
  }
}

// ---------- Démarrage et boucle ----------
// Raison du dernier redémarrage de la carte, en clair (affichée au démarrage, par 'i' et dans /api/state)
const char* resetReasonText() {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON:  return "mise sous tension";
    case ESP_RST_SW:       return "redémarrage logiciel (mise à jour)";
    case ESP_RST_PANIC:    return "PLANTAGE du firmware";
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT:      return "chien de garde (programme bloqué)";
    case ESP_RST_BROWNOUT: return "BAISSE DE TENSION (alimentation USB insuffisante : câble, batterie)";
    case ESP_RST_EXT:      return "broche EN (bouton reset ou ligne RTS du port série)";
    case ESP_RST_DEEPSLEEP: return "sortie de veille profonde";
    default:               return "inconnue";
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BRC, OUTPUT);
  digitalWrite(PIN_BRC, HIGH);
  robot.begin(115200, SERIAL_8N1, PIN_RX, PIN_TX);   // réglage par défaut du Roomba 600 : 115200 bauds, 8N1
  delay(500);
  printHelp();
  out.printf("Redémarrage de la carte : %s.\n", resetReasonText());
  // Seul ordre envoyé au robot au démarrage : roues à l'arrêt. Sans effet s'il dort ou s'il est en Passive ;
  // indispensable si la carte a redémarré (coupure d'alimentation, plantage) pendant un déplacement en Safe,
  // car le robot garderait sinon son dernier ordre de roues.
  driveDirect(0, 0);
  robot.write(OI_STREAM_PAUSE);   // et fin d'un éventuel flux continu laissé par une session précédente
  robot.write((uint8_t)0);
  prefs.begin("cfg", true);
  driveSpeed = constrain(prefs.getInt("speed", SPEED_MM_S), 20, (int)SPEED_MM_S);   // vitesse choisie sur la page, conservée
  prefs.end();
  setupWifi();
  if (imuInit()) {
    out.printf("Gyroscope MPU-6050 détecté (WHO_AM_I 0x%02X) : calibration pendant 1 s, robot immobile.\n", imu.whoami);
    xTaskCreatePinnedToCore(imuTask, "imu", 4096, nullptr, 1, nullptr, 0);   // second cœur, indépendant de la liaison robot
  } else {
    out.println(F("Gyroscope MPU-6050 non détecté (VCC->3V3, GND, SCL->D22, SDA->D21) : fonctions g et z inactives."));
  }
  radarSetup();   // radar à ultrasons : broches, réglages, tâche sur le second cœur ; reste en mode arrêt tant qu'on ne l'active pas
  out.println(F("Séquence conseillée : s, b (robot réveillé par CLEAN, ou par 'w' deux fois à 4 s d'intervalle)."));
}

void loop() {
  if (driving && millis() - lastDriveMs > DRIVE_TIMEOUT_MS) stopWheels();
  if (keepAwake && millis() - lastKeepAwakeMs > KEEP_AWAKE_MS) { brcPulse(); lastKeepAwakeMs = millis(); }
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c < 0x20 || c > 0x7E) continue;   // fins de ligne et octets parasites ignorés (l'espace, touche stop, passe)
    handle(c);
  }
  tcpTick();
  http.handleClient();
  ArduinoOTA.handle();
  wifiTick();
  pollTick();
  sniffTick();   // le robot a-t-il envoyé son texte de démarrage ?
  radarTick();   // arrêt des roues devant un obstacle, messages du radar
  tourTick();    // tour sur place : ordres de roues répétés, conditions d'arrêt
  if (baudRescuePending && !driving && !tourActive()) { baudRescuePending = false; baudRescue(true); }
}
