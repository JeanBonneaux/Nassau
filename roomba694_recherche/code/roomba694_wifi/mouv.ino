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
// v14 : &brosse=N ajouté à une avance ou à une rotation fait tourner la brosse latérale SEULE, à la puissance N sur 127
//       (plafonnée à BROSSE_LAT_MAX), du premier ordre de roues à la fin du mouvement, quelle que soit cette fin.
//       /api/brosse?lat=N[&ms=T] : la même brosse pendant T ms (5 s au plus, 2 s par défaut), robot immobile, pour régler
//       la puissance ; /api/brosse?lat=0 l'arrête ; /api/brosse seul : son état. Voir brosseLaterale() dans le fichier principal.
// v17 (2026-11-21) : deux ajouts pour rouler sans s'arrêter le long d'un mur. Tous deux ne font rien tant qu'on ne les
//       demande pas : une avance lancée comme avant se déroule exactement comme avant.
//       (1) RETOUCHE D'UNE AVANCE EN COURS : /api/mouv?retouche=1[&cap=DEG][&jusqua=MM][&v=MM_S]
//           cap    : nouveau cap à tenir, relatif au cap du DÉPART de cette avance (borné à ±45° comme au départ) ;
//           jusqua : nouvelle distance totale, comptée depuis le départ de l'avance ; jamais plus de 2 m au-delà du
//                    chemin déjà fait (si le PC se tait, le robot s'arrête donc au plus 2 m plus loin, comme aujourd'hui ;
//                    c'est au PC de ne prolonger que de quelques dizaines de centimètres à la fois), jamais moins que
//                    ce chemin (jusqua = chemin fait : arrêt), 30 m au plus en tout ;
//           v      : nouvelle vitesse maximale (50 à 150 mm/s).
//           Les trois valeurs sont absolues, pas des écarts : une requête rejouée par le Wi-Fi ne change rien.
//           Refusée (rien n'est touché) s'il n'y a pas d'avance en cours ; jamais pour un recul ni une rotation.
//       (2) RALENTISSEMENT SUR LES CAPTEURS OPTIQUES DE DEVANT : &opt=SEUIL ajouté à une avance. Tant que l'un des
//           quatre capteurs optiques de devant du pare-chocs (avant gauche, centre gauche, centre droit, avant droit)
//           lit SEUIL ou plus, et 0,6 s après, la vitesse est plafonnée à 60 mm/s. Le robot ne s'arrête pas pour autant :
//           c'est le pare-chocs qui arrête. Utile quand le capteur de distance regarde de côté : plus rien d'autre ne
//           surveille l'avant. Le 2026-11-15, 7 contacts sur 17 étaient annoncés par une lecture de 100 ou plus, une
//           seconde avant (notes/P_capteurs_en_direct.md § 2) ; au repos ces capteurs lisent 0 à 50.
// Les fonctions du fichier principal utilisées ici : driveDirect, wheelsAllowed n'est pas appelée (les mêmes
// vérifications sont faites ici avec leur raison), bumperPressedNow, radarForwardBlocked, radarObstacleAhead, jsonStr.

constexpr uint32_t MOUV_CMD_MS     = 50;        // un ordre de roues toutes les 50 ms (les capteurs du robot sont lus à ce rythme)
constexpr float    MOUV_CHAINE_MAX = 30000.0f;  // v17 : mm, longueur totale d'une avance prolongée par des retouches
constexpr int16_t  MOUV_V_OPTIQUE  = 60;        // v17 : mm/s, vitesse plafonnée quand un capteur optique de devant voit quelque chose
constexpr uint32_t MOUV_OPT_TENUE_MS = 600;     // v17 : le plafond tient ce temps après la dernière lecture au-dessus du seuil
constexpr int      MOUV_OPT_MIN    = 40;        // v17 : seuil le plus bas accepté (au repos ces capteurs lisent jusqu'à 50)
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
  int8_t   brosse = 0;                     // v14 : puissance de la brosse latérale demandée pour ce mouvement (0 : arrêtée)
  uint32_t retouches = 0;                  // v17 : retouches acceptées pendant cette avance
  int16_t  optSeuil = 0;                   // v17 : seuil des capteurs optiques de devant pour cette avance (0 : pas de ralentissement)
  uint16_t optMax = 0;                     // v17 : plus forte lecture de ces capteurs pendant l'avance
  uint32_t optDernierMs = 0;               // v17 : date de la dernière lecture au-dessus du seuil (0 : aucune)
  uint32_t optRalentis = 0;                // v17 : nombre d'ordres de roues donnés à vitesse plafonnée
  char     raison[96] = "";
} mouv;

