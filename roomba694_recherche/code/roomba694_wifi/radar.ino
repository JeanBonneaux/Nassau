// radar.ino — « radar » à ultrasons : capteur HC-SR04 monté sur un servo SG90 (modules du kit ELEGOO de l'utilisateur).
// Troisième fichier du sketch roomba694_wifi : l'outil Arduino le concatène après roomba694_wifi.ino et avant web.ino
// (ordre alphabétique), il voit donc tout ce que définit le fichier principal (out, prefs, stopWheels, driving...).
// Version 3 — préparé le 2026-11-09, essayé sur le matériel le soir même (journal_wifi.md § 14 ; notes/G_radar_ultrason_servo.md).
// Depuis la version 5, chaque écho est aussi placé dans la pièce par carteAdd() (carte.ino).
// Relu et corrigé le même jour, avant tout essai : rappel interne vers la masse sur l'entrée Echo, et capteur maintenu
// devant tant qu'une avance est demandée (voir radarForwardBlocked et radarTask).
//
// CÂBLAGE (détail et dessin sur la photo de la plaque : notes/G_radar_ultrason_servo.md). Les deux modules marchent en
// 5 V. Décision de l'utilisateur du 2026-11-09 : ce 5 V est pris sur la broche VIN de la carte (environ 4,7 V quand la
// carte est alimentée par son USB : le 5 V de l'USB moins la diode de la carte), par un fil qu'il pose lui-même jusqu'à
// la ligne rouge de la bande d'alimentation libre, du côté VIN de la plaque ; la ligne bleue de cette bande est reliée
// à la masse. Tous les signaux sont du côté 3V3 de la carte, dans le trou libre à côté de chaque broche.
// Jamais ce 5 V sur 3V3, ni sur la ligne rouge du côté 3V3 (3,3 V de la carte et du gyroscope).
//   HC-SR04 : Vcc -> ligne 5 V ; Gnd -> masse ; Trig <- D19 (GPIO19) ;
//             Echo -> 1 kΩ -> D23 (GPIO23), et 2 kΩ de D23 vers la masse : diviseur qui ramène l'Echo (≈ 4,7 V) à ≈ 3,1 V.
//             L'Echo sort du 5 V : JAMAIS directement sur une broche de l'ESP32.
//   SG90    : fil brun -> masse ; fil rouge -> ligne 5 V ; fil orange (signal) <- D18 (GPIO18).
//   Un condensateur de 100 à 470 µF entre la ligne 5 V et la masse (patte longue au 5 V), près du servo, amortit ses
//   appels de courant (jusqu'à 250 mA en mouvement, 650 mA bloqué). Ce courant traverse la prise USB et la diode de la
//   carte : si la carte redémarre avec la raison « baisse de tension » quand le servo bouge, c'est lui.
//   (Première version du 2026-11-09 : D27 / D32 / D34 côté VIN, abandonnée faute de trous libres de ce côté.)
//
// FONCTIONNEMENT : une tâche sur le second cœur (comme le gyroscope) pilote le servo (PWM 50 Hz par LEDC, sans
// bibliothèque) et le capteur (impulsion Trig de 10 µs, durée de l'écho mesurée par interruption sur Echo) ; rien ne
// bloque la boucle principale ni la liaison robot. Trois modes :
//   arrêt     servo ramené au centre puis relâché (plus d'impulsions : il ne force pas, ne vibre pas, ne consomme rien) ;
//   fixe      le capteur regarde dans une direction choisie (0 = devant) et mesure 10 fois par seconde ;
//   balayage  de -amplitude à +amplitude par pas de « pas » degrés, aller puis retour (~2 s par passage à ±60°, pas 10°).
// Les mesures remplissent une carte polaire (une case tous les 5°, de -90° à +90° depuis la v15) servie par /api/radar et
// dessinée sur la page web. Angle 0 = droit devant, positif = vers la gauche (anti-horaire, comme l'angle de l'OI et le cap gyro).
// v15 : au-delà de ±30° le servo tourne lentement, degré par degré (voir RADAR_ZONE_VIVE et la tâche radar) ; capteur
// tourné de côté, plus rien ne surveille l'avant que le pare-chocs du robot (limite déjà notée plus bas pour le mode fixe).
// Distance = durée de l'écho × 0,1715 mm/µs (son à 343 m/s, aller-retour). Portée utile du HC-SR04 : 2 cm à 4 m,
// cône de 15° environ ; les surfaces molles (rideaux, canapés) et très obliques renvoient peu d'écho.
//
// SÉCURITÉ (option « arrêt auto », active par défaut) : la distance « devant » est la médiane des trois dernières mesures
// du secteur ±15° (contre les mesures parasites). Si elle est sous le seuil (30 cm par défaut) et récente (< 1,5 s),
// la boucle principale arrête les roues quand le robot avance et refuse les ordres d'avance ; reculer et tourner restent
// possibles. En balayage, dès qu'une avance est demandée et pendant toute la marche avant, le capteur se place devant
// et mesure à 10 Hz (option « devant en marche avant ») ; il y reste 1 s après le dernier ordre d'avance, puis reprend
// le balayage : sinon le secteur avant ne serait revu qu'une fois par passage (~2 s, soit 30 cm parcourus à 150 mm/s),
// et un refus d'avancer expirerait tout seul pendant que l'on maintient le bouton.
// Limites connues : en mode fixe orienté ailleurs que devant, rien ne surveille l'avant ; au premier ordre d'avance en
// balayage, le robot peut parcourir quelques centimètres avant que le capteur ne soit revenu devant ; en balayage, la
// médiane mélange trois directions voisines (-10°, 0°, +10° au pas de 10°). Le pare-chocs du robot reste la vraie
// sécurité : le capteur, posé sur le dessus du robot, ne voit ni les obstacles bas (pieds de chaise) ni les surfaces
// absorbantes.
// La tâche n'écrit jamais sur la console ni vers le robot (réservés à la boucle principale) : elle pose des valeurs et
// des compteurs que radarTick(), la console ('u') et les pages lisent.

