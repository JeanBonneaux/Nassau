// tour.ino — « tour sur place » : le robot tourne sur lui-même pendant que le capteur de distance regarde droit devant.
// Chaque mesure est rangée avec le cap du gyroscope à l'instant du tir : on obtient la distance des obstacles tout
// autour du robot, une mesure tous les 3° environ, sans dépendre du servo (dont la course est limitée par ses fils).
// Un mur vu de face renvoie un écho net : dans la courbe distance / direction, chaque mur donne un creux à fond plat,
// dont le fond est la distance du mur et le milieu sa direction (première brique de la cartographie, note H à venir).
// Quatrième fichier du sketch : l'outil Arduino le place après radar.ino et avant web.ino.
// Version du 2026-11-09, écrite après les premiers essais du radar ; PAS ENCORE ESSAYÉE avec le robot en mouvement.
//
// DÉROULEMENT : touche 't' ou /api/tour?go=1.
//   1. Préparation (1,5 s) : capteur à 0° en mode fixe, biais du gyroscope remesuré robot immobile, cap remis à zéro.
//   2. Rotation vers la gauche à 30 °/s (roue droite +62 mm/s, roue gauche -62 mm/s), jusqu'à 380° d'après le gyroscope :
//      un tour complet plus 20° de recouvrement, pour vérifier que la fin du tour retrouve le début.
//   3. Arrêt des roues ; le radar reprend le mode qu'il avait. Les mesures restent disponibles par /api/tour.
//
// SÉCURITÉ : rotation seule, jamais de translation. Le tour est refusé si le robot ne répond pas, n'est pas en mode
// Safe, si une roue est soulevée, le pare-chocs enfoncé, le gyroscope absent ou les roues déjà en mouvement.
// Il s'arrête tout de suite si : le pare-chocs est touché, une roue se soulève, le robot ne répond plus ou quitte le
// mode Safe, le gyroscope ne voit pas la rotation (robot bloqué) ou la voit trop rapide, le capteur ne réagit plus,
// la durée maximale est dépassée, une touche de roues ou d'arrêt arrive (5, espace, 8, 2, 4, 6…), une mise à jour
// commence. L'ordre de roues est répété toutes les 300 ms : si cette boucle cessait de tourner, le garde-fou de 1,5 s
// du fichier principal couperait les roues. Limite connue : si la carte perd son alimentation pendant la rotation,
// le robot garde son dernier ordre et continue de tourner ; il suffit alors de le soulever ou d'appuyer sur CLEAN.

void jsonStr(String& o, const char* s);        // défini dans web.ino

constexpr float    TOUR_RATE_DPS   = 30.0f;    // vitesse de rotation visée
constexpr int16_t  TOUR_WHEEL_MM_S = 62;       // 30 °/s × 117,5 mm (demi-voie : 235 mm entre les roues du Roomba)
constexpr float    TOUR_TOTAL_DEG  = 380.0f;   // un tour complet plus 20° de recouvrement
constexpr uint32_t TOUR_PREP_MS    = 1500;     // servo en place, calibration du gyroscope (1 s)
constexpr uint32_t TOUR_MAX_MS     = 30000;    // durée maximale de la rotation (380° à 30 °/s : 12,7 s)
constexpr uint32_t TOUR_CMD_MS     = 300;      // période de répétition de l'ordre de roues
constexpr int      TOUR_MAX_PTS    = 256;      // 380° à 3° par mesure : 127 mesures
constexpr uint8_t  OI_MODE_SAFE_LU = 3;        // valeur du paquet 35 lue sur ce 694 en mode Safe (décalée de +1, voir journal_tests.md)

enum : uint8_t { TOUR_REPOS = 0, TOUR_PREPARE = 1, TOUR_TOURNE = 2, TOUR_FINI = 3, TOUR_INTERROMPU = 4 };

struct TourState {
  volatile uint8_t  etat = TOUR_REPOS;
  volatile bool     mesure = false;        // vrai pendant la rotation : la tâche radar range ses mesures ici
  volatile uint16_t n = 0;                 // nombre de mesures rangées
  volatile float    cap0 = 0;              // cap du gyroscope au début de la rotation
  int16_t  deg10[TOUR_MAX_PTS];            // direction du tir, en dixièmes de degré depuis le départ (positif = vers la gauche)
  int16_t  mm[TOUR_MAX_PTS];               // distance en mm (0 = rien à portée)
  uint32_t t0 = 0, tRot = 0, tFin = 0, dernierOrdreMs = 0, lentDepuisMs = 0;
  float    tourne = 0;                     // rotation accomplie, degrés
  int      prochainMsgDeg = 90;
  uint8_t  modeRadarAvant = 0;
  char     raison[112] = "";
} tour;

