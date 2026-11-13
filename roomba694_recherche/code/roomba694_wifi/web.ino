// web.ino — API HTTP et service des pages du firmware roomba694_wifi (second fichier du sketch, concaténé après
// roomba694_wifi.ino). Le HTML des pages est dans pages.h.
//
// Pages :  /            tableau de bord (pilotage, capteurs, gyroscope, console)
//          /wifi        réseau Wi-Fi de la maison : état, recherche des réseaux, enregistrement (sans redémarrage)
//          /update      mise à jour du firmware par fichier .bin, sans mot de passe depuis le 2026-11-09 (garde-fou : updateRequestIsLocal)
// API :    /api/state   état complet en JSON (lu toutes les 600 ms par la page)
//          /api/cmd?c=X envoie la touche X (mêmes touches que la console série)
//          /api/speed?v=N  vitesse des flèches, 50 à SPEED_MM_S mm/s
//          /api/log?since=N  dernières lignes de la console (journal en mémoire, voir TeeOut)
//          /api/scan    réseaux Wi-Fi à portée (lance une recherche, puis renvoie la liste)
//          /api/radar   radar à ultrasons (radar.ino) : état et carte polaire en JSON ; paramètres facultatifs : mode=off|fixe|balayage,
//                       angle=-80..80, seuil=10..150 (cm), securite=0|1, auto=0|1, pas=5..45, amplitude=20..80, ech=1..3, inv=0|1, effacer=1,
//                       butee=10..80 (degrés de part et d'autre du centre que le servo ne dépasse jamais)
//          /api/tour    tour sur place (tour.ino) : état et mesures [dixièmes de degré, mm] du dernier tour ; go=1 le lance, stop=1 l'arrête
//          /api/mouv    v10 : avance (av=MM, v=, cap=) ou rotation (rot=DEG) exécutée par le cerveau, stop=1 ; voir mouv.ino
//          /api/pose    position du robot (position.ino) : x, y en mm, cap en degrés, tracé [x, y] ; zero=1 remet à zéro ;
//                       gen et from : la page ne redemande que les points qu'elle n'a pas encore
//          /api/essai   essais sans mouvement de l'enquête sur la liaison : b=octets à envoyer, ecoute=ms (voir handleEssai)
//          /api/carte   carte des obstacles vus par le capteur de distance (carte.ino) : points [x, y] en mm ; effacer=1 ;
//                       dx=N décalage du capteur ; gen et from comme pour /api/pose
//
// Le mot de passe du réseau de la maison n'est jamais renvoyé par l'API ni affiché sur la console.

// ---------- Utilitaires JSON ----------
void jsonStr(String& o, const char* s) {
  o += '"';
  for (const unsigned char* p = (const unsigned char*)s; *p; p++) {
    unsigned char c = *p;
    if (c == '"') o += "\\\"";
    else if (c == '\\') o += "\\\\";
    else if (c < 0x20) { char b[8]; snprintf(b, sizeof(b), "\\u%04x", c); o += b; }
    else o += (char)c;
  }
  o += '"';
}

String savedSsid;
bool   savedLoaded = false;

void loadSavedSsid() {
  if (savedLoaded) return;
  prefs.begin("wifi", true);
  savedSsid = prefs.getString("ssid", "");
  prefs.end();
  savedLoaded = true;
}

#include "pages.h"   // PAGE_INDEX, PAGE_WIFI, PAGE_UPDATE

// ---------- Handlers ----------
// Mise à jour du firmware SANS mot de passe : décision de l'utilisateur du 2026-11-09 (réseau de la maison jugé sûr ;
// l'ancien mot de passe était de toute façon celui du point d'accès, connu de quiconque s'y connecte).
// Il reste un garde-fou sans secret : la requête doit viser une adresse de la carte elle-même (en-tête Host) et ne pas
// venir d'une page d'un autre site (en-tête Origin absent, ou identique à l'adresse visée). Un navigateur joint toujours
// Origin à un envoi de formulaire : une page web quelconque, ouverte sur un appareil de la maison, ne peut donc pas
// remplacer le firmware à l'insu de l'utilisateur. curl (sans Origin) et la page /update de la carte passent.
// Conséquence assumée : tout appareil connecté au réseau de la maison ou au point d'accès peut mettre la carte à jour.
bool updateRequestIsLocal() {
  String full = http.hostHeader();   // « 192.168.18.25 », « roomba694.local », parfois suivi de « :80 »
  full.toLowerCase();
  String host = full;
  int colon = host.indexOf(':');
  if (colon >= 0) host.remove(colon);
  String name = HOSTNAME;
  name.toLowerCase();
  bool own = host == WiFi.softAPIP().toString()
          || (WiFi.status() == WL_CONNECTED && host == WiFi.localIP().toString())
          || host == name || host == name + ".local";
  if (!own) return false;
  String origin = http.header("Origin");   // en-tête collecté grâce à http.collectHeaders() (setup du fichier principal)
  if (!origin.length()) return true;
  origin.toLowerCase();
  return origin == String("http://") + full;
}