constexpr int PIN_SERVO = 18;   // D18 : signal du servo SG90 (fil orange)
constexpr int PIN_TRIG  = 19;   // D19 : Trig du HC-SR04 (3,3 V suffisent pour le déclencher)
constexpr int PIN_ECHO  = 23;   // D23 : Echo du HC-SR04 à travers le diviseur 1 kΩ / 2 kΩ (le 2 kΩ vers GND tient la broche à 0 V au repos ; rappel interne en plus, voir radarSetup)

constexpr int      RADAR_SPAN_MAX   = 90;                                       // degrés de part et d'autre du centre (taille de la carte polaire ; 80 jusqu'à la v14)
// v12 : plafond de la butée du servo, écrit dans le code. Les fils du capteur sont courts : l'utilisateur a fixé la butée
// à 30° le 2026-11-09. Jusqu'à la v11 ce n'était qu'un réglage en mémoire : /api/radar?butee=80 le relevait, et une mémoire
// effacée redonnait 80°.
// v15 (2026-11-21) : le plafond passe à 90°, à la demande de l'utilisateur, pour lire les murs de côté en roulant (« on peut
// aussi essayer le capteur de distance qui tourne de 90 degrés. Pas besoin de photo, fais-le. L'important, c'est que si ça
// tourne, ça doit tourner très doucement »). Deux garde-fous vont avec :
//   - la butée réglée (radar.butee) reste à 30° tant qu'on ne la relève pas par /api/radar?butee=N : installer la v15 ne
//     change rien à ce que fait le servo ;
//   - hors de la zone éprouvée depuis le 9 novembre (RADAR_ZONE_VIVE, ±30°), le servo n'avance que d'un degré à la fois, à
//     radar.lent degrés par seconde (5 par défaut, 10 au plus) : voir la tâche radar.
constexpr int      RADAR_BUTEE_MAX  = 90;
constexpr int      RADAR_ZONE_VIVE  = 30;                                       // v15 : en deçà, le servo saute d'une direction à l'autre comme avant ; au-delà, rotation lente
constexpr int      RADAR_LENT_DEFAUT = 5;                                       // v15 : vitesse de la rotation lente, degrés par seconde
constexpr int      RADAR_LENT_MIN   = 1;
constexpr int      RADAR_LENT_MAX   = 10;
constexpr int      RADAR_SLOT_DEG   = 5;                                        // résolution de la carte polaire
constexpr int      RADAR_SLOTS      = 2 * RADAR_SPAN_MAX / RADAR_SLOT_DEG + 1;  // 37 cases, de -90° à +90° (33 cases, de -80° à +80°, jusqu'à la v14)
constexpr int      RADAR_FRONT_DEG  = 15;                                       // secteur « devant » pour la sécurité
constexpr uint32_t RADAR_SETTLE_MS  = 80;                                       // repos du servo après un pas, plus 2 ms par degré parcouru
constexpr uint32_t RADAR_PING_MS    = 60;                                       // intervalle minimal entre deux mesures (fiche HC-SR04)
constexpr uint32_t RADAR_FIXED_MS   = 100;                                      // période des mesures en mode fixe et en suivi (10 Hz)
constexpr uint32_t RADAR_FRESH_MS   = 1500;                                     // âge maximal d'une distance « devant » pour la sécurité
constexpr uint32_t RADAR_HOLD_MS    = 1000;                                     // le capteur reste devant ce temps après le dernier ordre d'avance (la page le répète toutes les 400 ms)
constexpr uint32_t ECHO_MAX_US      = 25000;                                    // écho plus long : rien à portée (4,3 m aller-retour)
constexpr int      US_MIN_MM        = 20;                                       // en dessous, le capteur ne mesure pas : on plafonne
constexpr int      US_FAR_MM        = 4000;                                     // valeur « rien à portée » dans les calculs
constexpr uint32_t SERVO_CENTER_US  = 1500;                                     // impulsion du centre (à ajuster si le « devant » est de travers)
constexpr float    SERVO_US_PER_DEG = 10.0f;                                    // SG90 : environ 500 µs à 0°, 2500 µs à 180°

enum : uint8_t { RADAR_OFF = 0, RADAR_FIXED = 1, RADAR_SWEEP = 2 };

