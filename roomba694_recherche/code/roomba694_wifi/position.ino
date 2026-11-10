// position.ino — position du robot (x, y, cap) calculée dans le cerveau : étape 2 de la cartographie
// (notes/H_cartographie_strategie.md). Troisième fichier du sketch : l'outil Arduino le place après le fichier principal
// et carte.ino, avant radar.ino.
// Version du 2026-11-09 : signes vérifiés en rejouant sur le PC l'enregistrement du 2026-11-08 (24 m de pilotage) ;
// premier carré piloté à la main le soir même : le tracé se referme à 4 cm sur 1,79 m (journal_wifi.md § 19), sans
// mesure au sol pour le confirmer.
//
// PRINCIPE : à chaque lecture des capteurs (toutes les 200 ms), les compteurs des deux roues donnent la distance
// parcourue depuis la lecture précédente, et le gyroscope donne la direction du robot. Chaque petit déplacement est
// ajouté dans la direction moyenne entre les deux lectures.
// Le cap vient du gyroscope et non des roues : en tournant, les roues glissent et leurs compteurs se trompent de
// plusieurs degrés par tour. Le cap calculé avec les seules roues est gardé à côté (cap_roues) pour comparer.
// Sans gyroscope, c'est lui qui sert, et la page le signale.
//
// REPÈRE : fixé à la dernière remise à zéro (touche 0, /api/pose?zero=1, bouton de la page ; au démarrage de la carte,
// à la première lecture réussie). x pointe vers l'avant du robot à cet instant, y vers sa gauche. Le cap vaut 0 dans
// cette direction et augmente quand le robot tourne à gauche (même sens que le gyroscope et que l'OI).
// Unités : millimètres et degrés.
//
// LIMITES CONNUES :
//   - les compteurs du Roomba ne savent pas dans quel sens tourne une roue ; le robot le déduit de l'ordre qu'il a
//     reçu. Une roue poussée à la main est donc mal comptée ;
//   - robot soulevé : la position n'a plus de sens. C'est compté (« levés ») et signalé ; remettre à zéro ;
//   - si le robot reste plus de 2 s sans répondre, ou si un compteur fait un saut impossible (le robot remet ses
//     compteurs à zéro en se réveillant), le déplacement correspondant n'est pas compté (« sauts ») ;
//   - le cap dérive lentement avec le gyroscope (quelques degrés en plusieurs minutes) ; rien ne le recale encore.
//     C'est le rôle des murs à l'étape 3.

constexpr float    POSE_MM_PAR_PAS = 0.44456f;   // π × 72 mm de diamètre / 508,8 pas par tour de roue
constexpr float    POSE_VOIE_MM    = 235.0f;     // distance entre les deux roues
constexpr uint32_t POSE_TROU_MS    = 2000;       // au-delà de ce temps sans lecture, le déplacement n'est pas compté...
constexpr int      POSE_PAS_NEGLIGE = 20;        // ... sauf s'il fait moins de 20 pas de compteur (9 mm) par roue
constexpr int      POSE_MAX_PTS    = 800;        // points gardés pour le tracé
constexpr uint16_t POSE_PAS_MM     = 25;         // un point tous les 25 mm au départ ; doublé chaque fois que la mémoire est pleine

struct PoseState {
  float    x = 0, y = 0;         // mm
  float    cap0 = 0;             // cap absolu à la remise à zéro
  float    capAbs = 0;           // cap absolu à la dernière lecture (gyroscope, jamais remis à zéro ; ou roues)
  float    capRoues = 0;         // cap calculé avec les seules roues depuis la remise à zéro
  float    dist = 0;             // mm parcourus, avances et reculs comptés positivement
  bool     sync = false;         // compteurs de référence valides
  int16_t  encL = 0, encR = 0;   // compteurs à la dernière lecture
  uint32_t lastMs = 0;
  bool     gyro = false;         // cap pris sur le gyroscope
  bool     leve = false;         // une roue ne touche pas le sol en ce moment
  uint32_t leves = 0;            // nombre de fois où le robot a été soulevé depuis la remise à zéro
  uint32_t sauts = 0;            // déplacements non comptés depuis la remise à zéro
  int16_t  tx[POSE_MAX_PTS], ty[POSE_MAX_PTS];   // tracé, en mm
  uint16_t n = 0;
  uint16_t pasMm = POSE_PAS_MM;
  uint32_t gen = 1;              // change à chaque remise à zéro et chaque fois que le tracé est éclairci
} pose;