bool mouvActive() { return mouv.etat == MOUV_EN_COURS; }

// Fin du mouvement, réussie ou non : roues à l'arrêt.
void mouvEnd(bool ok, const char* raison) {
  if (!mouvActive()) return;
  if (driving) driveDirect(0, 0);
  if (brosseLat) brosseLaterale(0);        // v14 : la brosse latérale ne survit jamais au mouvement qui l'a demandée
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
  // v17 : une ligne de plus, seulement si l'avance a été retouchée ou surveillée par les capteurs optiques
  if (!mouv.rotation && (mouv.retouches || mouv.optSeuil))
    out.printf("Mouvement %lu : %lu retouche(s) ; capteurs optiques de devant : seuil %d, plus forte lecture %u, %lu ordre(s) de roues ralenti(s).\n",
               (unsigned long)mouv.numero, (unsigned long)mouv.retouches, (int)mouv.optSeuil, (unsigned)mouv.optMax, (unsigned long)mouv.optRalentis);
}

// /api/mouv?av=… ou ?rot=… : vérifie que tout est prêt, puis lance le mouvement (le premier ordre part dans mouvTick).
void mouvStart(bool rotation, float but, int v, float capRel, int brosse, int opt) {
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
  mouv.brosse = 0;
  mouv.retouches = 0;                      // v17
  mouv.optSeuil = 0;
  mouv.optMax = 0;
  mouv.optDernierMs = 0;
  mouv.optRalentis = 0;
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
  mouv.brosse = (int8_t)constrain(brosse, 0, BROSSE_LAT_MAX);
  if (brosseLat) brosseLaterale(0);        // une impulsion en cours s'arrête ici : pendant un mouvement, la brosse ne dépend que de lui
  // v17 : ralentissement sur les capteurs optiques de devant, pour une avance seulement et seulement si on le demande
  mouv.optSeuil = (!rotation && !recul && opt > 0) ? (int16_t)constrain(opt, MOUV_OPT_MIN, 4095) : 0;
  mouv.etat = MOUV_EN_COURS;
  if (mouv.optSeuil) out.printf("Mouvement %lu : vitesse plafonnée à %d mm/s tant qu'un capteur optique de devant lit %d ou plus.\n",
                                (unsigned long)mouv.numero, (int)MOUV_V_OPTIQUE, (int)mouv.optSeuil);
  if (mouv.brosse) out.printf("Mouvement %lu : brosse latérale seule à %d sur 127 pendant ce mouvement.\n", (unsigned long)mouv.numero, (int)mouv.brosse);
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
  if (!mouv.parti && mouv.brosse) { brosseFinMs = 0; brosseLaterale(mouv.brosse); }   // v14 : mise en marche avec le premier ordre de roues, une seule fois
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
    if (mouv.optSeuil > 0 && !recul) {                                      // v17 : capteurs optiques de devant (avG, cG, cD, avD)
      uint16_t m = max(max(st.light[1], st.light[2]), max(st.light[3], st.light[4]));
      if (m > mouv.optMax) mouv.optMax = m;
      if (m >= (uint16_t)mouv.optSeuil) mouv.optDernierMs = now ? now : 1;
      if (mouv.optDernierMs && now - mouv.optDernierMs < MOUV_OPT_TENUE_MS && v > (float)MOUV_V_OPTIQUE) {
        v = (float)MOUV_V_OPTIQUE;                                          // quelque chose devant : on continue, mais doucement
        mouv.optRalentis++;
      }
    }
    float err = mouv.capCible - imu.yawDeg;                                 // positif : il faut tourner à gauche
    float d = constrain(MOUV_KP * err, -0.5f * v, 0.5f * v);               // les deux roues gardent le même sens
    float sens = recul ? -1.0f : 1.0f;
    driveDirect((int16_t)lroundf(sens * v + d), (int16_t)lroundf(sens * v - d));   // (droite, gauche)
    mouv.vCmd = v;
  }
  mouv.parti = true;
}