struct RadarState {
  volatile uint8_t  mode = RADAR_OFF;
  volatile bool     present = false;      // au moins un écho reçu depuis le démarrage
  volatile bool     absent = false;       // cinq mesures de suite sans réaction du capteur (Echo jamais monté)
  volatile bool     following = false;    // balayage interrompu : capteur devant (marche avant demandée ou en cours)
  // Réglages, conservés en mémoire flash (espace « radar ») :
  volatile int16_t  seuilCm = 30;         // distance d'arrêt automatique
  volatile bool     securite = true;      // arrêt auto et refus d'avancer vers un obstacle
  volatile bool     autoFront = true;     // en balayage, regarder devant pendant une marche avant
  volatile int8_t   pas = 10;             // pas du balayage, degrés
  volatile int8_t   amplitude = 60;       // demi-ouverture du balayage, degrés
  volatile int8_t   ech = 1;              // mesures par direction (1 à 3, médiane)
  volatile bool     inverse = false;      // vrai si le servo part à droite quand on lui demande la gauche (montage à l'envers)
  volatile int8_t   butee = RADAR_ZONE_VIVE;  // butée du servo, degrés de part et d'autre du centre : aucun ordre ne la dépasse (voir radarLimit) ; v15 : 30° tant qu'on ne la relève pas
  volatile int8_t   lent = RADAR_LENT_DEFAUT; // v15 : vitesse de la rotation lente hors de la zone éprouvée, degrés par seconde
  volatile int8_t   fixedDeg = 0;         // direction visée en mode fixe
  // État :
  volatile int8_t   servoDeg = 0;         // direction actuelle du capteur (v15 : elle avance degré par degré pendant une rotation lente)
  volatile int8_t   cibleDeg = 0;         // v15 : direction vers laquelle le servo se rend (égale à servoDeg une fois arrivé)
  // v16 : « doux » est posé par /api/radar?doux=1 (la page de pilotage) : le prochain mouvement du servo se fait au pas
  // lent d'un bout à l'autre, même à l'intérieur de ±30°. La tâche radar le lève quand ce mouvement est arrivé.
  volatile bool     doux = false;
  volatile bool     enLent = false;       // v16 : un mouvement lent est en cours (copie de l'état de la tâche radar, pour tour.ino)
  volatile int16_t  frontMm = -1;         // distance devant : > 0 mm, 0 = rien à portée, -1 = inconnue
  volatile uint32_t frontMs = 0;          // date de cette distance
  volatile int16_t  lastMm = -1;          // dernière mesure, quelle que soit sa direction : > 0 mm, 0 = rien à portée, -1 = aucune
  volatile int8_t   lastDeg = 0;          // direction du capteur pour cette mesure
  volatile uint32_t lastMs = 0;           // date de cette mesure
  volatile uint32_t sweeps = 0, pings = 0, noEcho = 0, faults = 0, stops = 0, refused = 0;
  volatile int16_t  mm[RADAR_SLOTS];      // carte : > 0 distance en mm, 0 = rien à portée, -1 = jamais mesuré
  volatile uint32_t ms[RADAR_SLOTS];      // date de chaque case
} radar;
portMUX_TYPE radarMux = portMUX_INITIALIZER_UNLOCKED;
// Dernier ordre d'avance reçu (touche 8), accepté ou refusé : posé par radarForwardBlocked() dans la boucle principale,
// lu par la tâche radar pour garder le capteur devant tant que l'on demande à avancer.
volatile uint32_t radarFwdMs = 0;
volatile bool     radarFwdSeen = false;

// Butée du servo, en degrés de part et d'autre du centre (réglage « butee », 10 à RADAR_BUTEE_MAX, conservé en flash).
// Ajoutée le 2026-11-09 à la demande de l'utilisateur, dont les fils du capteur sont courts : tout angle demandé y est
// ramené, que l'ordre vienne du balayage, du mode fixe, de l'API ou du dessin touché sur la page.
int radarLimit() { return constrain((int)radar.butee, 10, RADAR_BUTEE_MAX); }   // v12 : jamais au-delà du plafond du code

// v15 : dernière direction commandée au servo, gardée dans la mémoire RTC de la carte. Cette mémoire survit à un
// redémarrage (mise à jour, baisse de tension, plantage) mais pas à une coupure de l'alimentation. Sans elle, une carte
// qui redémarre pendant que le capteur regarde de côté le ramènerait devant d'un coup, à pleine vitesse. Une clé liée à la
// valeur écarte une mémoire jamais écrite ou abîmée.
constexpr uint32_t SERVO_MEMO_CLE = 0x5E12A0C3;
RTC_NOINIT_ATTR uint32_t servoMemoCle;
RTC_NOINIT_ATTR int32_t  servoMemoDeg;
void servoMemoEcrit(int deg) { servoMemoDeg = deg; servoMemoCle = SERVO_MEMO_CLE ^ (uint32_t)(deg + 128); }
int  servoMemoLit() {            // 0 : rien de valable, ou capteur devant
  if (esp_reset_reason() == ESP_RST_POWERON) return 0;   // mise sous tension : la mémoire RTC ne contient rien de sûr
  int d = servoMemoDeg;
  if (d < -RADAR_BUTEE_MAX || d > RADAR_BUTEE_MAX) return 0;
  return (servoMemoCle == (SERVO_MEMO_CLE ^ (uint32_t)(d + 128))) ? d : 0;
}
volatile int8_t radarRetourDemarrage = 0;   // direction retrouvée au démarrage, pour le message de radarTick (0 : rien à dire)

