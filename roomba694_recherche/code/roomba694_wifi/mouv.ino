// mouv.ino — mouvements exécutés par le cerveau lui-même (v10) : « avance de tant » et « tourne de tant ».
//
// Pourquoi : jusqu'à la v9, le PC commandait chaque mouvement à distance (ordre de roues redonné toutes les 0,5 s, arrêt
// décidé par le PC d'après le journal). Le 2026-11-13, un retard du Wi-Fi d'une seconde a fait dépasser une rotation
// de 50°, et le robot, qui tire à gauche de 5 à 13° par mètre, devait s'arrêter pour se redresser (journal_wifi.md
// § 32). Ici le cerveau reçoit un but (une distance, un angle), commande les deux roues séparément 20 fois par seconde,
// tient son cap au gyroscope pendant une avance, ralentit avant le but et s'arrête de lui-même.
//
// Sécurités : celles des flèches et du tour sur place, inchangées.
//   - Refus au départ : robot muet, hors mode Safe, roue soulevée, pare-chocs enfoncé ou choc non dégagé (sauf pour un
//     recul), obstacle devant sous le seuil du capteur de distance (pour une avance), roues déjà en marche, tour sur
//     place en cours.
//   - Arrêt en route : les mêmes causes, plus une durée maximale, plus un robot qui n'avance pas ou ne tourne pas.
//   - Le réflexe pare-chocs (reflexCheck) et l'arrêt du capteur de distance (radarTick) restent actifs pendant le
//     mouvement : s'ils arrêtent les roues, le mouvement se termine.
//   - Toute touche d'arrêt, de roues ou de mode interrompt le mouvement ; /api/mouv?stop=1 aussi.
//   - Bornes : avance de 2 m au plus, recul de 30 cm au plus, rotation de 360° au plus, vitesse plafonnée par
//     SPEED_MM_S (150 mm/s) dans driveDirect comme pour tout ordre de roues.
// Si le Wi-Fi se coupe, le mouvement va à son terme, qui est borné, au lieu de continuer 1,5 s sur le dernier ordre.
//
// /api/mouv?av=MM[&v=MM_S][&cap=DEG]  avance de MM mm (négatif : recul). cap : le cap à tenir est celui du départ plus
//                                     DEG (45° au plus) ; le robot le rejoint en roulant, sans s'arrêter pour pivoter.
// /api/mouv?rot=DEG[&v=MM_S]          rotation sur place de DEG degrés (positif : vers la gauche), roues à v mm/s (100 au plus).
// /api/mouv?stop=1                    arrêt.
// /api/mouv                           état du dernier mouvement en JSON (etat : 0 repos, 1 en cours, 2 terminé, 3 interrompu).
// Les fonctions du fichier principal utilisées ici : driveDirect, wheelsAllowed n'est pas appelée (les mêmes
// vérifications sont faites ici avec leur raison), bumperPressedNow, radarForwardBlocked, radarObstacleAhead, jsonStr.

constexpr uint32_t MOUV_CMD_MS     = 50;        // un ordre de roues toutes les 50 ms (les capteurs du robot sont lus à ce rythme)
constexpr float    MOUV_AV_MAX     = 2000.0f;   // mm
constexpr float    MOUV_RECUL_MAX  = 300.0f;    // mm
constexpr float    MOUV_ROT_MAX    = 360.0f;    // degrés
constexpr float    MOUV_CAP_MAX    = 45.0f;     // degrés : changement de cap accepté pendant une avance
constexpr int16_t  MOUV_V_MIN      = 50;        // mm/s, comme les flèches
constexpr int16_t  MOUV_V_ROT_MAX  = 100;       // mm/s aux roues pendant une rotation : environ 49 °/s
constexpr float    MOUV_KP         = 4.0f;      // mm/s ajoutés à une roue et retirés à l'autre, par degré d'erreur de cap

enum : uint8_t { MOUV_REPOS = 0, MOUV_EN_COURS = 1, MOUV_FINI = 2, MOUV_INTERROMPU = 3 };