// v17 : retouche d'une avance en cours (voir l'en-tête). Renvoie nullptr si elle est prise, sinon la raison du refus ;
// en cas de refus rien n'est touché. Appelée depuis la boucle principale (handleMouv), comme mouvTick : pas de concurrence.
const char* mouvRetouche(bool aCap, float capRel, bool aBut, float jusqua, bool aV, int v) {
  if (!mouvActive() || mouv.rotation || mouv.but <= 0) return "aucune avance en cours";
  uint32_t now = millis();
  if (aCap) mouv.capCible = mouv.cap0 + constrain(capRel, -MOUV_CAP_MAX, MOUV_CAP_MAX);
  if (aV)   mouv.vMax = (int16_t)constrain(v, (int)MOUV_V_MIN, (int)SPEED_MM_S);
  if (aBut) {
    float fait = poseDist() - mouv.dist0;
    if (fait < 0) fait = 0;
    float b = constrain(jusqua, fait, fminf(fait + MOUV_AV_MAX, MOUV_CHAINE_MAX));   // jamais plus de 2 m au-delà du chemin fait
    if (b < 1.0f) b = 1.0f;                                                            // le but reste positif : c'est une avance
    mouv.but = b;
    mouv.limiteMs = (now - mouv.t0) + (uint32_t)((b - fait) / 40.0f * 1000.0f) + 4000;
  }
  mouv.retouches++;
  return nullptr;
}

// Résumé pour /api/state
void mouvStateJson(String& j) {
  char b[192];
  snprintf(b, sizeof(b), "\"mouv\":{\"etat\":%u,\"n\":%lu,\"fait_mm\":%.0f,\"fait_deg\":%.1f,"
                         "\"but\":%.0f,\"cap_vise\":%.1f,\"v\":%d,\"ret\":%lu,\"opt\":%u},",   // v17 : but, cap visé, vitesse, retouches, plus forte lecture optique
           (unsigned)mouv.etat, (unsigned long)mouv.numero, mouv.faitMm, mouv.faitDeg,
           mouv.but, mouv.capCible - mouv.cap0, (int)mouv.vMax, (unsigned long)mouv.retouches, (unsigned)mouv.optMax);
  j += b;
}

// Réponse de /api/mouv
void mouvJson(String& j) {
  static const char* const NOMS[] = { "repos", "en cours", "terminé", "interrompu" };
  uint32_t duree = (mouv.etat == MOUV_EN_COURS) ? millis() - mouv.t0 : mouv.tFin - mouv.t0;
  char b[400];
  snprintf(b, sizeof(b), "{\"etat\":%u,\"texte\":\"%s\",\"n\":%lu,\"genre\":\"%s\",\"but\":%.1f,\"fait_mm\":%.0f,\"fait_deg\":%.1f,"
           "\"cap_vise\":%.1f,\"v\":%d,\"duree_ms\":%lu,\"brosse\":%d,"
           "\"retouches\":%lu,\"opt_seuil\":%d,\"opt_max\":%u,\"opt_ralentis\":%lu,\"raison\":",   // v17
           (unsigned)mouv.etat, NOMS[mouv.etat <= MOUV_INTERROMPU ? mouv.etat : 0], (unsigned long)mouv.numero,
           mouv.rotation ? "rot" : "av", mouv.but, mouv.faitMm, mouv.faitDeg, mouv.capCible - mouv.cap0, (int)mouv.vMax, (unsigned long)duree,
           (int)mouv.brosse,
           (unsigned long)mouv.retouches, (int)mouv.optSeuil, (unsigned)mouv.optMax, (unsigned long)mouv.optRalentis);
  j += b;
  jsonStr(j, mouv.raison);
  j += "}";
}