// ---------- Servo SG90 par LEDC (50 Hz, 16 bits : 20 000 µs sur 65 535 pas, soit 0,3 µs de résolution) ----------
bool servoOn = false;        // impulsions en cours
bool servoRelaxed = true;    // position mécanique incertaine après un relâchement

void servoPulse(uint32_t us) {
  if (!servoOn) { ledcAttach(PIN_SERVO, 50, 16); servoOn = true; }
  ledcWrite(PIN_SERVO, (uint32_t)((uint64_t)us * 65535 / 20000));
}

void servoRelax() {           // plus d'impulsions : le servo garde sa position sans forcer et ne consomme presque rien
  if (servoOn) ledcWrite(PIN_SERVO, 0);
  servoRelaxed = true;
}

// v15 : impulsion pour la direction deg (0 devant, positif à gauche), bornée au plafond du code et non à la butée réglée :
// si l'on abaisse la butée pendant que le capteur est au-delà, il doit pouvoir revenir degré par degré, sans saut.
// Tient à jour la direction courante et sa copie en mémoire RTC. N'est appelée que par servoGoto et par la tâche radar.
void servoEcrit(int deg) {
  deg = constrain(deg, -RADAR_BUTEE_MAX, RADAR_BUTEE_MAX);
  int mech = radar.inverse ? -deg : deg;
  servoPulse((uint32_t)(SERVO_CENTER_US + mech * SERVO_US_PER_DEG));   // ±90° : 600 à 2400 µs
  servoRelaxed = false;
  radar.servoDeg = (int8_t)deg;
  servoMemoEcrit(deg);
}

// Oriente le capteur vers deg d'un seul saut. Renvoie l'ampleur du mouvement en degrés (pour l'attente).
// v15 : la tâche radar ne l'appelle que si le départ et l'arrivée sont dans la zone éprouvée (RADAR_ZONE_VIVE).
int servoGoto(int deg) {
  int lim = radarLimit();
  deg = constrain(deg, -lim, lim);   // jamais au-delà de la butée
  int moved = servoRelaxed ? 2 * RADAR_SPAN_MAX : abs(deg - (int)radar.servoDeg);
  servoEcrit(deg);
  return moved;
}

// ---------- HC-SR04 : durée de l'écho mesurée par interruption ----------
volatile uint32_t echoRiseUs = 0, echoFallUs = 0;
volatile uint8_t  echoPhase = 0;   // 0 : attente du front montant, 1 : attente du front descendant, 2 : mesure prête

void ARDUINO_ISR_ATTR echoIsr() {
  uint32_t now = micros();
  if (digitalRead(PIN_ECHO)) { if (echoPhase == 0) { echoRiseUs = now; echoPhase = 1; } }
  else if (echoPhase == 1) { echoFallUs = now; echoPhase = 2; }
}

// Une mesure (tâche radar, 1 à 40 ms). Renvoie la distance en mm, 0 si rien à portée, -1 si le capteur ne réagit pas
// (Echo jamais monté : capteur absent, non alimenté, Trig ou diviseur débranché).
int16_t usPing() {
  uint32_t t0 = millis();
  while (digitalRead(PIN_ECHO) && millis() - t0 < 200) vTaskDelay(1);   // certains clones tiennent Echo haut ~200 ms sans écho
  echoPhase = 0;
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  uint32_t start = micros();
  for (;;) {
    uint8_t ph = echoPhase;
    if (ph == 2) break;
    uint32_t el = micros() - start;
    if (ph == 0 && el > 10000) return -1;              // 10 ms sans front montant (normal : ~0,5 ms) : le capteur ne réagit pas
    if (ph == 1 && el > ECHO_MAX_US + 2000) return 0;  // écho toujours en cours : rien à portée
    vTaskDelay(1);
  }
  uint32_t dur = echoFallUs - echoRiseUs;
  if (dur > ECHO_MAX_US) return 0;
  int32_t mm = (int32_t)(dur * 0.1715f);               // 343 m/s, aller-retour : 1 µs = 0,1715 mm
  if (mm < US_MIN_MM) mm = US_MIN_MM;
  if (mm >= US_FAR_MM) return 0;
  return (int16_t)mm;
}

// Combine 1 à 3 mesures : médiane des valeurs utilisables (« rien à portée » compté comme 4 m) ; avec deux valeurs,
// la plus courte (prudence) ; -1 si aucune n'est utilisable.
int16_t usCombine(const int16_t* v, int n) {
  int16_t a[3];
  int k = 0;
  for (int i = 0; i < n && k < 3; i++) if (v[i] >= 0) a[k++] = v[i] ? v[i] : US_FAR_MM;
  if (k == 0) return -1;
  for (int i = 1; i < k; i++) for (int j = i; j > 0 && a[j - 1] > a[j]; j--) { int16_t t = a[j]; a[j] = a[j - 1]; a[j - 1] = t; }
  int16_t m = (k == 3) ? a[1] : a[0];
  return (m >= US_FAR_MM) ? 0 : m;
}