float poseX()    { return pose.x; }
float poseY()    { return pose.y; }
float poseCap()  { return pose.capAbs - pose.cap0; }
float poseCap0() { return pose.cap0; }
// Position utilisable pour placer un obstacle sur la carte (carte.ino) : le robot vient de répondre et il est au sol.
bool  poseFiable() { return pose.sync && !pose.leve && st.ok && millis() - st.lastOkMs < 1500; }

// Ajoute la position actuelle au tracé. Mémoire pleine : on garde un point sur deux et le pas double.
void poseAddPoint() {
  if (pose.n >= POSE_MAX_PTS) {
    uint16_t k = 0;
    for (uint16_t i = 0; i < pose.n; i += 2) { pose.tx[k] = pose.tx[i]; pose.ty[k] = pose.ty[i]; k++; }
    pose.n = k;
    if (pose.pasMm < 6400) pose.pasMm *= 2;
    pose.gen++;
  }
  pose.tx[pose.n] = (int16_t)constrain(lroundf(pose.x), -32000L, 32000L);
  pose.ty[pose.n] = (int16_t)constrain(lroundf(pose.y), -32000L, 32000L);
  pose.n++;
}

// Touche 0, /api/pose?zero=1 : le robot devient le point (0, 0), son avant la direction x, le tracé repart de là.
void poseReset(bool annonce) {
  pose.x = pose.y = 0;
  pose.dist = 0;
  pose.capRoues = 0;
  if (imu.present) pose.capAbs = imu.yawDeg;
  pose.cap0 = pose.capAbs;
  pose.leves = 0;
  pose.sauts = 0;
  pose.n = 0;
  pose.pasMm = POSE_PAS_MM;
  pose.gen++;
  poseAddPoint();
  carteClear(false);   // les obstacles déjà rangés étaient dans l'ancien repère (carte.ino)
  if (annonce) out.println(F("Position remise à zéro : le robot est au point (0, 0), cap 0°, son avant donne la direction x. Carte des obstacles effacée."));
}

// Appelée après chaque lecture réussie des capteurs (pollFinish, fichier principal).
void poseUpdate() {
  uint32_t now = millis();
  float yaw = pollYaw;                                 // cap du gyroscope relevé à l'envoi de la requête
  bool leve = (st.bumpsDrops & 0x0C) != 0;
  if (leve && !pose.leve) pose.leves++;
  pose.leve = leve;
  pose.gyro = imu.present;
  if (!pose.sync) {                                    // première lecture depuis le démarrage de la carte
    pose.sync = true;
    pose.encL = st.encL;
    pose.encR = st.encR;
    pose.lastMs = now;
    if (imu.present) pose.capAbs = yaw;
    pose.cap0 = pose.capAbs;
    poseAddPoint();
    return;
  }
  uint32_t dt = now - pose.lastMs;
  int16_t dL = (int16_t)(st.encL - pose.encL);         // différence sur 16 bits : juste même quand un compteur repasse par zéro
  int16_t dR = (int16_t)(st.encR - pose.encR);
  pose.encL = st.encL;
  pose.encR = st.encR;
  pose.lastMs = now;
  float dl = dL * POSE_MM_PAR_PAS, dr = dR * POSE_MM_PAR_PAS;
  float maxMm = 0.6f * dt + 30.0f;                     // 600 mm/s : au-delà, ce n'est pas un déplacement
  bool petit = abs(dL) <= POSE_PAS_NEGLIGE && abs(dR) <= POSE_PAS_NEGLIGE;   // un pas ou deux après un silence : compté normalement
  if ((dt > POSE_TROU_MS && !petit) || fabsf(dl) > maxMm || fabsf(dr) > maxMm) {
    pose.sauts++;                                      // déplacement inconnu : pas compté
    if (imu.present) pose.capAbs = yaw;                // le cap, lui, reste juste : le gyroscope n'a pas cessé de mesurer
    return;
  }
  float d = (dl + dr) * 0.5f;
  float dCapRoues = (dr - dl) / POSE_VOIE_MM * 57.29578f;
  float capAvant = pose.capAbs;
  float capApres = imu.present ? yaw : capAvant + dCapRoues;
  float milieu = ((capAvant + capApres) * 0.5f - pose.cap0) * 0.01745329f;
  pose.x += d * cosf(milieu);
  pose.y += d * sinf(milieu);
  pose.dist += fabsf(d);
  pose.capRoues += dCapRoues;
  pose.capAbs = capApres;
  if (pose.n == 0) { poseAddPoint(); return; }
  float ex = pose.x - pose.tx[pose.n - 1], ey = pose.y - pose.ty[pose.n - 1];
  if (ex * ex + ey * ey >= (float)pose.pasMm * pose.pasMm) poseAddPoint();
}