struct MouvState {
  uint8_t  etat = MOUV_REPOS;
  bool     rotation = false;
  bool     parti = false;                  // un premier ordre de roues est parti
  float    but = 0;                        // mm (avance, négatif pour un recul) ou degrés (rotation)
  int16_t  vMax = 100;                     // mm/s
  float    cap0 = 0, capCible = 0;         // cap du gyroscope (imu.yawDeg) au départ ; cap à tenir ou à atteindre
  float    dist0 = 0;                      // chemin compté par position.ino au départ
  float    faitMm = 0, faitDeg = 0;
  float    vCmd = 0;                       // dernière vitesse commandée, mm/s
  float    repereMm = 0;                   // pour reconnaître un robot qui n'avance pas
  uint32_t t0 = 0, tFin = 0, dernierOrdreMs = 0, bougeDepuisMs = 0, limiteMs = 0;
  uint32_t numero = 0;                     // compteur de mouvements demandés depuis le démarrage de la carte
  char     raison[96] = "";
} mouv;

bool mouvActive() { return mouv.etat == MOUV_EN_COURS; }

// Fin du mouvement, réussie ou non : roues à l'arrêt.
void mouvEnd(bool ok, const char* raison) {
  if (!mouvActive()) return;
  if (driving) driveDirect(0, 0);
  lastStopMs = millis();
  mouv.tFin = millis();
  mouv.faitDeg = imu.yawDeg - mouv.cap0;
  mouv.faitMm = poseDist() - mouv.dist0;
  mouv.etat = ok ? MOUV_FINI : MOUV_INTERROMPU;
  snprintf(mouv.raison, sizeof(mouv.raison), "%s", raison);
  if (mouv.rotation) out.printf("Mouvement %lu : rotation de %.1f° pour %.1f° demandés, %s. Roues arrêtées.\n",
                                (unsigned long)mouv.numero, mouv.faitDeg, mouv.but, raison);
  else               out.printf("Mouvement %lu : %.0f mm pour %.0f mm demandés, cap %+.1f°, %s. Roues arrêtées.\n",
                                (unsigned long)mouv.numero, mouv.faitMm, mouv.but, mouv.faitDeg, raison);
}