void handleRoot() { http.send_P(200, "text/html; charset=utf-8", PAGE_INDEX); }

void handleState() {
  loadSavedSsid();
  String j;
  j.reserve(2400);
  char b[800];
  snprintf(b, sizeof(b),
    "{\"ms\":%lu,\"ver\":\"v10 %s %s\",\"host\":\"%s\",\"driving\":%s,\"speed\":%d,\"keep\":%s,\"csv\":%s,\"lecture\":\"%s\","
    "\"robot\":{\"ok\":%s,\"age\":%lu,\"v\":%u,\"i\":%d,\"t\":%d,\"q\":%u,\"qmax\":%u,\"chg\":%u,\"mode\":%u,"
    "\"bump\":[%u,%u],\"drop\":[%u,%u],\"cliff\":[%u,%u,%u,%u],\"lbits\":%u,\"light\":[%u,%u,%u,%u,%u,%u],"
    "\"enc\":[%d,%d],\"btn\":%u,\"wall\":%u,\"cur\":[%d,%d],\"base\":%s},"
    "\"imu\":{\"ok\":%s,\"cal\":%s,\"yaw\":%.1f,\"rate\":%.1f,\"acc\":[%.2f,%.2f,%.2f],\"biais\":%.3f,\"suivis\":%lu},",
    (unsigned long)millis(), __DATE__, __TIME__, HOSTNAME, driving ? "true" : "false", (int)driveSpeed,
    keepAwake ? "true" : "false", csvEnabled ? "true" : "false", useSplitGroups ? "groupes 6 et 101" : "groupe 100",
    st.ok ? "true" : "false", (unsigned long)(millis() - st.lastOkMs), st.voltage, st.current, st.temp,
    st.charge, st.capacity, st.charging, st.mode,
    (st.bumpsDrops >> 1) & 1, st.bumpsDrops & 1, (st.bumpsDrops >> 3) & 1, (st.bumpsDrops >> 2) & 1,
    st.cliff[0], st.cliff[1], st.cliff[2], st.cliff[3], st.lightBits,
    st.light[0], st.light[1], st.light[2], st.light[3], st.light[4], st.light[5],
    st.encL, st.encR, st.buttons, st.wallSignal, st.curL, st.curR, (st.chargeSrc & 2) ? "true" : "false",
    imu.present ? "true" : "false", imu.calibrating ? "true" : "false", imuCap(), imu.rateDps,
    imu.acc[0], imu.acc[1], imu.acc[2],
    (imu.vertAxis >= 0) ? imu.vertSign * imu.bias[imu.vertAxis] : 0.0f, (unsigned long)imu.suivis);   // v9 : zéro du gyroscope suivi à l'arrêt
  j += b;
  poseStateJson(j);    // "pose":{x, y, cap, cap_roues, dist, n, gen, pas, gyro, leve, leves, sauts}
  carteStateJson(j);   // "carte":{total, gen, dx}
  radarStateJson(j);   // "radar":{mode, front_mm, age, present, servo}
  tourStateJson(j);    // "tour":{etat, tourne, n}
  mouvStateJson(j);    // "mouv":{etat, n, fait_mm, fait_deg} (v10)
  // réflexe pare-chocs (v6) : arrêts décidés par le cerveau, ordres refusés, verrou après un choc, cause du dernier arrêt
  j += "\"reflexe\":{\"arrets\":"; j += (unsigned long)reflexStops; j += ",\"refus\":"; j += (unsigned long)reflexRefused;
  j += ",\"verrou\":"; j += bumpLatch ? "true" : "false"; j += ",\"cause\":"; jsonStr(j, reflexCause); j += "},";
  j += "\"bauds19200\":"; j += (unsigned long)baudRescues; j += ',';   // retours du robot de 19200 à 115200 bauds depuis le démarrage
  j += "\"robot_redem\":"; j += (unsigned long)robotBoots; j += ',';   // redémarrages du robot vus (texte de démarrage reçu)
  j += "\"ap\":{\"ssid\":"; jsonStr(j, AP_SSID);
  j += ",\"ip\":\""; j += WiFi.softAPIP().toString(); j += "\",\"clients\":"; j += (int)WiFi.softAPgetStationNum(); j += "},";
  j += "\"rst\":"; jsonStr(j, resetReasonText()); j += ',';
  bool on = (WiFi.status() == WL_CONNECTED);
  j += "\"sta\":{\"saved\":"; jsonStr(j, savedSsid.c_str());
  j += ",\"on\":"; j += on ? "true" : "false";
  j += ",\"ip\":\""; if (on) j += WiFi.localIP().toString(); j += "\"";
  j += ",\"err\":"; jsonStr(j, on ? "" : staReasonText(staReason));
  j += "}}";
  http.send(200, "application/json", j);
}

