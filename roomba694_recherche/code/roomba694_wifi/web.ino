// web.ino — API HTTP et service des pages du firmware roomba694_wifi (second fichier du sketch, concaténé après
// roomba694_wifi.ino). Le HTML des pages est dans pages.h.
//
// Pages :  /            tableau de bord (pilotage, capteurs, gyroscope, console)
//          /wifi        réseau Wi-Fi de la maison : état, recherche des réseaux, enregistrement (sans redémarrage)
//          /update      mise à jour du firmware par fichier .bin (identifiant admin, mot de passe = celui du réseau Roomba694)
// API :    /api/state   état complet en JSON (lu toutes les 600 ms par la page)
//          /api/cmd?c=X envoie la touche X (mêmes touches que la console série)
//          /api/speed?v=N  vitesse des flèches, 50 à SPEED_MM_S mm/s
//          /api/log?since=N  dernières lignes de la console (journal en mémoire, voir TeeOut)
//          /api/scan    réseaux Wi-Fi à portée (lance une recherche, puis renvoie la liste)
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
bool authOk() {
  if (http.authenticate("admin", AP_PASS)) return true;
  http.requestAuthentication();
  return false;
}

void handleRoot() { http.send_P(200, "text/html; charset=utf-8", PAGE_INDEX); }

void handleState() {
  loadSavedSsid();
  String j;
  j.reserve(1800);
  char b[720];
  snprintf(b, sizeof(b),
    "{\"ms\":%lu,\"ver\":\"v2 %s %s\",\"host\":\"%s\",\"driving\":%s,\"speed\":%d,\"keep\":%s,\"csv\":%s,\"ql\":%s,"
    "\"robot\":{\"ok\":%s,\"age\":%lu,\"v\":%u,\"i\":%d,\"t\":%d,\"q\":%u,\"qmax\":%u,\"chg\":%u,\"mode\":%u,"
    "\"bump\":[%u,%u],\"drop\":[%u,%u],\"cliff\":[%u,%u,%u,%u],\"lbits\":%u,\"light\":[%u,%u,%u,%u,%u,%u],"
    "\"enc\":[%d,%d],\"btn\":%u},"
    "\"imu\":{\"ok\":%s,\"cal\":%s,\"yaw\":%.1f,\"rate\":%.1f,\"acc\":[%.2f,%.2f,%.2f]},",
    (unsigned long)millis(), __DATE__, __TIME__, HOSTNAME, driving ? "true" : "false", (int)driveSpeed,
    keepAwake ? "true" : "false", csvEnabled ? "true" : "false", useQueryList ? "true" : "false",
    st.ok ? "true" : "false", (unsigned long)(millis() - st.lastOkMs), st.voltage, st.current, st.temp,
    st.charge, st.capacity, st.charging, st.mode,
    (st.bumpsDrops >> 1) & 1, st.bumpsDrops & 1, (st.bumpsDrops >> 3) & 1, (st.bumpsDrops >> 2) & 1,
    st.cliff[0], st.cliff[1], st.cliff[2], st.cliff[3], st.lightBits,
    st.light[0], st.light[1], st.light[2], st.light[3], st.light[4], st.light[5],
    st.encL, st.encR, st.buttons,
    imu.present ? "true" : "false", imu.calibrating ? "true" : "false", imu.yawDeg, imu.rateDps,
    imu.acc[0], imu.acc[1], imu.acc[2]);
  j += b;
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

const char* ALLOWED_WEB_CMDS = "?wsfchbeknml82465 ajioxgzqp";

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

void handleUpdateGet() {
  if (!authOk()) return;
  http.send_P(200, "text/html; charset=utf-8", PAGE_UPDATE);
}

bool updateAuthorized = false;

void handleUpdateDone() {
  if (!authOk()) return;
  http.sendHeader("Connection", "close");
  if (!updateAuthorized || Update.hasError()) {
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
    updateAuthorized = http.authenticate("admin", AP_PASS);   // rien n'est écrit en flash sans l'identifiant
    if (!updateAuthorized) { out.println(F("Mise à jour refusée : identifiant manquant ou faux.")); return; }
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
    out.println(F("Mise à jour interrompue."));
  }
}