// Touche k
void posePrint() {
  out.printf("Position : x %.0f mm, y %.0f mm, cap %.1f° (%s), %.2f m parcourus, à %.0f mm du départ ; 0 pour remettre à zéro\n",
             pose.x, pose.y, poseCap(), pose.gyro ? "gyroscope" : "roues seules, sans gyroscope",
             pose.dist / 1000.0f, sqrtf(pose.x * pose.x + pose.y * pose.y));
  out.printf("  cap d'après les roues seules : %.1f° | robot soulevé %lu fois, %lu déplacement(s) non compté(s) | tracé : %u points, un tous les %u mm\n",
             pose.capRoues, (unsigned long)pose.leves, (unsigned long)pose.sauts, (unsigned)pose.n, (unsigned)pose.pasMm);
}

// Résumé pour /api/state
void poseStateJson(String& j) {
  char b[256];
  snprintf(b, sizeof(b),
           "\"pose\":{\"x\":%.0f,\"y\":%.0f,\"cap\":%.1f,\"cap_roues\":%.1f,\"dist\":%.0f,\"n\":%u,\"gen\":%lu,\"pas\":%u,"
           "\"gyro\":%s,\"leve\":%s,\"leves\":%lu,\"sauts\":%lu},",
           pose.x, pose.y, poseCap(), pose.capRoues, pose.dist, (unsigned)pose.n, (unsigned long)pose.gen, (unsigned)pose.pasMm,
           pose.gyro ? "true" : "false", pose.leve ? "true" : "false", (unsigned long)pose.leves, (unsigned long)pose.sauts);
  j += b;
}

// /api/pose : position et tracé [x, y] en mm. zero=1 remet à zéro. gen et from servent à la page pour ne redemander que
// les points nouveaux : si gen est celui du tracé en cours, seuls les points à partir du numéro from sont renvoyés.
void handlePose() {
  if (http.hasArg("zero")) poseReset(true);
  uint32_t gen  = http.hasArg("gen")  ? strtoul(http.arg("gen").c_str(), nullptr, 10)  : 0;
  uint32_t from = http.hasArg("from") ? strtoul(http.arg("from").c_str(), nullptr, 10) : 0;
  if (gen != pose.gen || from > pose.n) from = 0;
  String j;
  j.reserve(360 + 14 * (pose.n - from));
  char b[320];
  snprintf(b, sizeof(b),
           "{\"x\":%.0f,\"y\":%.0f,\"cap\":%.1f,\"cap_roues\":%.1f,\"dist\":%.0f,\"gyro\":%s,\"leve\":%s,\"leves\":%lu,\"sauts\":%lu,"
           "\"gen\":%lu,\"pas\":%u,\"n\":%u,\"from\":%lu,\"points\":[",
           pose.x, pose.y, poseCap(), pose.capRoues, pose.dist, pose.gyro ? "true" : "false", pose.leve ? "true" : "false",
           (unsigned long)pose.leves, (unsigned long)pose.sauts, (unsigned long)pose.gen, (unsigned)pose.pasMm,
           (unsigned)pose.n, (unsigned long)from);
  j += b;
  for (uint16_t i = (uint16_t)from; i < pose.n; i++) {
    char p[20];
    snprintf(p, sizeof(p), "%s[%d,%d]", i > from ? "," : "", (int)pose.tx[i], (int)pose.ty[i]);
    j += p;
  }
  j += "]}";
  http.send(200, "application/json", j);
}