const char* ALLOWED_WEB_CMDS = "?wsfchbeknml82465 ajioxgzqpruty0v";

void handleCmd() {
  String c = http.arg("c");
  if (c.length() == 1 && strchr(ALLOWED_WEB_CMDS, c[0]) != nullptr) {
    handle(c[0]);
    http.send(200, "text/plain", "ok");
  } else {
    http.send(400, "text/plain", "commande inconnue");
  }
}

void handleSpeed() {
  int v = http.arg("v").toInt();
  if (v < 20 || v > SPEED_MM_S) { http.send(400, "text/plain; charset=utf-8", "vitesse hors limites"); return; }
  driveSpeed = (int16_t)v;
  prefs.begin("cfg", false);
  prefs.putInt("speed", driveSpeed);   // conservée d'un démarrage à l'autre
  prefs.end();
  out.printf("Vitesse réglée à %d mm/s (page web).\n", (int)driveSpeed);
  http.send(200, "text/plain", String(driveSpeed));
}

// Dernières lignes de la console : /api/log?since=N renvoie les lignes de numéro >= N encore en mémoire
void handleLog() {
  uint32_t since = http.hasArg("since") ? strtoul(http.arg("since").c_str(), nullptr, 10) : 0;
  uint32_t end = logSeq;                                  // lignes terminées : 0 .. end-1
  uint32_t start = (end >= LOG_LINES) ? end - (LOG_LINES - 1) : 0;   // la case la plus ancienne est en cours de réécriture
  if (since > start) start = since;
  if (start > end) start = end;
  String j;
  j.reserve(LOG_WIDTH * (end - start) + 64);
  j += "{\"seq\":"; j += (unsigned long)end; j += ",\"from\":"; j += (unsigned long)start; j += ",\"lines\":[";
  for (uint32_t i = start; i < end; i++) { if (i > start) j += ','; jsonStr(j, logBuf[i % LOG_LINES]); }
  j += "]}";
  http.send(200, "application/json", j);
}

// Réseaux à portée : la première requête lance une recherche (asynchrone, 2 à 3 s), les suivantes renvoient la liste
void handleScan() {
  int n = WiFi.scanComplete();
  if (n == WIFI_SCAN_FAILED) {
    WiFi.scanNetworks(true, false);
    http.send(200, "application/json", "{\"status\":\"scanning\"}");
    return;
  }
  if (n == WIFI_SCAN_RUNNING) { http.send(200, "application/json", "{\"status\":\"scanning\"}"); return; }
  String j;
  j.reserve(64 + 56 * n);
  j += "{\"status\":\"done\",\"networks\":[";
  int shown = 0;
  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    if (!s.length()) continue;
    bool dup = false;
    for (int k = 0; k < i && !dup; k++) if (WiFi.SSID(k) == s) dup = true;   // un même réseau vu par plusieurs bornes
    if (dup) continue;
    if (shown++) j += ',';
    j += "{\"ssid\":"; jsonStr(j, s.c_str());
    j += ",\"rssi\":"; j += WiFi.RSSI(i);
    j += ",\"open\":"; j += (WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "true" : "false";
    j += '}';
  }
  j += "]}";
  WiFi.scanDelete();
  http.send(200, "application/json", j);
}

void handleWifiGet() { http.send_P(200, "text/html; charset=utf-8", PAGE_WIFI); }

