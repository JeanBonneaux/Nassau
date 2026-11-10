// carte.ino — carte des obstacles vus par le capteur de distance, tenue dans le cerveau : premier pas de l'étape 3 de
// la cartographie (notes/H_cartographie_strategie.md). Deuxième fichier du sketch (ordre alphabétique : après le
// fichier principal, avant position.ino).
// Version du 2026-11-09 : écrite avec la nouvelle page de pilotage ; PAS ENCORE comparée à une pièce mesurée.
//
// PRINCIPE : à chaque écho du capteur de distance, la tâche radar connaît la distance, la direction du capteur (angle
// du servo) et le cap du robot à l'instant du tir (gyroscope). Avec la position du robot (position.ino), cela donne
// l'endroit de la pièce où se trouve l'obstacle : un point (x, y) en millimètres, dans le même repère que la position.
// Les points sont gardés dans un anneau (les 1500 derniers) et servis par /api/carte ; la page les dessine autour du
// tracé du robot, en vue de dessus ou en 3D. Un tour sur place dessine ainsi le contour de la pièce vu de cet endroit.
//
// LIMITES CONNUES :
//   - le capteur entend dans un cône large : un mur donne un arc de points, pas un trait net (journal_wifi.md § 16) ;
//   - la position dérive (rien ne la recale encore) : deux passages au même endroit ne se superposent pas exactement ;
//   - le décalage du capteur par rapport au centre du robot n'est pas mesuré : réglage « dx » (mm vers l'avant), 0 par
//     défaut, /api/carte?dx=N ;
//   - rien n'est rangé quand la position n'est pas fiable (robot muet ou soulevé) ni au-delà de 3 m ;
//   - remettre la position à zéro efface la carte : l'ancien repère n'existe plus.

constexpr int     CARTE_MAX_PTS   = 1500;
constexpr int16_t CARTE_MIN_MM    = 40;     // en dessous, le capteur ne mesure pas bien
constexpr int16_t CARTE_MAX_MM    = 3000;   // au-delà, la direction de l'écho est trop incertaine pour faire un point
constexpr int     CARTE_PROCHE_MM = 30;     // un écho à moins de 30 mm d'un des 12 derniers points n'est pas rangé de nouveau
constexpr int     CARTE_PAR_REPONSE = 400;  // points par réponse de /api/carte, au plus

struct CarteState {
  int16_t  x[CARTE_MAX_PTS], y[CARTE_MAX_PTS];   // mm ; le point numéro k est dans la case k % CARTE_MAX_PTS
  volatile uint32_t total = 0;      // points rangés depuis le dernier effacement
  volatile uint32_t gen = 1;        // change à chaque effacement
  volatile int16_t  dxMm = 0;       // capteur en avant (+) ou en arrière (-) du centre du robot
  volatile uint32_t ecartes = 0;    // échos non rangés parce que la position n'était pas fiable
} carte;

void carteSetup() {
  prefs.begin("carte", true);
  carte.dxMm = (int16_t)constrain(prefs.getInt("dx", 0), -250, 250);
  prefs.end();
}

void carteClear(bool annonce) {
  carte.total = 0;
  carte.ecartes = 0;
  carte.gen = carte.gen + 1;
  if (annonce) out.println(F("Carte des obstacles effacée."));
}

// Appelée par la tâche radar (second cœur) après chaque mesure réussie. capAbs : cap du gyroscope à l'instant du tir
// (imu.yawDeg) ; servoDeg : direction du capteur, 0 = devant, positif = gauche ; mm : distance mesurée.
void carteAdd(float capAbs, int servoDeg, int16_t mm) {
  if (mm < CARTE_MIN_MM || mm > CARTE_MAX_MM) return;
  if (!poseFiable()) { carte.ecartes = carte.ecartes + 1; return; }
  float capRobot = (imu.present ? capAbs - poseCap0() : poseCap()) * 0.01745329f;
  float capTir = capRobot + servoDeg * 0.01745329f;
  float dx = carte.dxMm;
  float x = poseX() + dx * cosf(capRobot) + mm * cosf(capTir);
  float y = poseY() + dx * sinf(capRobot) + mm * sinf(capTir);
  if (fabsf(x) > 32000.0f || fabsf(y) > 32000.0f) return;
  uint32_t t = carte.total;
  uint32_t recents = t < 12 ? t : 12;
  for (uint32_t k = 1; k <= recents; k++) {            // même obstacle revu sans que rien ait bougé : inutile de le ranger encore
    uint32_t i = (t - k) % CARTE_MAX_PTS;
    float ex = x - carte.x[i], ey = y - carte.y[i];
    if (ex * ex + ey * ey < (float)CARTE_PROCHE_MM * CARTE_PROCHE_MM) return;
  }
  uint32_t i = t % CARTE_MAX_PTS;
  carte.x[i] = (int16_t)lroundf(x);
  carte.y[i] = (int16_t)lroundf(y);
  carte.total = t + 1;                                 // le compteur n'avance qu'une fois le point écrit
}

// Résumé pour /api/state
void carteStateJson(String& j) {
  char b[96];
  snprintf(b, sizeof(b), "\"carte\":{\"total\":%lu,\"gen\":%lu,\"dx\":%d},",
           (unsigned long)carte.total, (unsigned long)carte.gen, (int)carte.dxMm);
  j += b;
}

// /api/carte : points [x, y] en mm. effacer=1 vide la carte ; dx=N règle le décalage du capteur (-250 à 250 mm, gardé
// en mémoire). gen et from servent à la page pour ne redemander que les points nouveaux : from est le nombre de points
// qu'elle a déjà reçus de cette génération. La réponse donne « from » (numéro du premier point renvoyé) et « total ».
void handleCarte() {
  if (http.hasArg("effacer")) carteClear(true);
  if (http.hasArg("dx")) {
    int v = http.arg("dx").toInt();
    if (v >= -250 && v <= 250) {
      carte.dxMm = (int16_t)v;
      prefs.begin("carte", false);
      prefs.putInt("dx", v);
      prefs.end();
      out.printf("Carte : capteur de distance compté à %d mm en avant du centre du robot.\n", v);
    }
  }
  uint32_t gen  = http.hasArg("gen")  ? strtoul(http.arg("gen").c_str(), nullptr, 10)  : 0;
  uint32_t from = http.hasArg("from") ? strtoul(http.arg("from").c_str(), nullptr, 10) : 0;
  uint32_t total = carte.total;
  uint32_t garde = total < (uint32_t)CARTE_MAX_PTS ? total : (uint32_t)CARTE_MAX_PTS;
  uint32_t premier = total - garde;                    // plus ancien point encore en mémoire
  if (gen != carte.gen || from > total || from < premier) from = premier;
  uint32_t fin = total;
  if (fin - from > (uint32_t)CARTE_PAR_REPONSE) fin = from + CARTE_PAR_REPONSE;
  String j;
  j.reserve(160 + 14 * (fin - from));
  char b[160];
  snprintf(b, sizeof(b), "{\"gen\":%lu,\"total\":%lu,\"from\":%lu,\"dx\":%d,\"ecartes\":%lu,\"points\":[",
           (unsigned long)carte.gen, (unsigned long)total, (unsigned long)from, (int)carte.dxMm, (unsigned long)carte.ecartes);
  j += b;
  for (uint32_t k = from; k < fin; k++) {
    uint32_t i = k % CARTE_MAX_PTS;
    char p[20];
    snprintf(p, sizeof(p), "%s[%d,%d]", k > from ? "," : "", (int)carte.x[i], (int)carte.y[i]);
    j += p;
  }
  j += "]}";
  http.send(200, "application/json", j);
}