// ---------- Tâche radar (second cœur) ----------
// v15 — ROTATION LENTE. Tant que le départ et l'arrivée d'un mouvement sont dans la zone éprouvée (±RADAR_ZONE_VIVE), rien
// ne change : le servo saute à sa cible et on attend qu'il se pose. Dès que l'un des deux est au-delà, le mouvement entier
// se fait degré par degré, à radar.lent degrés par seconde, et il reste lent jusqu'à l'arrivée, même une fois revenu dans
// la zone. La cible est relue à chaque degré : un nouvel ordre (autre angle, mode arrêt, butée abaissée) est pris tout de
// suite, sans attendre la fin du mouvement en cours. Une mesure est faite à chaque degré, rangée avec la direction réelle
// du capteur : on voit le capteur répondre pendant qu'il tourne, et un fil arraché se lit aussitôt (« absent »).
// En mode arrêt le servo revient au centre de la même façon avant d'être relâché.
void radarTask(void*) {
  int16_t  ring[3] = { -1, -1, -1 };   // trois dernières mesures du secteur avant
  uint8_t  ringIdx = 0, faultStreak = 0, lastMode = 255;
  int      dir = 1, angle = -radar.amplitude;
  uint32_t lastPingMs = 0, dernierPasMs = 0;
  bool     lent = false;               // v15 : un mouvement lent est en cours
  int memo = servoMemoLit();
  if (abs(memo) > RADAR_ZONE_VIVE) {
    // v15 : la carte a redémarré alors que le capteur regardait de côté ; le servo y est resté. On lui redonne la même
    // consigne (il ne bouge pas) et la boucle le ramène devant lentement, puisque le mode est « arrêt ».
    servoEcrit(memo);
    radarRetourDemarrage = (int8_t)memo;
  } else {
    servoGoto(0);                      // signe de vie au démarrage : le servo se centre, puis se relâche
    vTaskDelay(pdMS_TO_TICKS(600));
    servoRelax();
  }
  for (;;) {
    uint8_t mode = radar.mode;
    if (mode != lastMode) {
      lastMode = mode;
      radar.following = false;
    }
    if (mode == RADAR_OFF && servoRelaxed) { radar.cibleDeg = 0; radar.enLent = false; vTaskDelay(pdMS_TO_TICKS(100)); continue; }   // arrêt, servo déjà au centre et relâché

    int  lim = radarLimit();
    int  pas = constrain((int)radar.pas, 5, 45);
    int  amp = constrain((int)radar.amplitude, 5, lim);                             // le balayage ne dépasse pas la butée
    // Capteur devant pendant la marche avant, et aussi tant que l'avance est demandée (bouton maintenu), même refusée :
    // sinon le balayage reprendrait dès l'arrêt automatique, la mesure « devant » vieillirait, le refus expirerait au
    // bout de 1,5 s et le robot s'approcherait de l'obstacle par à-coups.
    uint32_t fwdMs = radarFwdMs;                                                   // lu avant millis() : l'âge ne peut pas être négatif
    bool wanted = radarFwdSeen && (millis() - fwdMs) < RADAR_HOLD_MS;
    bool follow = (mode == RADAR_SWEEP) && radar.autoFront && (driveForward || wanted);
    radar.following = follow;
    bool fixed = (mode == RADAR_FIXED) || follow;
    int  target;
    if (mode == RADAR_OFF) target = 0;                                              // v15 : arrêt = retour au centre, puis relâchement
    else if (mode == RADAR_FIXED) target = tourSampling() ? 0 : constrain((int)radar.fixedDeg, -lim, lim);   // tour sur place : droit devant
    else if (follow) target = 0;
    else {
      angle = constrain(angle, -amp, amp);                                          // réglages changés en route : on reste dans la plage
      angle = ((angle + (angle >= 0 ? pas / 2 : -pas / 2)) / pas) * pas;            // et sur un multiple du pas
      target = constrain(angle, -amp, amp);                                         // l'arrondi ne doit pas faire sortir de la plage
    }
    radar.cibleDeg = (int8_t)target;

    // ---- Mouvement du servo (v15) ----
    int cur = radar.servoDeg;
    if (servoRelaxed && abs(target) > RADAR_ZONE_VIVE) {                            // servo relâché (il l'est toujours au centre) et cible de côté :
      int moved = servoGoto(0);                                                     // on le reprend au centre avant de partir lentement
      vTaskDelay(pdMS_TO_TICKS(RADAR_SETTLE_MS + 2 * moved));
      cur = 0;
      dernierPasMs = millis();
    }
    if (cur != target && (lent || radar.doux || abs(cur) > RADAR_ZONE_VIVE || abs(target) > RADAR_ZONE_VIVE)) {   // v16 : ou mouvement demandé « doux »
      lent = true;                                                                  // un degré vers la cible, pas plus
      uint32_t pasMs = 1000 / (uint32_t)constrain((int)radar.lent, RADAR_LENT_MIN, RADAR_LENT_MAX);
      uint32_t ecoule = millis() - dernierPasMs;
      if (ecoule < pasMs) vTaskDelay(pdMS_TO_TICKS(pasMs - ecoule));
      servoEcrit(cur + (target > cur ? 1 : -1));
      dernierPasMs = millis();
      vTaskDelay(pdMS_TO_TICKS(25));                                                // le temps d'une période du servo (20 ms) avant de mesurer
    } else {
      int moved = servoGoto(target);
      if (moved) vTaskDelay(pdMS_TO_TICKS(RADAR_SETTLE_MS + 2 * moved));         // SG90 : ~0,1 s pour 60°, puis stabilisation
    }
    int  ici = radar.servoDeg;                                                      // direction réelle du capteur pour la mesure qui suit
    bool arrive = (ici == target);
    if (arrive) {
      if (lent) radar.doux = false;                                                 // v16 : la demande « doux » ne vaut que pour le mouvement qui vient de finir
      lent = false;
    }
    radar.enLent = lent;
    if (mode == RADAR_OFF) {                                                        // arrêt : pas de mesure ; une fois au centre, on relâche
      if (arrive) { vTaskDelay(pdMS_TO_TICKS(500)); servoRelax(); }
      continue;
    }

    uint32_t period = fixed ? RADAR_FIXED_MS : RADAR_PING_MS;
    uint32_t since = millis() - lastPingMs;
    if (since < period) vTaskDelay(pdMS_TO_TICKS(period - since));

    int n = (tourSampling() || !arrive) ? 1 : constrain((int)radar.ech, 1, 3);   // tour sur place ou servo en route : une mesure par direction
    float capTir = imu.yawDeg;                                      // cap du gyroscope à l'instant du tir
    int16_t v[3];
    for (int k = 0; k < n; k++) {
      if (k) vTaskDelay(pdMS_TO_TICKS(RADAR_PING_MS));
      v[k] = usPing();
      lastPingMs = millis();
      radar.pings = radar.pings + 1;
      if (v[k] == 0) radar.noEcho = radar.noEcho + 1;
      if (v[k] < 0)  radar.faults = radar.faults + 1;
    }
    int16_t res = usCombine(v, n);
    // v15 : chaque mesure est rangée avec la direction réelle du capteur (ici), qui n'est plus toujours la cible.
    if (res >= 0 && mode == RADAR_FIXED && ici == 0) tourSample(capTir, res);   // rangée seulement pendant un tour sur place (tour.ino), capteur droit devant
    if (res >= 0) { radar.lastMm = res; radar.lastDeg = (int8_t)ici; radar.lastMs = millis(); }
    if (res > 0) carteAdd(capTir, ici, res);                        // obstacle placé dans la pièce (carte.ino)
    if (res < 0) {
      if (faultStreak < 255) faultStreak++;
      if (faultStreak >= 5) radar.absent = true;
    } else {
      faultStreak = 0;
      radar.absent = false;
      radar.present = true;
      int idx = constrain((ici + RADAR_SPAN_MAX + RADAR_SLOT_DEG / 2) / RADAR_SLOT_DEG, 0, RADAR_SLOTS - 1);
      portENTER_CRITICAL(&radarMux);
      radar.mm[idx] = res;
      radar.ms[idx] = millis();
      portEXIT_CRITICAL(&radarMux);
      if (abs(ici) <= RADAR_FRONT_DEG) {
        ring[ringIdx] = res;
        ringIdx = (ringIdx + 1) % 3;
        int16_t rv[3] = { ring[0], ring[1], ring[2] };
        int16_t m = usCombine(rv, 3);
        if (m >= 0) { radar.frontMm = m; radar.frontMs = millis(); }
      }
    }
    if (!fixed && arrive) {                                                        // balayage : case suivante, demi-tour aux extrémités (v15 : une fois la case atteinte)
      if (angle + dir * pas > amp || angle + dir * pas < -amp) { dir = -dir; radar.sweeps = radar.sweeps + 1; }
      angle = constrain(angle + dir * pas, -amp, amp);
    }
  }
}