void handleWifiPost() {
  String ssid = http.arg("ssid");
  String pass = http.arg("pass");
  ssid.trim();
  if (ssid.length() == 0 || ssid.length() > 32) { http.send(400, "application/json", "{\"ok\":false,\"msg\":\"nom de réseau vide ou trop long\"}"); return; }
  if (pass.length() > 63) { http.send(400, "application/json", "{\"ok\":false,\"msg\":\"mot de passe trop long\"}"); return; }
  prefs.begin("wifi", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  prefs.end();
  savedSsid = ssid;
  savedLoaded = true;
  out.printf("Réseau de la maison « %s » enregistré depuis la page /wifi.\n", ssid.c_str());
  http.send(200, "application/json", "{\"ok\":true}");   // réponse envoyée avant la connexion, qui peut couper brièvement le point d'accès
  staConnect(ssid, pass);
}

void handleWifiForget() {
  prefs.begin("wifi", false);
  prefs.clear();
  prefs.end();
  savedSsid = "";
  savedLoaded = true;
  staReason = 0;
  WiFi.disconnect(false, true);
  out.println(F("Réseau de la maison oublié (page /wifi)."));
  http.send(200, "application/json", "{\"ok\":true}");
}

void handleUpdateGet() { http.send_P(200, "text/html; charset=utf-8", PAGE_UPDATE); }

bool updateAuthorized = false;   // vrai pendant un envoi accepté par updateRequestIsLocal()

void handleUpdateDone() {
  http.sendHeader("Connection", "close");
  if (!updateAuthorized) {   // requête refusée, ou sans fichier : rien n'a été écrit en flash, la carte ne redémarre pas
    http.send(403, "text/plain; charset=utf-8", "Mise à jour refusée : elle doit être envoyée à l'adresse de la carte, avec un fichier, et pas par une page d'un autre site.");
    return;
  }
  updateAuthorized = false;
  if (Update.hasError()) {
    http.send(200, "text/plain; charset=utf-8", "ÉCHEC de la mise à jour : voir la console. La carte redémarre avec l'ancien firmware.");
  } else {
    http.send(200, "text/plain; charset=utf-8", "Mise à jour réussie, la carte redémarre.");
  }
  delay(800);
  ESP.restart();
}

void handleUpdateUpload() {
  HTTPUpload& up = http.upload();
  if (up.status == UPLOAD_FILE_START) {
    updateAuthorized = updateRequestIsLocal();   // pas de mot de passe, mais rien n'est écrit en flash pour une requête venue d'ailleurs
    if (!updateAuthorized) { out.println(F("Mise à jour refusée : requête adressée à un autre nom que la carte, ou venue d'une page d'un autre site.")); return; }
    tourEnd(false, "mise à jour du programme");   // sans effet si aucun tour sur place n'est en cours
    if (driving) stopWheels();
    out.printf("Mise à jour par la page web : %s\n", up.filename.c_str());
    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) Update.printError(Serial);
  } else if (!updateAuthorized) {
    return;
  } else if (up.status == UPLOAD_FILE_WRITE) {
    if (Update.write(up.buf, up.currentSize) != up.currentSize) Update.printError(Serial);
  } else if (up.status == UPLOAD_FILE_END) {
    if (Update.end(true)) out.printf("Mise à jour reçue : %u octets.\n", (unsigned)up.totalSize);
    else Update.printError(Serial);
  } else if (up.status == UPLOAD_FILE_ABORTED) {
    Update.abort();
    updateAuthorized = false;
    out.println(F("Mise à jour interrompue."));
  }
}

// ---------- Essais de l'enquête sur la liaison (2026-11-09) ----------
// /api/essai?b=150,255&ecoute=1000 : envoie au robot la suite d'octets donnée (24 au plus), écoute sa réponse pendant
// « ecoute » ms (100 à 5000) et renvoie les octets reçus. Réservé aux essais SANS MOUVEMENT : ne passent que les octets
// qui ne peuvent être, même lus de travers par le robot, ni un ordre de roues, de moteurs ou de nettoyage, ni un
// changement de mode ou de débit. Restent permis : les valeurs inférieures à 128, 255, et les ordres 139 (voyants),
// 140 et 141 (notes), 142, 148, 149, 150 (capteurs). Refusé pendant que les roues tournent.
bool essaiByteOk(long v) {
  if (v < 0 || v > 255) return false;
  if (v < 128 || v == 255) return true;
  return v == 139 || v == 140 || v == 141 || v == 142 || v == 148 || v == 149 || v == 150;
}