// /api/mouv?av=… ou ?rot=… : vérifie que tout est prêt, puis lance le mouvement (le premier ordre part dans mouvTick).
void mouvStart(bool rotation, float but, int v, float capRel) {
  uint32_t now = millis();
  bool recul = !rotation && but < 0;
  if (mouvActive()) {                      // rien n'est touché : le mouvement en cours continue
    out.println(F("Mouvement refusé : un autre est déjà en cours (5 ou espace pour l'arrêter)."));
    return;
  }
  const char* refus = nullptr;
  if (tourActive())                                         refus = "un tour sur place est en cours";
  else if (!st.ok || now - st.lastOkMs > 1500)              refus = "le robot ne répond pas (CLEAN sur le robot, puis s, puis f)";
  else if (st.mode != OI_MODE_SAFE_LU)                      refus = "le robot n'est pas en mode Safe (touche f)";
  else if (st.bumpsDrops & 0x0C)                            refus = "une roue est soulevée";
  else if (!recul && (bumpLatch || bumperPressedNow()))     refus = "pare-chocs enfoncé ou choc non dégagé : reculer d'abord";
  else if (!imu.present)                                    refus = "le gyroscope est absent";
  else if (driving)                                         refus = "les roues tournent déjà";
  else if (rotation && fabsf(but) < 1.0f)                   refus = "angle trop petit (moins de 1°)";
  else if (!rotation && fabsf(but) < 10.0f)                 refus = "distance trop petite (moins de 10 mm)";
  else if (!rotation && !recul && radarForwardBlocked())    refus = "obstacle devant, sous le seuil du capteur de distance";
  mouv.numero++;
  mouv.rotation = rotation;
  mouv.faitMm = mouv.faitDeg = 0;
  mouv.t0 = mouv.tFin = now;
  if (refus) {
    mouv.but = but;
    mouv.etat = MOUV_INTERROMPU;
    snprintf(mouv.raison, sizeof(mouv.raison), "refusé : %s", refus);
    out.printf("Mouvement %lu refusé : %s.\n", (unsigned long)mouv.numero, refus);
    return;
  }
  if (recul) bumpLatch = false;            // reculer, c'est se dégager : le verrou du choc tombe (comme la flèche du bas)
  if (rotation) {
    mouv.but = constrain(but, -MOUV_ROT_MAX, MOUV_ROT_MAX);
    mouv.vMax = (int16_t)constrain(v, (int)MOUV_V_MIN, (int)MOUV_V_ROT_MAX);
    mouv.limiteMs = (uint32_t)(fabsf(mouv.but) / 15.0f * 1000.0f) + 4000;
  } else {
    mouv.but = constrain(but, -MOUV_RECUL_MAX, MOUV_AV_MAX);
    mouv.vMax = (int16_t)constrain(v, (int)MOUV_V_MIN, (int)SPEED_MM_S);
    mouv.limiteMs = (uint32_t)(fabsf(mouv.but) / 40.0f * 1000.0f) + 4000;
  }
  mouv.cap0 = imu.yawDeg;
  mouv.capCible = mouv.cap0 + (rotation ? mouv.but : constrain(capRel, -MOUV_CAP_MAX, MOUV_CAP_MAX));
  mouv.dist0 = poseDist();
  mouv.repereMm = 0;
  mouv.vCmd = 0;
  mouv.parti = false;
  mouv.dernierOrdreMs = 0;
  mouv.bougeDepuisMs = now;
  mouv.raison[0] = 0;
  mouv.etat = MOUV_EN_COURS;
  if (rotation) out.printf("Mouvement %lu : rotation de %+.1f°, roues à %d mm/s au plus. 5 ou espace pour arrêter.\n",
                           (unsigned long)mouv.numero, mouv.but, (int)mouv.vMax);
  else          out.printf("Mouvement %lu : %s de %.0f mm à %d mm/s au plus, cap tenu à %+.1f° du cap actuel. 5 ou espace pour arrêter.\n",
                           (unsigned long)mouv.numero, recul ? "recul" : "avance", fabsf(mouv.but), (int)mouv.vMax, mouv.capCible - mouv.cap0);
}

// Appelée à chaque passage de la boucle principale.
void mouvTick() {
  if (!mouvActive()) return;
  uint32_t now = millis();
  bool recul  = !mouv.rotation && mouv.but < 0;
  bool avance = !mouv.rotation && mouv.but > 0;
  mouv.faitDeg = imu.yawDeg - mouv.cap0;
  mouv.faitMm = poseDist() - mouv.dist0;
  const char* stop = nullptr;
  if (now - st.lastOkMs > 1500)                    stop = "le robot ne répond plus";
  else if (st.mode != OI_MODE_SAFE_LU)             stop = "le robot a quitté le mode Safe (bord, roue soulevée ou bouton)";
  else if (st.bumpsDrops & 0x0C)                   stop = "roue soulevée";
  else if ((st.bumpsDrops & 0x03) && !recul)       { bumpLatch = true; stop = "pare-chocs touché"; }
  else if (avance && radarObstacleAhead())         stop = "obstacle devant (capteur de distance)";
  else if (mouv.parti && !driving)                 stop = "roues arrêtées par une sécurité ou une touche";
  else if (now - mouv.t0 > mouv.limiteMs)          stop = "durée maximale dépassée";
  if (stop) { mouvEnd(false, stop); return; }
  if (mouv.parti && now - mouv.dernierOrdreMs < MOUV_CMD_MS) return;
  mouv.dernierOrdreMs = now;
  float ecoule = (now - mouv.t0) * 0.001f;

  if (mouv.rotation) {
    float reste = mouv.capCible - imu.yawDeg;                               // signé : positif, il reste à tourner à gauche
    float vit = fabsf(imu.rateDps);
    if (fabsf(reste) <= 0.8f + vit * 0.04f || (reste > 0) != (mouv.but > 0)) { mouvEnd(true, "angle atteint"); return; }
    if (vit > 5.0f || ecoule < 0.8f) mouv.bougeDepuisMs = now;
    else if (now - mouv.bougeDepuisMs > 1500) { mouvEnd(false, "le robot ne tourne pas (roues bloquées ?)"); return; }
    float w = fminf((float)mouv.vMax, fmaxf(22.0f, fabsf(reste) * 3.0f));  // ralentit dans les trente derniers degrés
    w = fminf(w, 30.0f + ecoule * 400.0f);                                  // départ progressif
    int16_t s = (int16_t)lroundf(w);
    if (reste > 0) driveDirect(s, -s); else driveDirect(-s, s);             // (droite, gauche) : droite en avant = vers la gauche
    mouv.vCmd = w;
  } else {
    float reste = fabsf(mouv.but) - mouv.faitMm;
    if (reste <= mouv.vCmd * 0.07f) { mouvEnd(true, "distance atteinte"); return; }
    if (mouv.faitMm - mouv.repereMm > 4.0f || ecoule < 0.8f) { mouv.repereMm = mouv.faitMm; mouv.bougeDepuisMs = now; }
    else if (now - mouv.bougeDepuisMs > 1500) { mouvEnd(false, "le robot n'avance pas (roues bloquées ?)"); return; }
    float v = fminf((float)mouv.vMax, 40.0f + ecoule * 400.0f);            // départ progressif : 400 mm/s²
    v = fminf(v, 45.0f + reste * 1.3f);                                     // ralentit dans les huit derniers centimètres
    float err = mouv.capCible - imu.yawDeg;                                 // positif : il faut tourner à gauche
    float d = constrain(MOUV_KP * err, -0.5f * v, 0.5f * v);               // les deux roues gardent le même sens
    float sens = recul ? -1.0f : 1.0f;
    driveDirect((int16_t)lroundf(sens * v + d), (int16_t)lroundf(sens * v - d));   // (droite, gauche)
    mouv.vCmd = v;
  }
  mouv.parti = true;
}