// ---------- Réglages en mémoire flash ----------
void radarLoadSettings() {
  prefs.begin("radar", true);
  radar.seuilCm   = constrain(prefs.getInt("seuil", 30), 10, 150);
  radar.securite  = prefs.getBool("sec", true);
  radar.autoFront = prefs.getBool("auto", true);
  radar.pas       = constrain(prefs.getInt("pas", 10), 5, 45);
  radar.amplitude = constrain(prefs.getInt("amp", 60), 5, RADAR_SPAN_MAX);
  radar.ech       = constrain(prefs.getInt("ech", 1), 1, 3);
  radar.inverse   = prefs.getBool("inv", false);
  radar.butee     = constrain(prefs.getInt("max", RADAR_ZONE_VIVE), 10, RADAR_BUTEE_MAX);   // v15 : mémoire vide -> 30° (la zone éprouvée), jamais le plafond
  radar.lent      = constrain(prefs.getInt("lent", RADAR_LENT_DEFAUT), RADAR_LENT_MIN, RADAR_LENT_MAX);   // v15
  prefs.end();
}

void radarSaveSettings() {
  prefs.begin("radar", false);
  prefs.putInt("seuil", radar.seuilCm);
  prefs.putBool("sec", radar.securite);
  prefs.putBool("auto", radar.autoFront);
  prefs.putInt("pas", radar.pas);
  prefs.putInt("amp", radar.amplitude);
  prefs.putInt("ech", radar.ech);
  prefs.putBool("inv", radar.inverse);
  prefs.putInt("max", radar.butee);
  prefs.putInt("lent", radar.lent);   // v15
  prefs.end();
}