bool tourActive()   { return tour.etat == TOUR_PREPARE || tour.etat == TOUR_TOURNE; }
bool tourSampling() { return tour.mesure; }

// Appelée par la tâche radar pour chaque mesure faite pendant la rotation : cap au moment du tir et distance.
void tourSample(float capDeg, int16_t mm) {
  if (!tour.mesure) return;
  uint16_t i = tour.n;
  if (i >= TOUR_MAX_PTS) return;
  long d = lroundf((capDeg - tour.cap0) * 10.0f);
  tour.deg10[i] = (int16_t)constrain(d, -32000L, 32000L);
  tour.mm[i] = mm;
  tour.n = i + 1;                          // l'indice n'avance qu'une fois la mesure écrite
}

// Fin du tour, réussie ou non : roues à l'arrêt, radar remis dans son mode d'avant.
void tourEnd(bool ok, const char* raison) {
  if (!tourActive()) return;
  tour.mesure = false;
  if (tour.etat == TOUR_TOURNE || driving) driveDirect(0, 0);
  tour.tFin = millis();
  if (tour.etat == TOUR_PREPARE) tour.tRot = tour.tFin;
  tour.etat = ok ? TOUR_FINI : TOUR_INTERROMPU;
  snprintf(tour.raison, sizeof(tour.raison), "%s", raison);
  radar.mode = tour.modeRadarAvant;
  if (ok) out.printf("Tour sur place terminé : %.0f° en %.1f s, %u mesures. Roues arrêtées.\n",
                     tour.tourne, (tour.tFin - tour.tRot) / 1000.0f, (unsigned)tour.n);
  else    out.printf("Tour sur place interrompu après %.0f° : %s. Roues arrêtées.\n", tour.tourne, raison);
}

// Touche 't' ou /api/tour?go=1 : vérifie que tout est prêt, puis lance la préparation.
void tourStart() {
  if (tourActive()) { out.println(F("Tour sur place : déjà en cours (5 ou espace pour l'arrêter).")); return; }
  const char* refus = nullptr;
  if (!st.ok || millis() - st.lastOkMs > 2000) refus = "le robot ne répond pas (CLEAN sur le robot, puis s, puis f)";
  else if (st.mode != OI_MODE_SAFE_LU)         refus = "le robot n'est pas en mode Safe (touche f)";
  else if (st.bumpsDrops & 0x0C)               refus = "une roue est soulevée";
  else if (st.bumpsDrops & 0x03)               refus = "le pare-chocs est enfoncé";
  else if (!imu.present)                       refus = "le gyroscope est absent";
  else if (driving)                            refus = "les roues tournent déjà";
  if (refus) {
    tour.etat = TOUR_INTERROMPU;
    tour.tourne = 0;
    tour.tRot = tour.tFin = millis();
    snprintf(tour.raison, sizeof(tour.raison), "refusé : %s", refus);
    out.printf("Tour sur place refusé : %s.\n", refus);
    return;
  }
  tour.modeRadarAvant = radar.mode;
  radar.fixedDeg = 0;
  radar.mode = RADAR_FIXED;               // capteur droit devant, dix mesures par seconde
  imu.calibRequested = true;              // biais du gyroscope remesuré pendant 1 s, cap remis à zéro
  tour.n = 0;
  tour.tourne = 0;
  tour.mesure = false;
  tour.raison[0] = 0;
  tour.prochainMsgDeg = 90;
  tour.t0 = millis();
  tour.etat = TOUR_PREPARE;
  out.println(F("Tour sur place : préparation, ne pas toucher le robot (capteur droit devant, gyroscope recalé pendant 1 s)."));
}