void handleEssai() {
  String s = http.arg("b");
  uint8_t bytes[24];
  size_t n = 0;
  const char* p = s.c_str();
  bool ok = s.length() > 0;
  while (ok && *p) {
    char* fin = nullptr;
    long v = strtol(p, &fin, 10);
    if (fin == p || !essaiByteOk(v) || n >= sizeof(bytes)) { ok = false; break; }
    bytes[n++] = (uint8_t)v;
    p = fin;
    if (*p == ',') p++;
    else if (*p) ok = false;
  }
  if (!ok || n == 0) { http.send(400, "text/plain; charset=utf-8", "octets refusés : b=liste de nombres séparés par des virgules, parmi les valeurs permises (voir web.ino)"); return; }
  if (driving || tourActive()) { http.send(409, "text/plain; charset=utf-8", "refusé : les roues tournent"); return; }
  uint32_t ecoute = http.hasArg("ecoute") ? (uint32_t)constrain(http.arg("ecoute").toInt(), 100L, 5000L) : 500;
  finishPendingRead();
  waitInterQuery();
  flushInput();
  robot.write(bytes, n);
  static uint8_t rx[160];
  size_t got = 0, total = 0;
  uint32_t t0 = millis(), tPremier = 0;
  while (millis() - t0 < ecoute) {
    if (robot.available()) {
      uint8_t c = (uint8_t)robot.read();
      if (!total) tPremier = millis() - t0;
      total++;
      sniffByte(c);
      if (got < sizeof(rx)) rx[got++] = c;
    } else {
      delay(1);
    }
  }
  lastExchangeMs = millis();
  String j;
  j.reserve(200 + 4 * (n + got));
  j += "{\"envoye\":[";
  for (size_t i = 0; i < n; i++) { if (i) j += ','; j += (int)bytes[i]; }
  j += "],\"mode_avant\":"; j += (int)st.mode;
  j += ",\"ecoute_ms\":"; j += (unsigned long)ecoute;
  j += ",\"recus\":"; j += (unsigned long)total;
  j += ",\"premier_ms\":"; j += (unsigned long)tPremier;
  j += ",\"octets\":[";
  for (size_t i = 0; i < got; i++) { if (i) j += ','; j += (int)rx[i]; }
  j += "]}";
  out.printf("Essai : %u octet(s) envoyé(s) au robot (", (unsigned)n);
  for (size_t i = 0; i < n; i++) out.printf("%s%u", i ? ", " : "", (unsigned)bytes[i]);
  out.printf("), %lu octet(s) reçu(s) en %lu ms.\n", (unsigned long)total, (unsigned long)ecoute);
  http.send(200, "application/json", j);
}

// ---------- Tour sur place (tour.ino) ----------
// /api/tour renvoie l'état et les mesures du dernier tour ; go=1 le lance (mêmes vérifications que la touche 't'),
// stop=1 l'arrête. Le lancer fait tourner le robot sur lui-même : mode Safe requis, voir les sécurités dans tour.ino.
void handleTour() {
  if (http.hasArg("stop")) tourEnd(false, "arrêt demandé");
  else if (http.hasArg("go")) {
    if (http.hasArg("v")) tourRouesDemande = (int16_t)constrain(http.arg("v").toInt(), (long)TOUR_WHEEL_MIN, (long)TOUR_WHEEL_MM_S);   // tour lent (v8)
    tourStart();
  }
  String j;
  j.reserve(5400);   // jusqu'à 400 mesures de 11 caractères environ
  tourJson(j);
  http.send(200, "application/json", j);
}