// ---------- Appels depuis la boucle principale, la console et les pages ----------
void radarSetup() {
  pinMode(PIN_TRIG, OUTPUT);
  digitalWrite(PIN_TRIG, LOW);
  pinMode(PIN_ECHO, INPUT_PULLDOWN);   // rappel interne (~45 kΩ) vers la masse : entrée calme tant que rien n'est câblé, sans effet sur le diviseur
  for (int i = 0; i < RADAR_SLOTS; i++) { radar.mm[i] = -1; radar.ms[i] = 0; }
  radarLoadSettings();
  attachInterrupt(digitalPinToInterrupt(PIN_ECHO), echoIsr, CHANGE);
  xTaskCreatePinnedToCore(radarTask, "radar", 4096, nullptr, 1, nullptr, 0);   // second cœur, comme le gyroscope
  out.printf("Radar à ultrasons : servo sur D%d, Trig sur D%d, Echo sur D%d (diviseur 1 k / 2 k) ; mode arrêt, 'r' ou la page web pour l'activer.\n",
             PIN_SERVO, PIN_TRIG, PIN_ECHO);
}

const char* radarModeName(uint8_t m) { return m == RADAR_SWEEP ? "balayage" : m == RADAR_FIXED ? "fixe" : "arrêt"; }

void radarSetMode(uint8_t m) {
  radar.mode = m;
  if (m == RADAR_FIXED)      out.printf("Radar : mode fixe, capteur vers %d° (0 = devant, positif = gauche), 10 mesures/s.\n", (int)radar.fixedDeg);
  else if (m == RADAR_SWEEP) {
    int a = min((int)radar.amplitude, radarLimit());   // amplitude réellement balayée : jamais plus que la butée
    out.printf("Radar : balayage de -%d° à +%d° par pas de %d°%s.\n", a, a, (int)radar.pas,
               radar.autoFront ? ", capteur devant pendant une marche avant" : "");
  }
  else                       out.println(F("Radar : arrêt, servo recentré puis relâché."));
}

// Touche 'r' : arrêt -> fixe devant -> balayage. v15 : « fixe devant » remet la direction visée à 0, pour qu'une touche
// de la console n'envoie jamais le capteur de côté (la direction visée garde sinon la dernière valeur demandée par l'API).
void radarCycleMode() {
  if (radar.mode == RADAR_OFF) radar.fixedDeg = 0;
  radarSetMode(radar.mode == RADAR_OFF ? RADAR_FIXED : radar.mode == RADAR_FIXED ? RADAR_SWEEP : RADAR_OFF);
}

void radarClearMap() {
  portENTER_CRITICAL(&radarMux);
  for (int i = 0; i < RADAR_SLOTS; i++) { radar.mm[i] = -1; radar.ms[i] = 0; }
  portEXIT_CRITICAL(&radarMux);
  radar.frontMm = -1;
  out.println(F("Radar : carte effacée."));
}

// Distance devant en mm pour le CSV et /api/state : 0 = rien à portée, -1 = inconnue ou vieille de plus de 3 s
int radarFrontMm() { return (radar.frontMm >= 0 && millis() - radar.frontMs < 3000) ? radar.frontMm : -1; }

// Obstacle devant à moins du seuil, mesure récente, sécurité active et radar en marche ?
bool radarObstacleAhead() {
  if (!radar.securite || radar.mode == RADAR_OFF) return false;
  int16_t mm = radar.frontMm;
  return mm > 0 && mm < radar.seuilCm * 10 && millis() - radar.frontMs < RADAR_FRESH_MS;
}

// Appelée par la touche '8' avant d'avancer : vrai (et message, au plus un toutes les 2 s) si le radar interdit l'avance.
// Note aussi la date de la demande : la tâche radar garde le capteur devant tant que les demandes continuent.
bool radarForwardBlocked() {
  static uint32_t lastMsgMs = 0;
  radarFwdMs = millis();
  radarFwdSeen = true;
  if (!radarObstacleAhead()) return false;
  radar.refused = radar.refused + 1;
  if (millis() - lastMsgMs > 2000) {
    out.printf("Radar : obstacle à %d cm devant, avance refusée (seuil %d cm) : reculez ou tournez.\n", radar.frontMm / 10, (int)radar.seuilCm);
    lastMsgMs = millis();
  }
  return true;
}