// Appelée à chaque passage de la boucle principale.
void tourTick() {
  if (!tourActive()) return;
  uint32_t now = millis();
  const char* stop = nullptr;
  if (now - st.lastOkMs > 2500)            stop = "le robot ne répond plus";
  else if (st.mode != OI_MODE_SAFE_LU)     stop = "le robot a quitté le mode Safe (bord, roue soulevée ou bouton)";
  else if (st.bumpsDrops & 0x03)           stop = "pare-chocs touché";
  else if (st.bumpsDrops & 0x0C)           stop = "roue soulevée";
  else if (radar.absent)                   stop = "le capteur de distance ne réagit pas";
  if (stop) { tourEnd(false, stop); return; }

  if (tour.etat == TOUR_PREPARE) {
    if (imu.calibRequested || imu.calibrating || now - tour.t0 < TOUR_PREP_MS) {
      if (now - tour.t0 > 5000) tourEnd(false, "le gyroscope ne termine pas sa calibration");
      return;
    }
    tour.cap0 = imu.yawDeg;
    tour.n = 0;
    tour.tRot = now;
    tour.lentDepuisMs = now;
    tour.etat = TOUR_TOURNE;
    tour.mesure = true;
    driveDirect(TOUR_WHEEL_MM_S, -TOUR_WHEEL_MM_S);   // roue droite en avant, roue gauche en arrière : rotation vers la gauche
    tour.dernierOrdreMs = now;
    out.printf("Tour sur place : rotation vers la gauche à %.0f °/s (roues à %d mm/s). 5 ou espace pour arrêter.\n",
               TOUR_RATE_DPS, (int)TOUR_WHEEL_MM_S);
    return;
  }

  tour.tourne = imu.yawDeg - tour.cap0;
  float vitesse = fabsf(imu.rateDps);
  if (tour.tourne >= TOUR_TOTAL_DEG)       { tourEnd(true, "tour complet"); return; }
  if (now - tour.tRot > TOUR_MAX_MS)       { tourEnd(false, "durée maximale dépassée"); return; }
  if (vitesse > 90.0f)                     { tourEnd(false, "rotation trop rapide"); return; }
  if (tour.n >= TOUR_MAX_PTS)              { tourEnd(false, "mémoire des mesures pleine"); return; }
  if (vitesse > 8.0f) tour.lentDepuisMs = now;
  else if (now - tour.lentDepuisMs > 2000) { tourEnd(false, "le robot ne tourne pas (roues bloquées ?)"); return; }
  if (now - tour.dernierOrdreMs >= TOUR_CMD_MS) {
    driveDirect(TOUR_WHEEL_MM_S, -TOUR_WHEEL_MM_S);
    tour.dernierOrdreMs = now;
  }
  if (tour.tourne >= tour.prochainMsgDeg) {
    out.printf("Tour sur place : %d° (%u mesures).\n", tour.prochainMsgDeg, (unsigned)tour.n);
    tour.prochainMsgDeg += 90;
  }
}

// Résumé pour /api/state
void tourStateJson(String& j) {
  char b[64];
  snprintf(b, sizeof(b), "\"tour\":{\"etat\":%u,\"tourne\":%.0f,\"n\":%u},", (unsigned)tour.etat, tour.tourne, (unsigned)tour.n);
  j += b;
}

// Réponse de /api/tour : état, rotation accomplie, raison de l'arrêt et mesures [dixièmes de degré, mm]
void tourJson(String& j) {
  static const char* const NOMS[] = { "repos", "préparation", "rotation", "terminé", "interrompu" };
  uint16_t n = tour.n;
  uint32_t duree = 0;
  if (tour.etat == TOUR_TOURNE) duree = millis() - tour.tRot;
  else if (tour.etat == TOUR_FINI || tour.etat == TOUR_INTERROMPU) duree = tour.tFin - tour.tRot;
  char b[200];
  snprintf(b, sizeof(b), "{\"etat\":%u,\"texte\":\"%s\",\"tourne\":%.1f,\"n\":%u,\"duree_ms\":%lu,\"vitesse\":%.0f,\"total\":%.0f,\"raison\":",
           (unsigned)tour.etat, NOMS[tour.etat <= TOUR_INTERROMPU ? tour.etat : 0], tour.tourne, (unsigned)n,
           (unsigned long)duree, TOUR_RATE_DPS, TOUR_TOTAL_DEG);
  j += b;
  jsonStr(j, tour.raison);
  j += ",\"points\":[";
  for (uint16_t i = 0; i < n; i++) {
    char p[24];
    snprintf(p, sizeof(p), "%s[%d,%d]", i ? "," : "", (int)tour.deg10[i], (int)tour.mm[i]);
    j += p;
  }
  j += "]}";
}