void handleMouv() {
  const char* retoucheRefus = nullptr;     // v17
  if (http.hasArg("stop")) mouvEnd(false, "arrêt demandé");
  else if (http.hasArg("retouche")) {      // v17 : retouche de l'avance en cours ; ne lance jamais un mouvement
    bool aCap = http.hasArg("cap"), aBut = http.hasArg("jusqua"), aV = http.hasArg("v");
    float capRel = aCap ? http.arg("cap").toFloat() : 0.0f;
    float jusqua = aBut ? http.arg("jusqua").toFloat() : 0.0f;
    if (!isfinite(capRel) || !isfinite(jusqua)) {
      http.send(400, "text/plain; charset=utf-8", "valeur refusée : cap et jusqua doivent être des nombres finis");
      return;
    }
    retoucheRefus = mouvRetouche(aCap, capRel, aBut, jusqua, aV, aV ? (int)http.arg("v").toInt() : 0);
  }
  else if (http.hasArg("rot") || http.hasArg("av")) {
    bool rotation = http.hasArg("rot");
    float but = http.arg(rotation ? "rot" : "av").toFloat();
    int v = http.hasArg("v") ? (int)http.arg("v").toInt() : (rotation ? 75 : (int)driveSpeed);
    float capRel = http.hasArg("cap") ? http.arg("cap").toFloat() : 0.0f;
    // v12 : « nan » et « inf » se lisent comme des nombres qui n'en sont pas. Toute comparaison avec « nan » est fausse :
    // il passait les contrôles de distance, la borne de 2 m ne s'appliquait plus, et l'avance n'était reconnue ni comme
    // une avance ni comme un recul (plus d'arrêt du capteur de distance). Vu le 2026-11-14 : /api/mouv?av=nan répondait
    // « but : nan » (mouvement refusé ce jour-là pour une autre raison, robot endormi).
    if (!isfinite(but) || !isfinite(capRel)) {
      http.send(400, "text/plain; charset=utf-8", "valeur refusée : av, rot et cap doivent être des nombres finis");
      return;
    }
    int brosse = http.hasArg("brosse") ? (int)http.arg("brosse").toInt() : 0;   // v14 : brosse latérale seule pendant ce mouvement
    int opt = http.hasArg("opt") ? (int)http.arg("opt").toInt() : 0;            // v17 : ralentissement sur les capteurs optiques de devant
    mouvStart(rotation, but, v, capRel, brosse, opt);
  }
  String j;
  j.reserve(520);
  mouvJson(j);
  if (http.hasArg("retouche")) {           // v17 : la réponse dit si la retouche a été prise
    j.remove(j.length() - 1);              // l'accolade fermante de mouvJson
    j += ",\"retouche\":";
    jsonStr(j, retoucheRefus ? retoucheRefus : "prise");
    j += "}";
  }
  http.send(200, "application/json", j);
}

// ---------- Brosse latérale seule, robot immobile (v14) ----------
// Résumé pour /api/state
void brosseStateJson(String& j) {
  char b[80];
  snprintf(b, sizeof(b), "\"brosse\":{\"lat\":%d,\"max\":%d,\"marches\":%lu},", (int)brosseLat, BROSSE_LAT_MAX, (unsigned long)brosseMarches);
  j += b;
}

// /api/brosse?lat=N[&ms=T] : une impulsion, pour régler la puissance sous les yeux de l'utilisateur. Refusée si le robot
// est muet, hors du mode Safe, une roue soulevée, s'il bouge (la brosse se demande alors avec le mouvement) ou pendant une
// sonde. /api/brosse?lat=0 : arrêt. Sans argument : l'état.
void handleBrosse() {
  const char* refus = nullptr;
  uint32_t now = millis();
  if (http.hasArg("lat")) {
    int n = (int)http.arg("lat").toInt();
    long ms = http.hasArg("ms") ? http.arg("ms").toInt() : 2000L;
    ms = constrain(ms, 200L, (long)BROSSE_IMPULSION_MAX_MS);
    if (n <= 0) {
      if (brosseLat) { brosseLaterale(0); out.println(F("Brosse latérale arrêtée.")); }
    }
    else if (!st.ok || now - st.lastOkMs > 1500)        refus = "le robot ne répond pas (CLEAN sur le robot, puis s, puis f)";
    else if (st.mode != OI_MODE_SAFE_LU)                refus = "le robot n'est pas en mode Safe (touche f)";
    else if (st.bumpsDrops & 0x0C)                      refus = "une roue est soulevée";
    else if (driving || mouvActive() || tourActive())   refus = "le robot bouge : demander la brosse avec le mouvement (&brosse=N)";
    else if (sondeActive())                             refus = "une sonde est en cours";
    else {
      brosseLaterale(n);
      brosseFinMs = now + (uint32_t)ms;
      if (brosseFinMs == 0) brosseFinMs = 1;
      out.printf("Brosse latérale seule à %d sur 127 pendant %ld ms (impulsion, robot immobile).\n", (int)brosseLat, ms);
    }
    if (refus) out.printf("Brosse latérale refusée : %s.\n", refus);
  }
  long reste = (brosseLat && brosseFinMs) ? (long)(int32_t)(brosseFinMs - millis()) : 0L;
  String j;
  j.reserve(200);
  char b[120];
  snprintf(b, sizeof(b), "{\"lat\":%d,\"max\":%d,\"reste_ms\":%ld,\"marches\":%lu,\"refus\":",
           (int)brosseLat, BROSSE_LAT_MAX, reste > 0 ? reste : 0L, (unsigned long)brosseMarches);
  j += b;
  jsonStr(j, refus ? refus : "");
  j += "}";
  http.send(200, "application/json", j);
}