// Appelée en boucle : arrêt des roues si le robot avance vers un obstacle ; messages sur l'état du capteur.
void radarTick() {
  static bool wasPresent = false, wasAbsent = false;
  static uint32_t lastStopMs = 0;
  if (radarRetourDemarrage) {   // v15 : dit une fois, après un redémarrage survenu capteur tourné de côté
    out.printf("Radar : la carte a redémarré avec le capteur tourné à %d° ; il revient devant lentement (%d°/s), puis le servo est relâché.\n",
               (int)radarRetourDemarrage, (int)radar.lent);
    radarRetourDemarrage = 0;
  }
  if (radar.present && !wasPresent) { wasPresent = true; out.println(F("Radar : capteur HC-SR04 détecté (premier écho reçu).")); }
  if (radar.absent != wasAbsent) {
    wasAbsent = radar.absent;
    if (wasAbsent) out.println(F("Radar : le capteur ne réagit pas (Echo jamais haut) : vérifier Vcc->5 V, Gnd->GND, Trig->D19, Echo->1 k->D23 (+2 k vers GND)."));
    else out.println(F("Radar : le capteur réagit de nouveau."));
  }
  if (driving && driveForward && radarObstacleAhead()) {
    stopWheels();
    radar.stops = radar.stops + 1;
    if (millis() - lastStopMs > 2000) {
      out.printf("Radar : obstacle à %d cm devant, roues arrêtées (seuil %d cm).\n", radar.frontMm / 10, (int)radar.seuilCm);
      lastStopMs = millis();
    }
  }
}

// Touche 'u' : état du radar et carte en clair
void radarPrintStatus() {
  int16_t f = radar.frontMm;
  uint32_t age = millis() - radar.frontMs;
  out.printf("Radar à ultrasons : mode %s%s, capteur vers %d°, servo %s, HC-SR04 %s\n", radarModeName(radar.mode),
             radar.following ? " (devant : marche avant demandée ou en cours)" : "", (int)radar.servoDeg,
             servoRelaxed ? "relâché" : "maintenu", radar.absent ? "SANS RÉACTION" : radar.present ? "détecté" : "pas encore entendu");
  if (radar.servoDeg != radar.cibleDeg) out.printf("Rotation lente en cours : vers %d°, à %d°/s\n", (int)radar.cibleDeg, (int)radar.lent);   // v15
  out.printf("Rotation lente au-delà de ±%d° : %d°/s (réglage « lent », %d à %d)\n", RADAR_ZONE_VIVE, (int)radar.lent, RADAR_LENT_MIN, RADAR_LENT_MAX);
  if (f > 0)       out.printf("Devant : %d cm (mesure vieille de %lu ms)\n", f / 10, (unsigned long)age);
  else if (f == 0) out.printf("Devant : rien à portée (< 4 m), mesure vieille de %lu ms\n", (unsigned long)age);
  else             out.println(F("Devant : distance inconnue"));
  out.printf("Réglages : seuil d'arrêt %d cm, arrêt auto %s, devant en marche avant %s, pas %d°, amplitude ±%d°, butée ±%d°, %d mesure(s) par direction, servo %s\n",
             (int)radar.seuilCm, radar.securite ? "oui" : "non", radar.autoFront ? "oui" : "non", (int)radar.pas, (int)radar.amplitude, radarLimit(),
             (int)radar.ech, radar.inverse ? "inversé" : "sens normal");
  out.printf("Compteurs : %lu mesures, %lu sans écho, %lu sans réaction, %lu passages, %lu arrêts auto, %lu avances refusées\n",
             (unsigned long)radar.pings, (unsigned long)radar.noEcho, (unsigned long)radar.faults, (unsigned long)radar.sweeps,
             (unsigned long)radar.stops, (unsigned long)radar.refused);
  out.print(F("Carte (angle° : cm ; · = rien à portée, ? = pas mesuré) :"));
  for (int i = 0; i < RADAR_SLOTS; i++) {
    if (i % 11 == 0) out.print(F("\n "));
    int16_t m = radar.mm[i];
    int a = -RADAR_SPAN_MAX + i * RADAR_SLOT_DEG;
    if (m > 0)       out.printf(" %+d:%d", a, m / 10);
    else if (m == 0) out.printf(" %+d:·", a);
    else             out.printf(" %+d:?", a);
  }
  out.println();
}

// Résumé pour /api/state (lu chaque seconde par monitor_wifi.py)
void radarStateJson(String& j) {
  char b[320];
  snprintf(b, sizeof(b), "\"radar\":{\"mode\":%u,\"front_mm\":%d,\"age\":%lu,\"present\":%s,\"absent\":%s,\"servo\":%d,"
                         "\"mm\":%d,\"a\":%d,\"mm_age\":%lu,\"seuil\":%d,\"securite\":%s,"
                         "\"cible\":%d,\"butee\":%d,\"lent\":%d},",   // v15 : direction visée, butée réglée, vitesse de la rotation lente
           (unsigned)radar.mode, (int)radar.frontMm, (unsigned long)(millis() - radar.frontMs), radar.present ? "true" : "false",
           radar.absent ? "true" : "false", (int)radar.servoDeg,
           (int)radar.lastMm, (int)radar.lastDeg, (unsigned long)(millis() - radar.lastMs),   // dernière mesure et sa direction
           (int)radar.seuilCm, radar.securite ? "true" : "false",
           (int)radar.cibleDeg, radarLimit(), (int)radar.lent);
  j += b;
}
