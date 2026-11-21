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
//          /api/texte?depuis=N  v13 : texte écrit par le robot de lui-même, en entier, daté par la carte (voir handleTexte)
//          /api/sonde   v13 : recherche de ce que le robot accepte par sa prise ; sous clé, compilée seulement si secrets.h
//                       définit CLE_SONDE (voir handleSonde)
//          /api/scan    réseaux Wi-Fi à portée (lance une recherche, puis renvoie la liste)
//          /api/radar   radar à ultrasons (radar.ino) : état et carte polaire en JSON ; paramètres facultatifs : mode=off|fixe|balayage,
//                       angle=-90..90, seuil=10..150 (cm), securite=0|1, auto=0|1, pas=5..45, amplitude=20..90, ech=1..3, inv=0|1, effacer=1,
//                       butee=10..90 (degrés de part et d'autre du centre que le servo ne dépasse jamais ; plafond RADAR_BUTEE_MAX, v12 ;
//                       v15 : 90 au lieu de 30, et la butée réglée reste à 30 tant qu'on ne la relève pas),
//                       lent=1..10 (v15 : degrés par seconde de la rotation lente, au-delà de ±30°),
//                       doux=1 (v16 : le mouvement demandé dans la même requête est lent d'un bout à l'autre, même en deçà de 30°),
//                       fige=1 (v16 : le capteur s'arrête là où il est)
//          /api/tour    tour sur place (tour.ino) : état et mesures [dixièmes de degré, mm] du dernier tour ; go=1 le lance, stop=1 l'arrête
//          /api/mouv    v10 : avance (av=MM, v=, cap=) ou rotation (rot=DEG) exécutée par le cerveau, stop=1 ; voir mouv.ino
//          /api/pose    position du robot (position.ino) : x, y en mm, cap en degrés, tracé [x, y] ; zero=1 remet à zéro ;
//                       gen et from : la page ne redemande que les points qu'elle n'a pas encore
//          /api/essai   essais sans mouvement de l'enquête sur la liaison : b=octets à envoyer, ecoute=ms (voir handleEssai) ;
//                       plus compilé depuis la v12, sauf si ESSAI_LIAISON vaut 1 (fichier principal)
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
  j.reserve(2700);   // v13 : 2400 + la dernière ligne « bat: »
  char b[800];
  snprintf(b, sizeof(b),
    "{\"ms\":%lu,\"ver\":\"v16 %s %s\",\"host\":\"%s\",\"driving\":%s,\"speed\":%d,\"keep\":%s,\"csv\":%s,\"lecture\":\"%s\","
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
  brosseStateJson(j);  // "brosse":{lat, max, marches} (v14 : brosse latérale seule)
  // réflexe pare-chocs (v6) : arrêts décidés par le cerveau, ordres refusés, verrou après un choc, cause du dernier arrêt
  j += "\"reflexe\":{\"arrets\":"; j += (unsigned long)reflexStops; j += ",\"refus\":"; j += (unsigned long)reflexRefused;
  j += ",\"verrou\":"; j += bumpLatch ? "true" : "false"; j += ",\"cause\":"; jsonStr(j, reflexCause); j += "},";
  // v11 : tampon de la console TCP (octets en attente, plus grand remplissage vu, octets abandonnés tampon plein)
  j += "\"console\":{\"tampon\":"; j += (unsigned long)consEnAttente(); j += ",\"max\":"; j += (unsigned long)consMax;
  j += ",\"perdus\":"; j += (unsigned long)consPerdus; j += "},";
  j += "\"bauds19200\":"; j += (unsigned long)baudRescues; j += ',';   // retours du robot de 19200 à 115200 bauds depuis le démarrage
  j += "\"robot_redem\":"; j += (unsigned long)robotBoots; j += ',';   // redémarrages du robot vus (texte de démarrage reçu)
  // v13 : texte écrit par le robot (mémoire tournante lue par /api/texte) et dernière ligne « bat: » reçue (âge en ms, -1 = aucune)
  long batAge = batLignes ? (long)(millis() - batMs) : -1L;
  j += "\"texte\":{\"pos\":"; j += (unsigned long)txtPos; j += ",\"lignes\":"; j += (unsigned long)txtLignes; j += "},";
  j += "\"bat\":{\"n\":"; j += (unsigned long)batLignes; j += ",\"age\":"; j += batAge; j += ",\"ligne\":"; jsonStr(j, batLigne); j += "},";
  // v13 : la sonde (/api/sonde) est-elle dans ce firmware, suspend-elle la lecture périodique, la liaison est-elle restée douteuse
  j += "\"sonde\":{\"compilee\":"; j += SONDE_COMPILEE ? "true" : "false"; j += ",\"suspend\":"; j += sondeActive() ? "true" : "false";
  j += ",\"douteux\":"; j += sondeDouteux ? "true" : "false"; j += "},";
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

// v13 : texte écrit par le robot de lui-même (réveil, charge, redémarrage...), gardé en entier par sniffByte().
// /api/texte?depuis=N renvoie du texte brut : une première ligne « pos P depuis D ms M », puis les caractères de la
// mémoire tournante de la position D à la position P. Chaque ligne du robot y est précédée de l'heure de la carte en
// millisecondes et d'une tabulation. L'outil qui lit redemande ensuite depuis=P ; si P a diminué, la carte a redémarré.
// Lecture seule : rien n'est envoyé au robot.
void handleTexte() {
  uint32_t depuis = http.hasArg("depuis") ? strtoul(http.arg("depuis").c_str(), nullptr, 10) : 0;
  uint32_t fin = txtPos;
  uint32_t debut = (fin > TXT_RING) ? fin - TXT_RING : 0;   // le plus ancien caractère encore en mémoire
  if (depuis > debut) debut = depuis;
  if (debut > fin) debut = fin;
  String r;
  r.reserve((fin - debut) + 64);
  r += "pos "; r += (unsigned long)fin; r += " depuis "; r += (unsigned long)debut; r += " ms "; r += (unsigned long)millis(); r += '\n';
  for (uint32_t i = debut; i < fin; i++) r += txtRing[i % TXT_RING];
  http.send(200, "text/plain; charset=utf-8", r);
}

// ---------- Sonde (v13) : chercher ce que le robot accepte par sa prise ----------
// /api/sonde?cle=...&action=lire|ecrire|essai|aplomb&o=HEX&ecoute=MS
//   cle     la clé CLE_SONDE de secrets.h ; sans elle, rien
//   o       octets à envoyer, en hexadécimal sans séparateur (« 8E23 » = 142, 35) ; vide = écouter seulement
//   ecoute  durée d'écoute après l'envoi, de 20 à 3000 ms (80 par défaut)
// Quatre actions, de la plus anodine à la plus risquée :
//   lire    les octets doivent former des ordres de lecture documentés et complets : 142 + numéro, 149 + liste,
//           128 (Start), 150 + un octet. Sert à demander au robot des numéros de capteurs que la documentation ne cite pas.
//   ecrire  ordres documentés et complets qui ne font tourner aucun moteur : 139 (voyants), 140 (suite de notes),
//           141 (la jouer), 162, 163, 164 (voyants et afficheur), 168 (jour et heure), 173 (Stop), plus ceux de « lire ».
//   essai   au plus 12 octets quelconques, SAUF ceux de la liste interdite, pour chercher des ordres non documentés.
//           Un ordre inconnu peut tout faire, y compris lancer un moteur. Le cerveau vérifie donc lui-même, juste avant
//           d'envoyer, que le robot répond, que ses DEUX roues sont levées et qu'il n'est ni sur sa base ni sur son
//           chargeur. Après l'écoute il pose une question de contrôle (142, 35) : si le robot n'y répond pas par un
//           octet, il attend peut-être la suite d'un ordre ; la liaison est dite « douteuse » et tout est refusé
//           jusqu'à un « aplomb » réussi.
//   aplomb  remet la liaison d'aplomb : 40 zéros (pour finir un ordre qui attendrait sa suite), pause du flux (150, 0),
//           Start (128), puis la question de contrôle. Permis seulement dans la minute qui suit un essai.
// Interdits dans « essai » à n'importe quelle place, et jamais permis comme ordre dans « lire » et « ecrire » :
//   132 (mode Full), 131 (mode Safe : il se demande par la touche f), 137, 145, 146 (roues), 138, 144 (brosses et
//   aspiration), 134, 135, 136 (nettoyage), 143 (retour à la base), 129 (débit de la liaison), 133 (extinction),
//   148 (flux continu), 165 (appui simulé sur un bouton : il lancerait un nettoyage), 167 (horaires de nettoyage),
//   7 (Reset).
// Toujours refusé pendant que les roues tournent, pendant un tour ou un mouvement. Après « ecrire », « essai » et
// « aplomb », l'état du robot est tenu pour inconnu (st.ok faux) : aucun ordre de roues ne repart avant une nouvelle
// lecture complète réussie, et le robot est alors en mode passif ou dans le mode où l'essai l'a laissé.
#ifdef CLE_SONDE
uint32_t sondeEssaiMs = 0;          // heure du dernier essai
bool     sondeEssaiFait = false;

bool sondeCleOk() {
  String c = http.arg("cle");
  const char* k = CLE_SONDE;
  size_t n = strlen(k);
  if (n < 12 || c.length() != n) return false;      // une clé de moins de 12 caractères ne protège rien : route fermée
  uint8_t d = 0;
  for (size_t i = 0; i < n; i++) d |= (uint8_t)(c[i] ^ k[i]);
  return d == 0;
}

bool sondeInterdit(uint8_t v) {
  switch (v) {
    case 7: case 129: case 131: case 132: case 133: case 134: case 135: case 136: case 137: case 138:
    case 143: case 144: case 145: case 146: case 148: case 165: case 167:
      return true;
  }
  return false;
}

// Nombre d'octets de données d'un ordre documenté permis ; -1 = pas permis dans cette action ; -2 = nombre variable
int sondeLongueur(uint8_t op, bool ecrire) {
  switch (op) {
    case 128: return 0;                 // Start
    case 142: return 1;                 // un paquet de capteurs
    case 150: return 1;                 // pause ou reprise du flux
    case 149: return -2;                // liste de paquets : n, puis n numéros
  }
  if (!ecrire) return -1;
  switch (op) {
    case 139: return 3;                 // voyants
    case 141: return 1;                 // jouer une suite de notes
    case 162: return 2;                 // voyants des horaires
    case 163: return 4;                 // afficheur, segments
    case 164: return 4;                 // afficheur, lettres
    case 168: return 3;                 // jour, heure, minute
    case 173: return 0;                 // Stop
    case 140: return -2;                // suite de notes : numéro, n, puis 2 n octets
  }
  return -1;
}

// Vrai si les octets forment une suite d'ordres documentés, permis dans cette action, et complets
bool sondeComplet(const uint8_t* b, size_t n, bool ecrire) {
  size_t i = 0;
  while (i < n) {
    uint8_t op = b[i++];
    int l = sondeLongueur(op, ecrire);
    if (l == -1) return false;
    if (l == -2) {
      if (op == 149) {
        if (i >= n) return false;
        l = b[i++];
        if (l < 1 || l > 14) return false;
      } else {                          // 140
        if (i + 1 >= n) return false;
        if (b[i] > 4 || b[i + 1] < 1 || b[i + 1] > 16) return false;
        l = 2 * b[i + 1];
        i += 2;
      }
    }
    if (i + (size_t)l > n) return false;
    i += (size_t)l;
  }
  return true;
}

int sondeHexVal(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

void sondeHex(String& j, const uint8_t* b, size_t n) {
  static const char H[] = "0123456789ABCDEF";
  for (size_t i = 0; i < n; i++) { j += H[b[i] >> 4]; j += H[b[i] & 15]; }
}

// Écoute le robot pendant « ms » millisecondes au plus ; range ce qui arrive dans rx (« max » octets au plus) et le
// montre à sniffByte(), pour que le texte du robot soit gardé. Si « calme » n'est pas nul, s'arrête dès que le robot
// s'est tu pendant « calme » millisecondes après un premier octet. Renvoie le nombre total d'octets reçus.
size_t sondeEcoute(uint8_t* rx, size_t max, uint32_t ms, uint32_t calme, uint32_t* premier) {
  size_t got = 0;
  uint32_t t0 = millis(), dernier = t0;
  *premier = 0;
  while (millis() - t0 < ms) {
    if (robot.available()) {
      uint8_t c = (uint8_t)robot.read();
      dernier = millis();
      if (!got) *premier = dernier - t0;
      sniffByte(c);
      if (got < max) rx[got] = c;
      got++;
    } else {
      if (got && calme && millis() - dernier >= calme) break;
      delay(1);
    }
  }
  lastExchangeMs = millis();
  return got;
}

void handleSonde() {
  const char* TXT = "text/plain; charset=utf-8";
  if (!sondeCleOk()) { http.send(403, TXT, "clé refusée"); return; }
  if (driving || tourActive() || mouvActive()) { http.send(409, TXT, "refusé : le robot bouge"); return; }
  String action = http.arg("action");
  bool lire = action == "lire", ecrire = action == "ecrire", essai = action == "essai", aplomb = action == "aplomb";
  if (!lire && !ecrire && !essai && !aplomb) { http.send(400, TXT, "action : lire, ecrire, essai ou aplomb"); return; }

  uint8_t b[40];
  size_t n = 0;
  String o = http.arg("o");
  if (o.length() % 2 || o.length() > 2 * sizeof(b)) { http.send(400, TXT, "o : octets en hexadécimal, deux caractères par octet, 40 octets au plus"); return; }
  for (size_t i = 0; i < o.length(); i += 2) {
    int h = sondeHexVal(o[i]), l = sondeHexVal(o[i + 1]);
    if (h < 0 || l < 0) { http.send(400, TXT, "o : octets en hexadécimal, deux caractères par octet, 40 octets au plus"); return; }
    b[n++] = (uint8_t)(h * 16 + l);
  }
  uint32_t ecoute = http.hasArg("ecoute") ? (uint32_t)constrain(http.arg("ecoute").toInt(), 20L, 3000L) : 80;
  uint32_t calme = http.hasArg("calme") ? (uint32_t)constrain(http.arg("calme").toInt(), 5L, 500L) : 0;

  static uint8_t rx[200];
  uint8_t q[8];
  size_t got = 0, nq = 0;
  uint32_t premier = 0, premierQ = 0;
  uint8_t roues = 0, base = 0, modeAvant = 0;

  if (aplomb) {
    if (n) { http.send(400, TXT, "aplomb : sans octets"); return; }
    if (!sondeEssaiFait || millis() - sondeEssaiMs > 60000UL) { http.send(409, TXT, "aplomb : permis seulement dans la minute qui suit un essai"); return; }
    finishPendingRead();
    waitInterQuery();
    flushInput();
    for (int i = 0; i < 40; i++) {
      robot.write((uint8_t)0);
      if (i % 8 == 7) { robot.flush(); delay(5); }
    }
    robot.write((uint8_t)OI_STREAM_PAUSE);            // au cas où un ordre inconnu aurait lancé le flux continu
    robot.write((uint8_t)0);
    robot.write((uint8_t)OI_START);
    robot.flush();
    got = sondeEcoute(rx, sizeof(rx), 80, 0, &premier);
  } else {
    if (sondeDouteux) { http.send(409, TXT, "refusé : la liaison est restée douteuse après le dernier essai ; action=aplomb d'abord"); return; }
    if (essai) {
      if (n == 0 || n > 12) { http.send(400, TXT, "essai : de 1 à 12 octets"); return; }
      for (size_t i = 0; i < n; i++) {
        if (sondeInterdit(b[i])) { http.send(400, TXT, String("essai : octet interdit ") + String((int)b[i])); return; }
      }
      if (!readSensor(7, &roues, 1) || !readSensor(34, &base, 1) || !readSensor(35, &modeAvant, 1)) {
        http.send(409, TXT, "essai refusé : le robot ne répond pas"); return;
      }
      if ((roues & 0x0C) != 0x0C) { http.send(409, TXT, "essai refusé : les deux roues du robot doivent être levées (robot posé sur un support, roues dans le vide)"); return; }
      if (base != 0) { http.send(409, TXT, "essai refusé : le robot est sur sa base ou sur son chargeur"); return; }
    } else if (n && !sondeComplet(b, n, ecrire)) {
      http.send(400, TXT, "octets refusés : seulement des ordres documentés, permis dans cette action, et complets (voir web.ino)"); return;
    }
    finishPendingRead();
    waitInterQuery();
    flushInput();
    if (n) { robot.write(b, n); robot.flush(); }
    got = sondeEcoute(rx, sizeof(rx), ecoute, calme, &premier);
  }
  if (essai || aplomb) {                              // la question de contrôle : un octet attendu, le mode de la liaison
    robot.write((uint8_t)OI_SENSORS);
    robot.write((uint8_t)35);
    nq = sondeEcoute(q, sizeof(q), 80, 15, &premierQ);
    sondeDouteux = (nq != 1);
  }
  if (essai) { sondeEssaiMs = millis(); sondeEssaiFait = true; }
  if (!lire) st.ok = false;                           // état du robot tenu pour inconnu jusqu'à la prochaine lecture complète
  sondeFinMs = millis() + (sondeDouteux ? 60000UL : 3000UL);
  sondeSuspend = true;

  size_t gardes = got < sizeof(rx) ? got : sizeof(rx);
  size_t gardesQ = nq < sizeof(q) ? nq : sizeof(q);
  String j;
  j.reserve(260 + 2 * (n + gardes + gardesQ));
  j += "{\"action\":\""; j += action; j += "\",\"envoye\":\""; sondeHex(j, b, n);
  j += "\",\"recus\":"; j += (unsigned long)got; j += ",\"octets\":\""; sondeHex(j, rx, gardes);
  j += "\",\"premier_ms\":"; j += (unsigned long)premier;
  if (essai || aplomb) {
    j += ",\"question_n\":"; j += (unsigned long)nq; j += ",\"question\":\""; sondeHex(j, q, gardesQ); j += "\"";
  }
  if (essai) {
    j += ",\"roues\":"; j += (int)roues; j += ",\"base\":"; j += (int)base; j += ",\"mode_avant\":"; j += (int)modeAvant;
  }
  j += ",\"douteux\":"; j += sondeDouteux ? "true" : "false"; j += "}";
  if (!lire) {
    String h;
    sondeHex(h, b, n);
    out.printf("Sonde, %s : %u octet(s) envoyé(s) [%s], %lu reçu(s)%s\n", action.c_str(), (unsigned)n, h.c_str(), (unsigned long)got,
               (essai || aplomb) ? (sondeDouteux ? " ; question de contrôle SANS réponse : liaison douteuse" : " ; question de contrôle : bonne") : "");
  }
  http.send(200, "application/json", j);
}
#endif   // CLE_SONDE

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
// v12 : plus compilé par défaut (ESSAI_LIAISON, fichier principal). Avant de le remettre : n'accepter que des ordres
// complets (140 annonce son nombre de notes, 148 et 149 leur nombre de paquets), sinon le robot attend la suite.
#if ESSAI_LIAISON
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
#endif   // ESSAI_LIAISON

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
    if (v >= 10 && v <= RADAR_BUTEE_MAX) {
      radar.butee = (int8_t)v; save = true;
      out.printf("Radar : butée du servo à %d° de chaque côté%s.\n", v, v > RADAR_ZONE_VIVE ? " (au-delà de 30°, rotation lente)" : "");   // v15
    }
    else out.printf("Radar : butée de %d° refusée (de 10 à %d°).\n", v, RADAR_BUTEE_MAX);   // v12
  }
  if (http.hasArg("lent")) {    // v15 : vitesse de la rotation lente au-delà de la zone éprouvée, degrés par seconde
    int v = http.arg("lent").toInt();
    if (v >= RADAR_LENT_MIN && v <= RADAR_LENT_MAX) { radar.lent = (int8_t)v; out.printf("Radar : rotation lente à %d°/s.\n", v); save = true; }
    else out.printf("Radar : vitesse lente de %d°/s refusée (de %d à %d°/s).\n", v, RADAR_LENT_MIN, RADAR_LENT_MAX);
  }
  if (http.hasArg("doux")) radar.doux = http.arg("doux") == "1";   // v16, avant l'angle : le mouvement qui suit se fait lentement d'un bout à l'autre
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
  if (http.hasArg("fige")) {     // v16 : le capteur s'arrête là où il est (bouton « Stop capteur » de la page)
    radar.fixedDeg = radar.servoDeg;
    if (radar.mode != RADAR_FIXED) radar.mode = RADAR_FIXED;
    out.printf("Radar : capteur arrêté à %d°.\n", (int)radar.fixedDeg);
  }
  if (http.hasArg("seuil"))     { radar.seuilCm = (int16_t)constrain(http.arg("seuil").toInt(), 10, 150); out.printf("Radar : seuil d'arrêt %d cm.\n", (int)radar.seuilCm); save = true; }
  if (http.hasArg("securite"))  { radar.securite = http.arg("securite") == "1"; out.printf("Radar : arrêt automatique %s.\n", radar.securite ? "activé" : "désactivé"); save = true; }
  if (http.hasArg("auto"))      { radar.autoFront = http.arg("auto") == "1"; out.printf("Radar : capteur devant pendant une marche avant : %s.\n", radar.autoFront ? "oui" : "non"); save = true; }
  if (http.hasArg("pas"))       { int v = http.arg("pas").toInt(); if (v >= 5 && v <= 45 && v % 5 == 0) { radar.pas = (int8_t)v; save = true; } }
  if (http.hasArg("amplitude")) { int v = http.arg("amplitude").toInt(); if (v >= 20 && v <= RADAR_SPAN_MAX) { radar.amplitude = (int8_t)((v / 5) * 5); save = true; } }
  if (http.hasArg("ech"))       { radar.ech = (int8_t)constrain(http.arg("ech").toInt(), 1, 3); save = true; }
  if (http.hasArg("inv")) {     // v15 : le sens ne se change que capteur droit devant ; tourné de côté, le servo sauterait d'un bord à l'autre
    if (radar.servoDeg != 0) out.printf("Radar : sens du servo inchangé, le capteur est tourné à %d° ; le ramener devant d'abord (angle=0).\n", (int)radar.servoDeg);
    else { radar.inverse = http.arg("inv") == "1"; out.printf("Radar : sens du servo %s.\n", radar.inverse ? "inversé" : "normal"); save = true; }
  }
  if (http.hasArg("effacer"))   radarClearMap();
  if (save) radarSaveSettings();

  String j;
  j.reserve(1400);   // v15 : 37 cases au lieu de 33
  char b[512];
  snprintf(b, sizeof(b),
    "{\"mode\":%u,\"present\":%s,\"absent\":%s,\"following\":%s,\"servo\":%d,\"cible\":%d,\"lent\":%d,\"front_cm\":%.1f,\"front_age\":%lu,"
    "\"seuil\":%d,\"securite\":%s,\"auto\":%s,\"pas\":%d,\"amplitude\":%d,\"butee\":%d,\"ech\":%d,\"inv\":%s,"
    "\"mesures\":%lu,\"sans_echo\":%lu,\"defauts\":%lu,\"passages\":%lu,\"arrets\":%lu,\"refus\":%lu,\"points\":[",
    (unsigned)radar.mode, radar.present ? "true" : "false", radar.absent ? "true" : "false", radar.following ? "true" : "false",
    (int)radar.servoDeg, (int)radar.cibleDeg, (int)radar.lent,   // v15 : direction visée et vitesse de la rotation lente
    radar.frontMm < 0 ? -1.0 : radar.frontMm / 10.0, (unsigned long)(millis() - radar.frontMs),
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