// Résumé pour /api/state
void mouvStateJson(String& j) {
  char b[96];
  snprintf(b, sizeof(b), "\"mouv\":{\"etat\":%u,\"n\":%lu,\"fait_mm\":%.0f,\"fait_deg\":%.1f},",
           (unsigned)mouv.etat, (unsigned long)mouv.numero, mouv.faitMm, mouv.faitDeg);
  j += b;
}

// Réponse de /api/mouv
void mouvJson(String& j) {
  static const char* const NOMS[] = { "repos", "en cours", "terminé", "interrompu" };
  uint32_t duree = (mouv.etat == MOUV_EN_COURS) ? millis() - mouv.t0 : mouv.tFin - mouv.t0;
  char b[280];
  snprintf(b, sizeof(b), "{\"etat\":%u,\"texte\":\"%s\",\"n\":%lu,\"genre\":\"%s\",\"but\":%.1f,\"fait_mm\":%.0f,\"fait_deg\":%.1f,"
           "\"cap_vise\":%.1f,\"v\":%d,\"duree_ms\":%lu,\"raison\":",
           (unsigned)mouv.etat, NOMS[mouv.etat <= MOUV_INTERROMPU ? mouv.etat : 0], (unsigned long)mouv.numero,
           mouv.rotation ? "rot" : "av", mouv.but, mouv.faitMm, mouv.faitDeg, mouv.capCible - mouv.cap0, (int)mouv.vMax, (unsigned long)duree);
  j += b;
  jsonStr(j, mouv.raison);
  j += "}";
}

void handleMouv() {
  if (http.hasArg("stop")) mouvEnd(false, "arrêt demandé");
  else if (http.hasArg("rot") || http.hasArg("av")) {
    bool rotation = http.hasArg("rot");
    float but = http.arg(rotation ? "rot" : "av").toFloat();
    int v = http.hasArg("v") ? (int)http.arg("v").toInt() : (rotation ? 75 : (int)driveSpeed);
    float capRel = http.hasArg("cap") ? http.arg("cap").toFloat() : 0.0f;
    mouvStart(rotation, but, v, capRel);
  }
  String j;
  j.reserve(360);
  mouvJson(j);
  http.send(200, "application/json", j);
}