// ---------- Radar à ultrasons (radar.ino) : état, carte et réglages ----------
// /api/radar renvoie l'état ; les paramètres facultatifs modifient d'abord les réglages (conservés en flash, sauf le mode et l'angle).
void handleRadar() {
  bool save = false;
  if (http.hasArg("butee")) {   // traitée en premier : l'angle demandé dans la même requête lui obéit déjà
    int v = http.arg("butee").toInt();
    if (v >= 10 && v <= RADAR_SPAN_MAX) { radar.butee = (int8_t)v; out.printf("Radar : butée du servo à %d° de chaque côté.\n", v); save = true; }
  }
  if (http.hasArg("angle")) radar.fixedDeg = (int8_t)constrain(http.arg("angle").toInt(), -radarLimit(), radarLimit());
  if (http.hasArg("mode")) {
    String m = http.arg("mode");
    if (m == "off" || m == "arret") radarSetMode(RADAR_OFF);
    else if (m == "fixe")           radarSetMode(RADAR_FIXED);
    else if (m == "balayage")       radarSetMode(RADAR_SWEEP);
    else { http.send(400, "text/plain; charset=utf-8", "mode inconnu : off, fixe ou balayage"); return; }
  } else if (http.hasArg("angle") && radar.mode == RADAR_FIXED) {
    out.printf("Radar : capteur vers %d°.\n", (int)radar.fixedDeg);
  }
  if (http.hasArg("seuil"))     { radar.seuilCm = (int16_t)constrain(http.arg("seuil").toInt(), 10, 150); out.printf("Radar : seuil d'arrêt %d cm.\n", (int)radar.seuilCm); save = true; }
  if (http.hasArg("securite"))  { radar.securite = http.arg("securite") == "1"; out.printf("Radar : arrêt automatique %s.\n", radar.securite ? "activé" : "désactivé"); save = true; }
  if (http.hasArg("auto"))      { radar.autoFront = http.arg("auto") == "1"; out.printf("Radar : capteur devant pendant une marche avant : %s.\n", radar.autoFront ? "oui" : "non"); save = true; }
  if (http.hasArg("pas"))       { int v = http.arg("pas").toInt(); if (v >= 5 && v <= 45 && v % 5 == 0) { radar.pas = (int8_t)v; save = true; } }
  if (http.hasArg("amplitude")) { int v = http.arg("amplitude").toInt(); if (v >= 20 && v <= RADAR_SPAN_MAX) { radar.amplitude = (int8_t)((v / 5) * 5); save = true; } }
  if (http.hasArg("ech"))       { radar.ech = (int8_t)constrain(http.arg("ech").toInt(), 1, 3); save = true; }
  if (http.hasArg("inv"))       { radar.inverse = http.arg("inv") == "1"; out.printf("Radar : sens du servo %s.\n", radar.inverse ? "inversé" : "normal"); save = true; }
  if (http.hasArg("effacer"))   radarClearMap();
  if (save) radarSaveSettings();

  String j;
  j.reserve(1100);
  char b[448];
  snprintf(b, sizeof(b),
    "{\"mode\":%u,\"present\":%s,\"absent\":%s,\"following\":%s,\"servo\":%d,\"front_cm\":%.1f,\"front_age\":%lu,"
    "\"seuil\":%d,\"securite\":%s,\"auto\":%s,\"pas\":%d,\"amplitude\":%d,\"butee\":%d,\"ech\":%d,\"inv\":%s,"
    "\"mesures\":%lu,\"sans_echo\":%lu,\"defauts\":%lu,\"passages\":%lu,\"arrets\":%lu,\"refus\":%lu,\"points\":[",
    (unsigned)radar.mode, radar.present ? "true" : "false", radar.absent ? "true" : "false", radar.following ? "true" : "false",
    (int)radar.servoDeg, radar.frontMm < 0 ? -1.0 : radar.frontMm / 10.0, (unsigned long)(millis() - radar.frontMs),
    (int)radar.seuilCm, radar.securite ? "true" : "false", radar.autoFront ? "true" : "false", (int)radar.pas, (int)radar.amplitude,
    radarLimit(), (int)radar.ech, radar.inverse ? "true" : "false",
    (unsigned long)radar.pings, (unsigned long)radar.noEcho, (unsigned long)radar.faults, (unsigned long)radar.sweeps,
    (unsigned long)radar.stops, (unsigned long)radar.refused);
  j += b;
  int16_t  mm[RADAR_SLOTS];
  uint32_t ms[RADAR_SLOTS];
  portENTER_CRITICAL(&radarMux);                 // copie cohérente de la carte : la tâche radar écrit pendant ce temps
  for (int i = 0; i < RADAR_SLOTS; i++) { mm[i] = radar.mm[i]; ms[i] = radar.ms[i]; }
  portEXIT_CRITICAL(&radarMux);
  uint32_t now = millis();
  bool first = true;
  for (int i = 0; i < RADAR_SLOTS; i++) {
    if (mm[i] < 0) continue;                     // case jamais mesurée
    char p[40];
    snprintf(p, sizeof(p), "%s[%d,%d,%lu]", first ? "" : ",", -RADAR_SPAN_MAX + i * RADAR_SLOT_DEG, (int)mm[i], (unsigned long)(now - ms[i]));
    j += p;                                      // [angle en degrés, distance en mm (0 = rien à portée), âge en ms]
    first = false;
  }
  j += "]}";
  http.send(200, "application/json", j);
}
