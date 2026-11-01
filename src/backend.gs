/**
 * Dépenses : backend Google Apps Script.
 *
 * Reçoit les notifications de banque et de carte (raccourci iPhone, courriels d'alerte lus
 * dans Gmail, tableau de bord), les lit avec SpendParser et les range dans cette feuille.
 * tools/build.mjs assemble ce fichier avec src/parser.js et src/insights.js en
 * apps-script/Spending.gs, le seul fichier à coller dans Apps Script.
 *
 * Installation (docs/GUIDE.fr.md) :
 *   1. Dans une feuille Google : Extensions > Apps Script. Remplacer Code.gs par Spending.gs.
 *   2. Déployer > Nouveau déploiement > Application Web, « Moi » / « Tout le monde ».
 *   3. Exécuter setup(). L'onglet Configuration de la feuille contient ensuite les liens.
 *
 * Jetons : CAPTURE_TOKEN (dans le raccourci : peut seulement ajouter des notifications) et
 * ADMIN_TOKEN (dans le tableau de bord : tout le reste).
 *
 * API (JSON ; le jeton dans le corps, ou ?token=... dans l'adresse) :
 *   POST {titre|title, soustitre|subtitle, corps|body}     une notification (jeton capture ou admin)
 *   POST {action:'list'|'ping'|'add'|'update'|'delete'|'rule'|'rule-delete'|'settings'|'unignore'|'confirm'}  (admin)
 *   GET  ?action=list|ping                                   (admin)
 */

var VERSION = '0.3.1';
var DASHBOARD_URL = 'https://jeanculess.github.io/Nassau/depenses.html';
var TX_SHEET = 'Transactions';
var IGNORED_SHEET = 'Ignored';
var RULES_SHEET = 'Rules';
var CONFIG_SHEET = 'Configuration';
var TX_COLS = ['date', 'amount', 'currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id', 'captured_at', 'reader', 'flags'];
var TX_FORMATS = ['yyyy-mm-dd hh:mm', '0.00', '@', '@', '@', '@', '@', '@', '@', '@', '@', '@', 'yyyy-mm-dd hh:mm:ss', '@', '@'];
var IGNORED_COLS = ['captured_at', 'source', 'reason', 'raw'];
var IGNORED_FORMATS = ['yyyy-mm-dd hh:mm:ss', '@', '@', '@'];
var RULES_COLS = ['pattern', 'category', 'name'];
var IGNORED_MAX = 1000;                 // les plus vieilles notifications ignorées sont supprimées
var IGNORED_DAYS = 62;                  // renvoyées au tableau de bord
var CAPTURE_MAX_PER_DAY = 300;          // au-delà, les notifications sont notées sans être lues
var STATUSES = ['ok', 'review', 'duplicate', 'excluded'];
var EDITABLE = ['date', 'amount', 'currency', 'merchant', 'category', 'type', 'card', 'status', 'note'];
var CHANNELS = ['phone', 'email', 'manual', 'paste', 'statement', 'applepay'];

// Fenêtres de détection des doublons (un même achat vu deux fois).
var REPEAT_DUP_MS = 90 * 1000;          // même texte, même source : le raccourci a tiré deux fois
var REPEAT_REVIEW_MS = 10 * 60 * 1000;  // même texte un peu plus tard : deux achats ? compté, à vérifier
var PHONE_PAIR_MS = 10 * 60 * 1000;     // Cartes + banque pour un paiement Apple Pay
var EMAIL_PAIR_MS = 12 * 60 * 60 * 1000; // notification + courriel du même achat
var EMAIL_SHORT_MS = 2 * 60 * 60 * 1000; // idem quand un des deux n'a pas de marchand
var MANUAL_PAIR_MS = 48 * 60 * 60 * 1000; // saisie manuelle / relevé / texte collé
var DEDUP_ROWS = 300;

// Surveillance et courriels.
var HEARTBEAT_DAYS_DEFAULT = 3;         // rien reçu depuis N jours -> courriel
var SOURCE_QUIET_DAYS = 7;              // une banque active qui se tait -> courriel
var ALERT_EVERY_DAYS = 7;               // un courriel par problème par semaine au plus
var EMAIL_QUERY_DEFAULT = 'newer_than:2d -label:Depenses (from:capitalone.ca OR from:capitalone.com OR from:scotiabank.com OR from:scotiabank.ca OR from:wealthsimple.com)';
var EMAIL_LABEL = 'Depenses';
var EMAIL_MAX_PER_TICK = 30;
var EMAIL_MAX_AGE_MS = 3 * 86400000;   // un courriel plus vieux n'est jamais relu
var MAIL_SEEN_DAYS = 4;                 // identifiants des courriels déjà lus, gardés dans les propriétés

// Claude (facultatif : rien ne sort de Google sans ANTHROPIC_API_KEY).
var CLAUDE_URL = 'https://api.anthropic.com/v1/messages';
var CLAUDE_DEFAULT_MODEL = 'claude-opus-5-5';
var CLAUDE_DEFAULT_MODE = 'review';     // review : seulement ce que les règles n'ont pas compris | always | off
var CLAUDE_MAX_PER_DAY = 40;
var CLAUDE_MAX_MONTH_USD = 1;
var CLAUDE_PRICES = { 'claude-opus-5-5': [4, 20], 'claude-sonnet-5-5': [2, 10], 'claude-haiku-5-5': [0.1, 0.5] }; // $ par million de jetons, entrée / sortie
var CLAUDE_REASONS = ['none', 'no-amount', 'not-a-spend', 'promo', 'declined', 'upcoming', 'statement', 'other'];
var CLAUDE_SCHEMA = {
  type: 'object',
  properties: {
    is_transaction: { type: 'boolean' },
    ignore_reason: { type: 'string', enum: CLAUDE_REASONS },
    type: { type: 'string', enum: ['purchase', 'refund', 'cash', 'fee', 'income', 'transfer'] },
    amount: { type: 'number' },
    currency: { type: 'string' },
    merchant: { type: 'string' },
    card: { type: 'string' },
    category: { type: 'string' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] }
  },
  required: ['is_transaction', 'ignore_reason', 'type', 'amount', 'currency', 'merchant', 'card', 'category', 'confidence'],
  additionalProperties: false
};

/* ================================================================== à lancer depuis l'éditeur */

/** Installe ou met à jour. Sans danger à relancer : les données et les jetons sont conservés. */
function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Ouvrez le script depuis la feuille (Extensions > Apps Script), puis relancez setup.');
  var props = PropertiesService.getScriptProperties();
  props.setProperty('SHEET_ID', ss.getId());

  // Jetons. Une installation de la version 0.1/0.2 n'avait qu'un jeton pour tout :
  // on le remplace par un jeton de capture et un jeton admin (l'ancien cesse de marcher).
  var migrated = false;
  if (!props.getProperty('ADMIN_TOKEN')) {
    var legacy = props.getProperty('TOKEN');
    props.setProperty('ADMIN_TOKEN', newToken_());
    props.setProperty('CAPTURE_TOKEN', newToken_());
    if (legacy) {
      // L'ancien jeton reste refusé, mais ses tentatives sont comptées : le tableau de bord dira que le raccourci n'a pas été mis à jour.
      props.setProperty('PREV_CAPTURE_TOKEN', legacy);
      props.setProperty('PREV_CAPTURE_UNTIL', String(now_().getTime() + 30 * 86400000));
      props.setProperty('STALE_HITS', '0');
      props.deleteProperty('TOKEN');
      migrated = true;
    }
  }
  if (!props.getProperty('CAPTURE_TOKEN')) props.setProperty('CAPTURE_TOKEN', newToken_());

  if (!props.getProperty('CURRENCY')) props.setProperty('CURRENCY', currencyFromLocale_(ss));
  ensureSheet_(ss, TX_SHEET, TX_COLS);
  ensureSheet_(ss, IGNORED_SHEET, IGNORED_COLS);
  ensureSheet_(ss, RULES_SHEET, RULES_COLS);
  // L'onglet vide créé par défaut (« Feuille 1 », « Sheet1 ») disparaît.
  ss.getSheets().forEach(function (sh) {
    var name = sh.getName();
    if ([TX_SHEET, IGNORED_SHEET, RULES_SHEET, CONFIG_SHEET].indexOf(name) < 0 && sh.getLastRow() === 0 && ss.getSheets().length > 3) ss.deleteSheet(sh);
  });
  var triggerOk = installTriggers_();
  var cfg = writeConfig_(ss);
  Logger.log('Installation terminée (version ' + VERSION + ').' +
    (migrated ? '\nL\'ancien jeton unique a été remplacé : recopiez le lien du raccourci dans Raccourcis.' : '') +
    '\n\nOuvrez l\'onglet « Configuration » de la feuille : il contient le lien du tableau de bord et le lien du raccourci.' +
    (cfg.webAppUrl ? '' : '\n\nL\'adresse de l\'application Web n\'est pas connue. Si le script n\'est pas déployé : Déployer > Nouveau déploiement > Application Web (Moi / Tout le monde). S\'il l\'est déjà : copiez l\'adresse qui se termine par /exec (Déployer > Gérer les déploiements) dans la cellule à droite de « Adresse du script » de l\'onglet Configuration, puis relancez setup.') +
    (triggerOk ? '' : '\n\nLe déclencheur automatique n\'a pas pu être installé (autorisation refusée ?). Relancez setup.') +
    '\n\nDevise : ' + currency_() + '. Relancer setup est sans danger.');
  return { adminToken: props.getProperty('ADMIN_TOKEN'), captureToken: props.getProperty('CAPTURE_TOKEN'), currency: currency_(), sheet: ss.getUrl(), webAppUrl: cfg.webAppUrl, migrated: migrated };
}

/** Alias en français. */
function installer() { return setup(); }

/** Remplace les deux jetons. Ensuite : rouvrir le tableau de bord depuis l'onglet Configuration et recopier le lien du raccourci. */
function rotateToken() {
  var props = PropertiesService.getScriptProperties();
  var old = props.getProperty('CAPTURE_TOKEN');
  if (old) {
    props.setProperty('PREV_CAPTURE_TOKEN', old);
    props.setProperty('PREV_CAPTURE_UNTIL', String(now_().getTime() + 30 * 86400000));
    props.setProperty('STALE_HITS', '0');
  }
  props.setProperty('ADMIN_TOKEN', newToken_());
  props.setProperty('CAPTURE_TOKEN', newToken_());
  var cfg = writeConfig_(ss_());
  Logger.log('Jetons remplacés. Onglet Configuration : rouvrez le tableau de bord avec le nouveau lien, puis recopiez le lien du raccourci dans Raccourcis.' + (cfg.webAppUrl ? '' : ' (Script non déployé.)'));
  return { adminToken: props.getProperty('ADMIN_TOKEN'), captureToken: props.getProperty('CAPTURE_TOKEN') };
}
function changerJetons() { return rotateToken(); }

/** Essaie le lecteur de notifications sur quelques textes. */
function testParse() {
  var samples = [
    { title: 'InfoAlerte Scotia', body: 'Un achat de 54,21 $ a été effectué chez IGA EXTRA avec votre carte Visa se terminant par 1234.' },
    { title: 'Visa Scotia', subtitle: 'Jean Coutu', body: '12,50 $' },
    { title: 'Capital One', body: 'Your verification code is 482913' }
  ];
  samples.forEach(function (s) {
    Logger.log(JSON.stringify(s) + '\n  -> ' + JSON.stringify(SpendParser.parse(s, { defaultCurrency: currency_(), rules: readRules_(ss_()) })));
  });
}

/** Envoie tout de suite le résumé hebdomadaire. */
function sendDigestNow() { return weeklyDigest_(true); }
/** Fait tout de suite la vérification quotidienne (courriel seulement s'il y a un problème). */
function checkNow() { return dailyCheck_(true); }
/** Lit tout de suite les courriels d'alerte. */
function pollEmailNow() { return pollEmail_(); }

/* ================================================================== points d'entrée web */

function doGet(e) {
  rememberUrl_();
  return respond_(function () {
    var p = (e && e.parameter) || {};
    var role = checkToken_(p.token);
    var action = p.action || 'list';
    if (role !== 'admin') throw new Error('Ce jeton ne permet que d\'envoyer des notifications.');
    if (action === 'list') return list_();
    if (action === 'ping') return ping_();
    throw new Error('Action inconnue : ' + action);
  }, false);
}

function doPost(e) {
  rememberUrl_();
  var b = body_(e);
  var action = b.action || 'capture';
  return respond_(function () {
    var role = checkToken_(b.token);
    if (action === 'capture') return capture_(b);
    if (role !== 'admin') throw new Error('Ce jeton ne permet que d\'envoyer des notifications.');
    if (action === 'add') return add_(b.tx || b);
    if (action === 'update') return update_(b.id, b.fields || {});
    if (action === 'delete') return delete_(b.id);
    if (action === 'confirm') return update_(b.id, { status: 'ok' });
    if (action === 'rule') return addRule_(b.pattern, b.category, b.apply !== false, b.name);
    if (action === 'rule-delete') return deleteRule_(b.pattern);
    if (action === 'settings') return settings_(b);
    if (action === 'unignore') return unignore_(b.captured_at, b.raw);
    if (action === 'list') return list_();
    if (action === 'ping') return ping_();
    throw new Error('Action inconnue : ' + action);
  }, action !== 'capture' && action !== 'list' && action !== 'ping');
}

// Les écritures du tableau de bord passent sous le verrou ; la capture gère son propre verrou court.
function respond_(fn, useLock) {
  var lock = null;
  var out;
  try {
    if (useLock) {
      lock = LockService.getScriptLock();
      lock.waitLock(30000);
    }
    out = fn();
  } catch (err) {
    out = { ok: false, error: String((err && err.message) || err) };
  } finally {
    if (lock) {
      try { lock.releaseLock(); } catch (ignored) { /* jamais obtenu */ }
    }
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

// Corps JSON (raccourci, tableau de bord), champs de formulaire, ou texte brut. Les paramètres de l'adresse complètent.
function body_(e) {
  var b = {};
  var pd = e && e.postData;
  if (pd && pd.contents && !/x-www-form-urlencoded/i.test(pd.type || '')) {
    try { b = JSON.parse(pd.contents); } catch (err) { b = null; }
    if (!b || typeof b !== 'object' || Array.isArray(b)) b = { body: String(pd.contents) };
  }
  var p = (e && e.parameter) || {};
  Object.keys(p).forEach(function (k) { if (b[k] === undefined) b[k] = p[k]; });
  return b;
}

// 'admin' | 'capture', ou une erreur. Un ancien jeton de capture est refusé mais compté :
// le tableau de bord et la vérification quotidienne peuvent dire que le raccourci n'a pas été mis à jour.
function checkToken_(token) {
  var props = PropertiesService.getScriptProperties();
  var admin = props.getProperty('ADMIN_TOKEN');
  if (!admin) throw new Error('Lancez setup() dans l\'éditeur Apps Script d\'abord.');
  var t = String(token || '').trim();
  if (!t) throw new Error('Non autorisé : jeton manquant.');
  if (t === admin) return 'admin';
  if (t === props.getProperty('CAPTURE_TOKEN')) return 'capture';
  var prev = props.getProperty('PREV_CAPTURE_TOKEN');
  if (prev && t === prev && Number(props.getProperty('PREV_CAPTURE_UNTIL') || 0) > now_().getTime()) {
    props.setProperty('STALE_HITS', String(Number(props.getProperty('STALE_HITS') || 0) + 1));
    props.setProperty('LAST_STALE_AT', now_().toISOString());
    throw new Error('Non autorisé : ce lien est périmé (les jetons ont été changés). Recopiez le lien du raccourci.');
  }
  throw new Error('Non autorisé : jeton incorrect.');
}

// Pendant une vraie requête, l'adresse de l'application Web est connue : on la garde pour l'onglet Configuration.
function rememberUrl_() {
  try {
    var url = ScriptApp.getService().getUrl() || '';
    if (/^https:\/\/\S+\/exec$/.test(url)) {
      var props = PropertiesService.getScriptProperties();
      if (props.getProperty('WEB_APP_URL') !== url) props.setProperty('WEB_APP_URL', url);
    }
  } catch (e) { /* hors requête */ }
}

/* ================================================================== capture */

// Les clés acceptées pour une notification, en français et en anglais.
function fields_(b) {
  var title = first_(b.title, b.titre, b.t);
  var subtitle = first_(b.subtitle, b.soustitre, b['sous-titre'], b.sous_titre, b.s);
  var body = first_(b.body, b.corps, b.text, b.texte, b.message, b.content, b.contenu, b.notification, b.c);
  if (blank_(title) && blank_(subtitle) && blank_(body) && !blank_(b.n)) {
    // Toute la notification dans un seul champ : première ligne = titre.
    var lines = String(b.n).split(/\r?\n/);
    title = lines.shift();
    body = lines.join(' ');
  }
  return { title: str_(title, 300), subtitle: str_(subtitle, 300), body: str_(body, 2000), app: str_(b.app, 40), from: str_(b.from, 200) };
}

function channelOf_(b, structured) {
  var c = String(b.channel || '').trim().toLowerCase();
  if (!c && b.source) c = String(b.source).split(':')[0].toLowerCase();
  if (c === 'notification' || c === 'notif') c = 'phone';
  if (CHANNELS.indexOf(c) < 0) c = structured ? 'applepay' : 'phone';
  return c;
}

function capture_(b) {
  var ss = ss_();
  var cur = currency_();
  var props = PropertiesService.getScriptProperties();
  var f = fields_(b);
  var structured = !blank_(b.amount) || !blank_(b.merchant);
  var channel = channelOf_(b, structured);
  var bank = str_(b.bank, 20).toLowerCase() || SpendParser.inferBank({ app: f.app, title: f.title, subtitle: f.subtitle, body: f.body, from: f.from });
  var source = channel + (bank ? ':' + bank : '');
  var received = now_();

  // Un envoi sans aucun texte : le bouton ▶ du raccourci. On le note, rien n'est ajouté.
  if (!structured && !f.title && !f.subtitle && !f.body) {
    if (channel === 'phone') props.setProperty('SHORTCUT_PING_AT', received.toISOString());
    return { ok: true, status: 'test', message: 'Raccourci relié ✓ (aucune notification dans cet envoi)' };
  }

  // Trop de notifications dans la journée (jeton de capture diffusé ?) : on note sans lire.
  var countKey = 'CAPTURE_COUNT_' + dayKey_(received);
  var count = Number(props.getProperty(countKey) || 0) + 1;
  props.setProperty(countKey, String(count));
  if (count > CAPTURE_MAX_PER_DAY) {
    appendIgnored_(ss, { captured_at: received, source: source, reason: 'rate-limit', raw: '' });
    return { ok: true, status: 'ignored', reason: 'rate-limit', message: 'Trop de notifications aujourd\'hui : non lue' };
  }

  if (channel === 'phone') props.setProperty('LAST_PHONE_AT', received.toISOString());
  if (channel === 'email') props.setProperty('LAST_EMAIL_AT', received.toISOString());
  props.setProperty('LAST_SRC_' + source, received.toISOString());

  // Le raccourci envoie les mots « Titre », « corps »... au lieu des variables.
  if (!structured && SpendParser.isPlaceholder(f)) {
    props.setProperty('MISCONFIGURED_AT', received.toISOString());
    appendIgnored_(ss, { captured_at: received, source: source, reason: 'raccourci', raw: [f.title, f.subtitle, f.body].filter(String).join(' | ') });
    return { ok: true, status: 'ignored', reason: 'raccourci', message: 'Raccourci mal configuré : les valeurs doivent être des variables (pastilles bleues), pas des mots tapés.' };
  }

  var rules = readRules_(ss);
  var r;
  var raw;
  if (structured) {
    r = SpendParser.fromFields({ amount: b.amount, merchant: b.merchant, card: b.card, currency: b.currency, type: b.type, category: b.category },
      { defaultCurrency: cur, rules: rules });
    raw = [str_(b.merchant, 100), str_(b.amount, 40), str_(b.card, 60)].filter(String).join(' | ');
  } else {
    r = SpendParser.parse({ title: f.title, subtitle: f.subtitle, body: f.body, app: f.app }, { defaultCurrency: cur, rules: rules });
    raw = [f.title, f.subtitle, f.body].filter(String).join(' | ');
  }

  if (r.kind !== 'transaction') {
    appendIgnored_(ss, { captured_at: received, source: source, reason: r.reason, raw: SpendParser.redactCodes(raw) });
    return { ok: true, status: 'ignored', reason: r.reason, message: 'Pas une transaction (' + reasonLabel_(r.reason) + ')' };
  }

  var notes = [];
  if (r.reason === 'hold') notes.push('Préautorisation ou montant mis à jour');
  if (r.original) notes.push('Montant original : ' + r.original.amount.toFixed(2) + ' ' + r.original.currency);
  var ruled = applyRules_(r, rules);
  var cfg = claudeConfig_();
  var tx = {
    id: newId_(), date: when_(b.date, b.trusted === true || channel === 'email' || channel === 'statement' || channel === 'paste' || channel === 'manual') || received,
    amount: SpendParser.signedAmount(r.amount, r.type), currency: r.currency,
    merchant: ruled.name || r.merchant, category: ruled.category || r.category, type: r.type, card: r.card,
    status: ruled.excluded ? 'excluded' : r.status, note: notes.join(' · '),
    source: source, raw: raw, captured_at: received,
    reader: cfg && !structured && shouldAskClaude_(cfg, r) ? 'pending' : 'rules', flags: ''
  };
  if (str_(b.note, 500)) tx.note = [tx.note, str_(b.note, 500)].filter(String).join(' · ');

  storeTx_(sheet_(ss, TX_SHEET, TX_COLS), tx);
  return { ok: true, status: tx.status === 'duplicate' ? 'duplicate' : tx.status === 'review' ? 'review' : 'added', tx: out_(tx, cur), message: message_(tx) };
}

// Vérifie les doublons et ajoute la ligne, sous un verrou court. Si la feuille est occupée, la ligne est
// quand même ajoutée (à vérifier) : rien n'est jamais perdu.
function storeTx_(sheet, tx) {
  var lock = LockService.getScriptLock();
  var locked = false;
  try { locked = lock.tryLock(10000); } catch (e) { locked = false; }
  try {
    var recent = readTx_(sheet, DEDUP_ROWS);
    tx.flags = flags_(tx, recent);
    if (locked) {
      var dup = findDuplicate_(recent, tx);
      if (dup) applyDuplicate_(tx, dup);
    } else {
      if (tx.status === 'ok') tx.status = 'review';
      tx.note = [tx.note, 'Enregistré sans vérification de doublon (feuille occupée)'].filter(String).join(' · ');
    }
    appendRow_(sheet, TX_COLS, TX_FORMATS, tx);
  } finally {
    if (locked) { try { lock.releaseLock(); } catch (ignored) { /* rien */ } }
  }
  return tx;
}

function applyDuplicate_(tx, dup) {
  var label = (dup.row.merchant || 'un achat') + ' (' + sourceLabel_(dup.row.source) + ')';
  if (dup.kind === 'repeat-review' || dup.kind === 'near-review' || dup.kind === 'manual-review') {
    if (tx.status === 'ok') tx.status = 'review';
    tx.flags = [tx.flags, 'dup'].filter(String).join(',');
    tx.note = [tx.note, dup.kind === 'repeat-review'
      ? 'Même texte il y a ' + minutesAgo_(dup.row.date, tx.date) + ' min : deux achats, ou envoi en double ?'
      : dup.kind === 'manual-review' ? 'Ressemble à ' + label + ' : deux achats, ou doublon ?'
      : 'Même montant chez ' + (dup.row.merchant || '?') + ' il y a ' + minutesAgo_(dup.row.date, tx.date) + ' min : deux achats, ou doublon ?'].filter(String).join(' · ');
  } else {
    tx.status = 'duplicate';
    tx.note = [tx.note, dup.kind === 'repeat' ? 'Même notification reçue deux fois' : 'Doublon probable de ' + label].filter(String).join(' · ');
  }
}

// Règles de l'utilisateur : catégorie, nom à afficher, ou « (ignorer) ».
function applyRules_(r, rules) {
  var out = { category: '', name: '', excluded: false };
  if (!r.merchant || (r.type !== 'purchase' && r.type !== 'refund')) return out;
  var fm = SpendParser.fold(r.merchant);
  for (var i = 0; i < rules.length; i++) {
    var rule = rules[i];
    if (!SpendParser.matchRule(fm, rule.pattern)) continue;
    if (/^\(ignorer\)$|^\(ignore\)$/i.test(rule.category)) { out.excluded = true; out.category = r.category; }
    else out.category = rule.category;
    out.name = rule.name || '';
    break;
  }
  return out;
}

function flags_(tx, recent) {
  var I = insights_();
  if (!I || tx.type !== 'purchase') return '';
  try {
    return I.flagAtCapture({ amount: tx.amount, merchant: tx.merchant, currency: tx.currency, type: tx.type, status: tx.status },
      recent.map(function (t) { return { amount: t.amount, merchant: t.merchant, currency: t.currency, type: t.type, status: t.status, date: t.date }; })).join(',');
  } catch (e) { return ''; }
}

// Un même achat peut arriver deux fois ; différents numéros de carte ou marchands incompatibles = jamais un doublon.
//   repeat         même texte, même source, < 90 s          -> doublon (le raccourci a tiré deux fois)
//   repeat-review  même texte, même source, < 10 min        -> compté, à vérifier (deux cafés ?)
//   near-review    autre texte, même source, < 10 min       -> compté, à vérifier
//   cross          autre source : téléphone/téléphone < 10 min, courriel < 12 h -> doublon
//   manual-review  saisie, texte collé ou relevé qui ressemble à une ligne des 48 h -> compté, à vérifier
//                  (sauf texte identique déjà reçu : doublon)
function findDuplicate_(rows, tx) {
  var t = tx.date.getTime();
  var chanT = tx.source.split(':')[0];
  for (var i = rows.length - 1; i >= 0; i--) {
    var r = rows[i];
    if (r.status === 'duplicate' || r.status === 'excluded' || !r.date) continue;
    if (Math.abs(r.amount - tx.amount) > 0.005 || (r.currency || tx.currency) !== tx.currency) continue;
    var dt = Math.abs(r.date.getTime() - t);
    var same = r.source === tx.source;
    var liveT = chanT === 'phone' || chanT === 'email';
    if (same && r.raw && r.raw === tx.raw) {
      if (dt < REPEAT_DUP_MS) return { kind: 'repeat', row: r };
      if (dt < REPEAT_REVIEW_MS) return { kind: 'repeat-review', row: r };
      if (liveT) continue; // le même texte bien plus tard = un nouvel achat
    }
    // Un texte collé qui est exactement une notification déjà reçue.
    if (chanT === 'paste' && r.raw && r.raw === tx.raw && dt < MANUAL_PAIR_MS) return { kind: 'cross', row: r };
    var da = cardDigits_(r.card);
    var db = cardDigits_(tx.card);
    if (da && db && da !== db) continue;
    if (!merchantCompatible_(r.merchant, tx.merchant)) continue;
    var chanR = r.source.split(':')[0];
    if (same && liveT) {
      if (dt < PHONE_PAIR_MS) return { kind: 'near-review', row: r };
      continue;
    }
    if (chanR === 'phone' && chanT === 'phone') {
      if (dt < PHONE_PAIR_MS) return { kind: 'cross', row: r };
      continue;
    }
    if (chanR === 'email' || chanT === 'email') {
      if (dt < (r.merchant && tx.merchant ? EMAIL_PAIR_MS : EMAIL_SHORT_MS)) return { kind: 'cross', row: r };
      continue;
    }
    if (dt < MANUAL_PAIR_MS) return { kind: liveT ? 'cross' : 'manual-review', row: r };
  }
  return null;
}

function merchantKey_(m) {
  var I = insights_();
  return I ? I.key(m) : SpendParser.fold(m).replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function merchantCompatible_(a, b) {
  var ka = merchantKey_(a);
  var kb = merchantKey_(b);
  if (!ka || !kb || ka === kb) return true;
  var wa = ka.split(' ').filter(function (w) { return w.length >= 3; })[0];
  var wb = kb.split(' ').filter(function (w) { return w.length >= 3; })[0];
  if (wa && kb.indexOf(wa) >= 0) return true;
  if (wb && ka.indexOf(wb) >= 0) return true;
  return ka.slice(0, 4) === kb.slice(0, 4) && ka.length >= 4 && kb.length >= 4;
}

/* ================================================================== actions du tableau de bord */

// Saisie manuelle, texte collé ou ligne de relevé : passe par la capture (doublons, règles).
function add_(t) {
  var text = str_(first_(t.text, t.raw), 2000);
  if (blank_(t.amount) && text) {
    var r = capture_({ channel: t.source === 'statement' ? 'statement' : 'paste', body: text, date: t.date, trusted: true, note: t.note });
    if (r.status === 'ignored') throw new Error('Ce texte n\'a pas été lu comme une transaction (' + reasonLabel_(r.reason) + ').');
    return r;
  }
  if (blank_(t.amount)) throw new Error('Le montant manque.');
  return capture_({ channel: t.source === 'statement' ? 'statement' : 'manual', amount: t.amount, merchant: t.merchant, card: t.card, currency: t.currency,
    type: t.type, category: t.category, date: t.date, trusted: true, note: t.note });
}

function update_(id, fields) {
  var ss = ss_();
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
  var row = findRow_(sheet, id);
  if (!row) throw new Error('Transaction introuvable : ' + id);
  var o = rowObj_(sheet.getRange(row, 1, 1, TX_COLS.length).getValues()[0]);
  EDITABLE.forEach(function (k) {
    if (fields[k] === undefined || fields[k] === null) return;
    var v = fields[k];
    if (k === 'date') {
      var d = date_(v);
      if (d) o.date = d;
    } else if (k === 'amount') {
      var n = Number(v);
      if (isFinite(n)) o.amount = n;
    } else if (k === 'type') {
      if (SpendParser.TYPES.indexOf(v) >= 0) o.type = v;
    } else if (k === 'status') {
      if (STATUSES.indexOf(v) >= 0) o.status = v;
    } else if (k === 'currency') {
      var c = String(v).trim().toUpperCase();
      if (/^[A-Z]{3}$/.test(c)) o.currency = c;
    } else {
      o[k] = str_(v, k === 'note' ? 500 : 100);
    }
  });
  o.amount = SpendParser.signedAmount(o.amount, o.type || 'purchase');
  if (o.reader === 'pending') o.reader = 'rules';
  writeRow_(sheet, row, TX_COLS, TX_FORMATS, o);
  return { ok: true, tx: out_(o, currency_()) };
}

// Une ligne capturée n'est jamais effacée : elle est exclue (visible, non comptée). Une saisie manuelle l'est.
function delete_(id) {
  var sheet = sheet_(ss_(), TX_SHEET, TX_COLS);
  var row = findRow_(sheet, id);
  if (!row) throw new Error('Transaction introuvable : ' + id);
  var o = rowObj_(sheet.getRange(row, 1, 1, TX_COLS.length).getValues()[0]);
  var chan = o.source.split(':')[0];
  if (chan === 'manual' || chan === 'paste' || chan === 'statement' || chan === 'sheet' || !o.source) {
    sheet.deleteRow(row);
    return { ok: true, id: id, deleted: true };
  }
  o.status = 'excluded';
  o.note = [o.note, 'Supprimé depuis le tableau de bord le ' + dayKey_(now_())].filter(String).join(' · ');
  writeRow_(sheet, row, TX_COLS, TX_FORMATS, o);
  return { ok: true, id: id, deleted: false, tx: out_(o, currency_()) };
}

// Les règles sont lues de haut en bas : la nouvelle va en haut.
function addRule_(pattern, category, apply, name) {
  pattern = str_(pattern, 100);
  category = str_(category, 40);
  name = str_(name, 60);
  if (!pattern || !category) throw new Error('Une règle a besoin d\'un motif et d\'une catégorie.');
  var ss = ss_();
  var rules = readRules_(ss).filter(function (r) { return SpendParser.fold(r.pattern) !== SpendParser.fold(pattern); });
  rules.unshift({ pattern: pattern, category: category, name: name });
  writeRules_(ss, rules);

  var updated = 0;
  if (apply) {
    var sheet = sheet_(ss, TX_SHEET, TX_COLS);
    var catCol = TX_COLS.indexOf('category') + 1;
    var merchantCol = TX_COLS.indexOf('merchant') + 1;
    var statusCol = TX_COLS.indexOf('status') + 1;
    var ignore = /^\(ignorer\)$|^\(ignore\)$/i.test(category);
    readTx_(sheet, 0).forEach(function (r) {
      if (r.type && r.type !== 'purchase' && r.type !== 'refund') return;
      if (!SpendParser.matchRule(SpendParser.fold(r.merchant), pattern)) return;
      var changed = false;
      if (ignore) {
        if (r.status !== 'excluded' && r.status !== 'duplicate') { sheet.getRange(r._row, statusCol).setValue('excluded'); changed = true; }
      } else if (r.category !== category) { sheet.getRange(r._row, catCol).setValue(category); changed = true; }
      if (name && r.merchant !== name) { sheet.getRange(r._row, merchantCol).setValue(name); changed = true; }
      if (changed) updated++;
    });
  }
  return { ok: true, updated: updated, rules: readRules_(ss) };
}

function deleteRule_(pattern) {
  var ss = ss_();
  var rules = readRules_(ss).filter(function (r) { return SpendParser.fold(r.pattern) !== SpendParser.fold(str_(pattern, 100)); });
  writeRules_(ss, rules);
  return { ok: true, rules: rules };
}

function settings_(b) {
  var props = PropertiesService.getScriptProperties();
  if (b.currency !== undefined) {
    var c = String(b.currency).trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(c)) throw new Error('La devise doit être un code à 3 lettres (CAD, USD, EUR).');
    props.setProperty('CURRENCY', c);
  }
  if (b.budget !== undefined) {
    var n = Number(b.budget);
    if (!isFinite(n) || n < 0) throw new Error('Le budget doit être un nombre.');
    props.setProperty('BUDGET', String(Math.round(n * 100) / 100));
  }
  if (b.digest !== undefined) props.setProperty('DIGEST', b.digest === false || b.digest === 'off' ? 'off' : 'on');
  if (b.email !== undefined) props.setProperty('EMAIL', b.email === false || b.email === 'off' ? 'off' : 'on');
  if (b.heartbeatDays !== undefined) {
    var h = Number(b.heartbeatDays);
    if (isFinite(h) && h >= 1 && h <= 30) props.setProperty('HEARTBEAT_DAYS', String(Math.round(h)));
  }
  if (b.claudeMode !== undefined && ['review', 'always', 'off'].indexOf(b.claudeMode) >= 0) props.setProperty('CLAUDE_MODE', b.claudeMode);
  return { ok: true, settings: settingsOut_() };
}

function unignore_(capturedAt, raw) {
  var ss = ss_();
  var sh = ss.getSheetByName(IGNORED_SHEET);
  if (!sh || sh.getLastRow() < 2) return { ok: true, removed: 0 };
  var last = sh.getLastRow();
  var values = sh.getRange(2, 1, last - 1, IGNORED_COLS.length).getValues();
  var removed = 0;
  var wanted = date_(capturedAt);
  for (var i = values.length - 1; i >= 0; i--) {
    var d = date_(values[i][0]);
    if (String(values[i][3]) === String(raw || '') && d && wanted && Math.abs(d.getTime() - wanted.getTime()) < 2000) {
      sh.deleteRow(i + 2);
      removed++;
    }
  }
  return { ok: true, removed: removed };
}

function list_() {
  var ss = ss_();
  var cur = currency_();
  var sheet = ensureSheet_(ss, TX_SHEET, TX_COLS);
  var rows = readTx_(sheet, 0);
  var idCol = TX_COLS.indexOf('id') + 1;
  rows.forEach(function (r) {
    // Une ligne tapée directement dans la feuille reçoit un identifiant pour que le tableau de bord puisse la modifier.
    if (!r.id) {
      r.id = newId_();
      sheet.getRange(r._row, idCol).setValue(r.id);
    }
  });
  var links = links_();
  return {
    ok: true, version: VERSION, currency: cur, sheetUrl: ss.getUrl(),
    captureToken: PropertiesService.getScriptProperties().getProperty('CAPTURE_TOKEN'), shortcutUrl: links.shortcutUrl, webAppUrl: links.webAppUrl,
    settings: settingsOut_(), health: health_(rows),
    transactions: rows.map(function (r) { return out_(r, cur); }),
    ignored: readIgnored_(ss, IGNORED_DAYS),
    rules: readRules_(ss)
  };
}

function ping_() {
  var cfg = claudeConfig_();
  var links = links_();
  return {
    ok: true, version: VERSION, parser: SpendParser.VERSION, currency: currency_(),
    claude: cfg ? cfg.mode + ' · ' + cfg.model : 'off',
    captureToken: PropertiesService.getScriptProperties().getProperty('CAPTURE_TOKEN'), shortcutUrl: links.shortcutUrl,
    settings: settingsOut_(), health: health_(null)
  };
}

function settingsOut_() {
  var props = PropertiesService.getScriptProperties();
  return {
    currency: currency_(), budget: Number(props.getProperty('BUDGET') || 0),
    digest: props.getProperty('DIGEST') !== 'off', email: props.getProperty('EMAIL') !== 'off',
    heartbeatDays: heartbeatDays_(), claudeMode: (claudeConfig_() || {}).mode || 'off', triggers: props.getProperty('TRIGGER_INSTALLED') === 'yes'
  };
}

// L'état de la capture : quand chaque source a parlé pour la dernière fois, etc.
function health_(rows) {
  var props = PropertiesService.getScriptProperties();
  var all = props.getProperties ? props.getProperties() : {};
  var bySource = {};
  Object.keys(all).forEach(function (k) { if (k.indexOf('LAST_SRC_') === 0) bySource[k.slice(9)] = all[k]; });
  var cfg = claudeConfig_();
  var today = dayKey_(now_());
  var month = today.slice(0, 7);
  var emailOnly = 0;
  if (rows) {
    var since = now_().getTime() - 7 * 86400000;
    rows.forEach(function (r) {
      if (r.source.indexOf('email:') === 0 && r.status !== 'duplicate' && r.status !== 'excluded' && r.captured_at && r.captured_at.getTime() > since) emailOnly++;
    });
  }
  return {
    lastPhoneAt: props.getProperty('LAST_PHONE_AT') || null,
    lastEmailAt: props.getProperty('LAST_EMAIL_AT') || null,
    shortcutPingAt: props.getProperty('SHORTCUT_PING_AT') || null,
    misconfiguredAt: props.getProperty('MISCONFIGURED_AT') || null,
    lastStaleAt: props.getProperty('LAST_STALE_AT') || null,
    staleHits: Number(props.getProperty('STALE_HITS') || 0),
    bySource: bySource,
    emailOnly7d: emailOnly,
    captureToday: Number(props.getProperty('CAPTURE_COUNT_' + today) || 0),
    lastTickAt: props.getProperty('LAST_TICK_AT') || null,
    claude: cfg ? { on: true, model: cfg.model, mode: cfg.mode, callsToday: Number(props.getProperty('CLAUDE_CALLS_' + today) || 0), costMonthUsd: Number(props.getProperty('CLAUDE_COST_' + month) || 0) } : { on: false }
  };
}

/* ================================================================== déclencheur : toutes les 15 minutes */

function installTriggers_() {
  try {
    ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'tick') ScriptApp.deleteTrigger(t); });
    ScriptApp.newTrigger('tick').timeBased().everyMinutes(15).create();
    PropertiesService.getScriptProperties().setProperty('TRIGGER_INSTALLED', 'yes');
    return true;
  } catch (e) {
    Logger.log('Déclencheur non installé : ' + e);
    PropertiesService.getScriptProperties().setProperty('TRIGGER_INSTALLED', 'no');
    return false;
  }
}

function tick() {
  var props = PropertiesService.getScriptProperties();
  props.setProperty('LAST_TICK_AT', now_().toISOString());
  safe_('pollEmail', pollEmail_);
  safe_('enrichPending', enrichPending_);
  safe_('dailyCheck', function () { dailyCheck_(false); });
  safe_('weeklyDigest', function () { weeklyDigest_(false); });
  safe_('writeConfig', function () { writeConfig_(ss_()); });
}

function safe_(name, fn) {
  try { return fn(); } catch (e) { Logger.log(name + ' : ' + (e && e.stack || e)); return null; }
}

/* ------------------------------------------------------------------ courriels d'alerte lus dans Gmail */

function pollEmail_() {
  var props = PropertiesService.getScriptProperties();
  if (props.getProperty('EMAIL') === 'off') return { ok: true, skipped: 'off' };
  if (typeof GmailApp === 'undefined') return { ok: true, skipped: 'no-gmail' };
  var query = props.getProperty('EMAIL_QUERY') || EMAIL_QUERY_DEFAULT;
  var label = GmailApp.getUserLabelByName(EMAIL_LABEL) || GmailApp.createLabel(EMAIL_LABEL);
  var threads = GmailApp.search(query, 0, EMAIL_MAX_PER_TICK);
  var seen = 0;
  var added = 0;
  var nowMs = now_().getTime();
  // Gmail regroupe les alertes d'une banque en une conversation : chaque message n'est lu qu'une fois,
  // grâce à une liste persistante des identifiants déjà lus (les plus vieux de 4 jours sont oubliés).
  var seenIds = {};
  try { seenIds = JSON.parse(props.getProperty('MAIL_SEEN') || '{}'); } catch (e) { seenIds = {}; }
  Object.keys(seenIds).forEach(function (k) { if (nowMs - Number(seenIds[k]) > MAIL_SEEN_DAYS * 86400000) delete seenIds[k]; });
  threads.forEach(function (thread) {
    thread.getMessages().forEach(function (msg) {
      var id = msg.getId();
      if (seenIds[id]) return;
      var when = msg.getDate();
      if (!when || nowMs - when.getTime() > EMAIL_MAX_AGE_MS) return; // un ancien message de la conversation
      seenIds[id] = String(nowMs);
      seen++;
      var from = String(msg.getFrom() || '');
      var subject = String(msg.getSubject() || '');
      var body = cleanEmailBody_(msg.getPlainBody());
      var suspicious = /https?:\/\//i.test(body) && /\b(v[ée]rifi\w*|valid\w*|confirm\w*|mot de passe|password|connectez-vous|log ?in)\b/i.test(body) && !/\b(achat|purchase|transaction|paiement|payment)\b/i.test(subject + ' ' + body.slice(0, 300));
      if (suspicious) {
        appendIgnored_(ss_(), { captured_at: now_(), source: 'email', reason: 'suspect', raw: SpendParser.redactCodes(subject) });
        return;
      }
      var r = capture_({ channel: 'email', from: from, title: subject, body: body, date: when, trusted: true });
      if (r && (r.status === 'added' || r.status === 'review')) added++;
    });
    thread.addLabel(label);
  });
  props.setProperty('MAIL_SEEN', JSON.stringify(seenIds));
  return { ok: true, seen: seen, added: added };
}

// Le corps d'un courriel d'alerte, sans le pied de page légal ni les liens de désabonnement.
function cleanEmailBody_(text) {
  var t = String(text || '').replace(/\r/g, '').replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n').trim();
  var cut = t.search(/\b(unsubscribe|se d[ée]sabonner|d[ée]sabonnement|privacy policy|politique de confidentialit[ée]|this email was sent|ce courriel (?:vous )?a [ée]t[ée] envoy[ée]|©|all rights reserved|tous droits r[ée]serv[ée]s)\b/i);
  if (cut > 40) t = t.slice(0, cut);
  return t.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1500);
}

/* ------------------------------------------------------------------ vérification quotidienne */

function heartbeatDays_() {
  var n = Number(PropertiesService.getScriptProperties().getProperty('HEARTBEAT_DAYS'));
  return isFinite(n) && n >= 1 ? n : HEARTBEAT_DAYS_DEFAULT;
}

function dailyCheck_(force) {
  var props = PropertiesService.getScriptProperties();
  var today = dayKey_(now_());
  if (!force) {
    if (props.getProperty('HEALTH_DAY') === today) return { ok: true, skipped: 'done' };
    if (hourLocal_(now_()) < 8) return { ok: true, skipped: 'early' };
  }
  props.setProperty('HEALTH_DAY', today);
  var h = health_(readTx_(sheet_(ss_(), TX_SHEET, TX_COLS), 400));
  var nowMs = now_().getTime();
  var problems = [];
  var last = [h.lastPhoneAt, h.lastEmailAt, h.shortcutPingAt].filter(Boolean).map(function (s) { return new Date(s).getTime(); });
  var lastAny = last.length ? Math.max.apply(null, last) : 0;
  var days = heartbeatDays_();
  if (lastAny && nowMs - lastAny > days * 86400000) {
    problems.push({ key: 'silent', text: 'Rien n\'est arrivé depuis ' + Math.floor((nowMs - lastAny) / 86400000) + ' jours (ni notification, ni courriel).\n' +
      'À vérifier : dans Raccourcis, l\'automatisation est activée et réglée pour s\'exécuter sans demander ; dans Réglages > Notifications, les aperçus sont affichés ; la mise à jour d\'iOS n\'a pas désactivé l\'automatisation.' });
  }
  Object.keys(h.bySource).forEach(function (src) {
    var t = new Date(h.bySource[src]).getTime();
    if (src.indexOf('phone:') !== 0 || !t) return;
    var age = nowMs - t;
    if (age > SOURCE_QUIET_DAYS * 86400000 && age < 30 * 86400000 && !(lastAny && nowMs - lastAny > days * 86400000)) {
      problems.push({ key: 'quiet-' + src, text: 'Rien de ' + sourceLabel_(src) + ' depuis ' + Math.floor(age / 86400000) + ' jours, alors que cette banque envoyait des notifications.\n' +
        'À vérifier : les alertes d\'achat sont toujours activées dans l\'appli de la banque, et l\'appli est encore dans la liste de l\'automatisation.' });
    }
  });
  if (h.staleHits > 0 && h.lastStaleAt && nowMs - new Date(h.lastStaleAt).getTime() < 7 * 86400000) {
    problems.push({ key: 'stale', text: 'Votre raccourci utilise encore l\'ancien lien (' + h.staleHits + ' tentatives). Ses notifications ne sont pas enregistrées.\n' +
      'À faire : dans le tableau de bord, Réglages > Copier le lien du raccourci, puis remplacez l\'URL dans l\'action « Obtenir le contenu de l\'URL ».' });
  }
  if (h.misconfiguredAt && nowMs - new Date(h.misconfiguredAt).getTime() < 2 * 86400000) {
    problems.push({ key: 'misconfigured', text: 'Le raccourci envoie les mots « Titre », « Sous-titre » ou « Corps » au lieu du contenu des notifications.\n' +
      'À faire : dans l\'action « Obtenir le contenu de l\'URL », chaque valeur doit être une variable (pastille bleue) choisie avec « Sélectionner une variable », pas un mot tapé.' });
  }
  if (h.emailOnly7d >= 2) {
    problems.push({ key: 'email-only', text: h.emailOnly7d + ' achats des 7 derniers jours ne sont arrivés que par courriel : votre iPhone rate des notifications.\n' +
      'À vérifier : Réglages > Notifications pour chaque appli bancaire (livraison immédiate, aperçus affichés), et que l\'automatisation s\'exécute sans confirmation.' });
  }
  var toSend = problems.filter(function (p) {
    var lastSent = Number(props.getProperty('LAST_ALERT_' + p.key) || 0);
    return force || nowMs - lastSent > ALERT_EVERY_DAYS * 86400000;
  });
  if (!toSend.length) return { ok: true, problems: problems.map(function (p) { return p.key; }), sent: false };
  var body = 'Bonjour,\n\nLa vérification quotidienne de Dépenses a trouvé ceci :\n\n' +
    toSend.map(function (p, i) { return (i + 1) + '. ' + p.text; }).join('\n\n') +
    '\n\nTableau de bord : ' + DASHBOARD_URL + '\n\n(Ce message est envoyé au plus une fois par semaine par problème.)';
  sendMail_('Dépenses : ' + (toSend.length === 1 ? 'une chose à vérifier' : toSend.length + ' choses à vérifier'), body, null);
  toSend.forEach(function (p) { props.setProperty('LAST_ALERT_' + p.key, String(nowMs)); });
  return { ok: true, problems: problems.map(function (p) { return p.key; }), sent: true };
}

/* ------------------------------------------------------------------ résumé du lundi */

function weeklyDigest_(force) {
  var props = PropertiesService.getScriptProperties();
  if (!force && props.getProperty('DIGEST') === 'off') return { ok: true, skipped: 'off' };
  var n = now_();
  var wk = weekKey_(n);
  if (!force) {
    if (weekdayLocal_(n) !== 1 || hourLocal_(n) < 8) return { ok: true, skipped: 'not-monday-morning' };
    if (props.getProperty('DIGEST_SENT') === wk) return { ok: true, skipped: 'done' };
  }
  var I = insights_();
  if (!I) return { ok: false, error: 'SpendInsights absent' };
  var rows = readTx_(sheet_(ss_(), TX_SHEET, TX_COLS), 0).map(function (r) { return out_(r, currency_()); });
  var h = health_(null);
  var lines = [];
  if (h.lastPhoneAt) lines.push('Dernière notification de l\'iPhone : ' + ago_(h.lastPhoneAt, n));
  if (h.lastEmailAt) lines.push('Dernier courriel d\'alerte lu : ' + ago_(h.lastEmailAt, n));
  Object.keys(h.bySource).forEach(function (src) { lines.push(sourceLabel_(src) + ' : ' + ago_(h.bySource[src], n)); });
  if (h.claude.on) lines.push('Claude : ' + h.claude.callsToday + ' lecture(s) aujourd\'hui, ' + h.claude.costMonthUsd.toFixed(2) + ' $ US ce mois-ci');
  var review = rows.filter(function (t) { return t.status === 'review'; }).length;
  var d = I.digest(rows, { now: n, currency: currency_(), budget: Number(props.getProperty('BUDGET') || 0), locale: 'fr', health: { lines: lines }, reviewCount: review, dashboardUrl: DASHBOARD_URL });
  sendMail_(d.subject, d.text, d.html);
  props.setProperty('DIGEST_SENT', wk);
  return { ok: true, sent: true, subject: d.subject };
}

function sendMail_(subject, text, html) {
  if (typeof MailApp === 'undefined') { Logger.log('MailApp absent : ' + subject); return false; }
  if (MailApp.getRemainingDailyQuota && MailApp.getRemainingDailyQuota() < 1) { Logger.log('Quota de courriels épuisé'); return false; }
  var to = Session.getEffectiveUser().getEmail();
  var opts = { to: to, subject: subject, body: text, name: 'Dépenses' };
  if (html) opts.htmlBody = html;
  MailApp.sendEmail(opts);
  return true;
}

/* ------------------------------------------------------------------ onglet Configuration */

var CONFIG_URL_ROW = 5; // la cellule « Adresse du script » (B5) peut être remplie à la main

function links_() {
  var props = PropertiesService.getScriptProperties();
  var url = String(props.getProperty('WEB_APP_URL') || '').trim();
  if (!url) {
    // L'adresse collée par l'utilisateur dans l'onglet Configuration.
    try {
      var sh = ss_().getSheetByName(CONFIG_SHEET);
      var typed = sh ? String(sh.getRange(CONFIG_URL_ROW, 2).getValue() || '').trim() : '';
      if (/^https:\/\/script\.google\.com\/\S+\/exec$/.test(typed)) url = typed;
    } catch (e) { /* pas encore d'onglet */ }
  }
  if (!url) {
    // Depuis l'éditeur, getUrl() renvoie parfois l'adresse de test (/dev), inutilisable.
    try { url = (ScriptApp.getService && ScriptApp.getService().getUrl()) || ''; } catch (e) { url = ''; }
    if (!/^https:\/\/\S+\/exec$/.test(url)) url = '';
  }
  if (url && props.getProperty('WEB_APP_URL') !== url) props.setProperty('WEB_APP_URL', url);
  var capture = props.getProperty('CAPTURE_TOKEN') || '';
  var admin = props.getProperty('ADMIN_TOKEN') || '';
  var setupLink = url ? DASHBOARD_URL + '#setup=' + base64url_(JSON.stringify({ u: url, k: admin, c: currency_() })) : '';
  return { webAppUrl: url, shortcutUrl: url ? url + '?token=' + capture : '', setupLink: setupLink };
}

function writeConfig_(ss) {
  var sh = ss.getSheetByName(CONFIG_SHEET) || ss.insertSheet(CONFIG_SHEET);
  var links = links_();
  var h = health_(null);
  var props = PropertiesService.getScriptProperties();
  var typed = String(sh.getRange(CONFIG_URL_ROW, 2).getValue() || '').trim();
  var rows = [
    ['Ne partagez pas cette feuille : cet onglet contient vos liens secrets.', ''],
    ['', ''],
    ['Lien de configuration (ouvre le tableau de bord déjà connecté)', links.setupLink || 'Adresse du script inconnue : collez l\'adresse de l\'application Web (…/exec) dans la cellule à droite de « Adresse du script », puis relancez setup.'],
    ['Lien du raccourci (action « Obtenir le contenu de l\'URL »)', links.shortcutUrl || ''],
    ['Adresse du script (…/exec)', links.webAppUrl || typed],
    ['Devise', currency_()],
    ['Version', VERSION],
    ['Déclencheur toutes les 15 min', props.getProperty('TRIGGER_INSTALLED') === 'yes' ? 'oui' : 'non : relancez setup et acceptez toutes les autorisations'],
    ['Lecture des courriels d\'alerte', props.getProperty('EMAIL') === 'off' ? 'non' : 'oui'],
    ['', ''],
    ['Santé de la capture', ''],
    ['Dernière notification (iPhone)', localTime_(h.lastPhoneAt)],
    ['Dernier test du raccourci', localTime_(h.shortcutPingAt)],
    ['Dernier courriel d\'alerte lu', localTime_(h.lastEmailAt)],
    ['Raccourci mal configuré', h.misconfiguredAt ? 'oui, le ' + localTime_(h.misconfiguredAt) : 'non'],
    ['Ancien lien utilisé', h.staleHits ? h.staleHits + ' fois, dernière le ' + localTime_(h.lastStaleAt) : 'non'],
    ['Claude', h.claude.on ? h.claude.mode + ' · ' + h.claude.model + ' · ' + h.claude.callsToday + ' lecture(s) aujourd\'hui' : 'désactivé'],
    ['Mis à jour le', localTime_(now_().toISOString())]
  ];
  sh.getRange(1, 1, rows.length, 2).setNumberFormats(rows.map(function () { return ['@', '@']; })).setValues(rows);
  return links;
}

function localTime_(iso) {
  var d = date_(iso);
  return d ? Utilities.formatDate(d, tz_(), 'yyyy-MM-dd HH:mm') : 'jamais';
}

/* ================================================================== Claude (facultatif, en différé) */

function claudeConfig_() {
  var p = PropertiesService.getScriptProperties();
  var key = String(p.getProperty('ANTHROPIC_API_KEY') || '').trim();
  var mode = String(p.getProperty('CLAUDE_MODE') || CLAUDE_DEFAULT_MODE).trim().toLowerCase();
  if (!key || mode === 'off') return null;
  return {
    key: key, mode: mode === 'always' ? 'always' : 'review', model: String(p.getProperty('CLAUDE_MODEL') || CLAUDE_DEFAULT_MODEL).trim(),
    maxPerDay: Number(p.getProperty('CLAUDE_MAX_PER_DAY')) || CLAUDE_MAX_PER_DAY, maxMonthUsd: Number(p.getProperty('CLAUDE_MAX_MONTH_USD')) || CLAUDE_MAX_MONTH_USD
  };
}

function shouldAskClaude_(cfg, r) {
  if (cfg.mode === 'always') return true;
  return r.kind === 'transaction' ? r.status === 'review' : (r.reason === 'no-amount' || r.reason === 'not-a-spend');
}

function claudeBudgetLeft_(cfg) {
  var p = PropertiesService.getScriptProperties();
  var today = dayKey_(now_());
  var calls = Number(p.getProperty('CLAUDE_CALLS_' + today) || 0);
  var cost = Number(p.getProperty('CLAUDE_COST_' + today.slice(0, 7)) || 0);
  return calls < cfg.maxPerDay && cost < cfg.maxMonthUsd;
}

function claudeRecord_(msg) {
  var p = PropertiesService.getScriptProperties();
  var today = dayKey_(now_());
  p.setProperty('CLAUDE_CALLS_' + today, String(Number(p.getProperty('CLAUDE_CALLS_' + today) || 0) + 1));
  var monthKey = 'CLAUDE_COST_' + today.slice(0, 7);
  p.setProperty(monthKey, String(Number(p.getProperty(monthKey) || 0) + claudeCostUsd_(msg)));
}

// Relit avec Claude ce que les règles n'ont pas compris : lignes « pending », et notifications ignorées
// faute de montant reconnu. Au plus quelques appels par passage, dans les plafonds.
function enrichPending_() {
  var cfg = claudeConfig_();
  if (!cfg) return { ok: true, skipped: 'off' };
  var ss = ss_();
  var cur = currency_();
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
  var rules = readRules_(ss);
  var ctx = claudeContext_(sheet, rules, cur);
  var done = 0;
  var pending = readTx_(sheet, 200).filter(function (r) { return r.reader === 'pending'; });
  for (var i = 0; i < pending.length && done < 10; i++) {
    if (!claudeBudgetLeft_(cfg)) break;
    var p = pending[i];
    var parts = p.raw.split(' | ');
    var c = claudeRead_(cfg, ctx, { app: '', title: parts.length > 1 ? parts[0] : '', subtitle: parts.length > 2 ? parts[1] : '', body: parts[parts.length - 1], received: p.captured_at || now_() }, false);
    done++;
    // La ligne est retrouvée par son identifiant, sous verrou : elle a pu bouger ou être modifiée pendant l'appel.
    withLock_(function () {
      var rowNo = findRow_(sheet, p.id);
      if (!rowNo) return;
      var r = rowObj_(sheet.getRange(rowNo, 1, 1, TX_COLS.length).getValues()[0]);
      if (r.reader !== 'pending') return;
      if (!c) { r.reader = 'rules'; writeRow_(sheet, rowNo, TX_COLS, TX_FORMATS, r); return; }
      if (c.kind === 'ignore') {
        r.reader = 'claude';
        if (r.status === 'ok' || r.status === 'review') { r.status = 'review'; r.note = [r.note, 'Claude pense que ce n\'est pas une transaction (' + reasonLabel_(c.reason) + ')'].filter(String).join(' · '); }
        writeRow_(sheet, rowNo, TX_COLS, TX_FORMATS, r);
        return;
      }
      var disagree = Math.abs(Math.abs(r.amount) - c.amount) > 0.005 || r.currency !== c.currency || (r.type !== c.type && r.status === 'ok');
      var ruled = applyRules_({ merchant: c.merchant, type: c.type, category: c.category }, rules);
      if (disagree) {
        r.status = 'review';
        r.note = [r.note, 'Claude lit ' + c.amount.toFixed(2) + ' ' + c.currency + ' · ' + (c.merchant || '?') + ' (' + c.type + ')'].filter(String).join(' · ');
      } else {
        if (!r.merchant && c.merchant) r.merchant = ruled.name || c.merchant;
        if (r.category === 'Other' || !r.category) r.category = ruled.category || c.category;
        if (!r.card && c.card) r.card = c.card;
        // Une ligne « à vérifier » à cause d'un doublon possible le reste : Claude ne tranche pas ça.
        if (r.status === 'review' && c.status === 'ok' && !/\bdup\b/.test(r.flags)) r.status = 'ok';
      }
      r.reader = 'claude';
      writeRow_(sheet, rowNo, TX_COLS, TX_FORMATS, r);
    });
  }
  // Notifications ignorées des 2 derniers jours qui contiennent un chiffre : peut-être un format inconnu.
  var ish = ss.getSheetByName(IGNORED_SHEET);
  var rescued = 0;
  if (ish && ish.getLastRow() >= 2 && claudeBudgetLeft_(cfg)) {
    var last = ish.getLastRow();
    var start = Math.max(2, last - 60);
    var vals = ish.getRange(start, 1, last - start + 1, IGNORED_COLS.length).getValues();
    var since = now_().getTime() - 2 * 86400000;
    for (var j = vals.length - 1; j >= 0 && done < 10; j--) {
      var when = date_(vals[j][0]);
      var reason = String(vals[j][2]);
      var raw = String(vals[j][3]);
      if (!when || when.getTime() < since || !/\d/.test(raw) || ['no-amount', 'not-a-spend', 'other'].indexOf(reason) < 0) continue;
      if (!claudeBudgetLeft_(cfg)) break;
      var p2 = raw.split(' | ');
      var c2 = claudeRead_(cfg, ctx, { app: '', title: p2.length > 1 ? p2[0] : '', subtitle: p2.length > 2 ? p2[1] : '', body: p2[p2.length - 1], received: when }, false);
      done++;
      var source2 = String(vals[j][1] || 'phone');
      withLock_(function () {
        // La ligne ignorée est retrouvée (date + texte) : la feuille a pu changer pendant l'appel.
        var rowNo = findIgnoredRow_(ish, when, raw);
        if (!rowNo) return;
        if (!c2 || c2.kind !== 'transaction') { ish.getRange(rowNo, 3).setValue(reason === 'other' ? reason : reason + ' (claude)'); return; }
        var ruled2 = applyRules_({ merchant: c2.merchant, type: c2.type, category: c2.category }, rules);
        var tx = {
          id: newId_(), date: when, amount: SpendParser.signedAmount(c2.amount, c2.type), currency: c2.currency,
          merchant: ruled2.name || c2.merchant, category: ruled2.category || c2.category, type: c2.type, card: c2.card,
          status: 'review', note: 'Lu par Claude (les règles n\'avaient pas compris)', source: source2, raw: raw,
          captured_at: now_(), reader: 'claude', flags: ''
        };
        var recent = readTx_(sheet, DEDUP_ROWS);
        tx.flags = flags_(tx, recent);
        var dup = findDuplicate_(recent, tx);
        if (dup) applyDuplicate_(tx, dup);
        appendRow_(sheet, TX_COLS, TX_FORMATS, tx);
        ish.deleteRow(rowNo);
        rescued++;
      });
    }
  }
  return { ok: true, calls: done, rescued: rescued };
}

function withLock_(fn) {
  var lock = LockService.getScriptLock();
  var locked = false;
  try { locked = lock.tryLock(15000); } catch (e) { locked = false; }
  if (!locked) { Logger.log('Feuille occupée : opération remise au prochain passage'); return false; }
  try { fn(); } finally { try { lock.releaseLock(); } catch (ignored) { /* rien */ } }
  return true;
}

function findIgnoredRow_(sh, when, raw) {
  var last = sh.getLastRow();
  if (last < 2) return 0;
  var start = Math.max(2, last - 400);
  var vals = sh.getRange(start, 1, last - start + 1, IGNORED_COLS.length).getValues();
  for (var i = vals.length - 1; i >= 0; i--) {
    var d = date_(vals[i][0]);
    if (d && when && Math.abs(d.getTime() - when.getTime()) < 2000 && String(vals[i][3]) === String(raw)) return start + i;
  }
  return 0;
}

// Ce que Claude reçoit en plus de la notification : la devise, les catégories, les règles et la
// catégorie déjà utilisée pour les marchands récents, pour classer comme l'utilisateur.
function claudeContext_(sheet, rules, cur) {
  var cats = SpendParser.CATEGORIES.map(function (c) { return c.name; });
  rules.forEach(function (r) { if (cats.indexOf(r.category) < 0 && !/^\(/.test(r.category)) cats.push(r.category); });
  var seen = {};
  var past = [];
  readTx_(sheet, 120).reverse().forEach(function (t) {
    if (t.category && cats.indexOf(t.category) < 0) cats.push(t.category);
    var k = SpendParser.fold(t.merchant);
    if (!t.merchant || seen[k] || t.status === 'duplicate' || past.length >= 40) return;
    seen[k] = true;
    past.push(t.merchant + ' -> ' + (t.category || 'Other'));
  });
  return { currency: cur, categories: cats, rules: rules, past: past };
}

function claudePrompt_(ctx, n) {
  var system = [
    'You read push notifications and alert emails from banking and credit-card apps for a personal spending tracker, and turn each one into one record that follows the JSON schema.',
    'is_transaction is true only when the notification reports money that moved or was authorized on the user\'s account or card: a purchase, refund, cash withdrawal, fee, income or transfer. Promotions, rewards or cash back earned, balances, statements, reminders of upcoming payments, declined or blocked transactions, security codes and sign-in alerts are not transactions: set is_transaction to false and choose the ignore_reason that fits.',
    'amount is the amount of that transaction as a positive number in major units, never a balance or an available credit. Texts can be in French or English, with amounts written like "1 234,56 $" or "$1,234.56". When a foreign amount and its conversion are both given, use the amount in ' + ctx.currency + '.',
    'currency is an ISO 4217 code. A bare "$" means ' + ctx.currency + ' unless the text says otherwise (US$, USD, CA$, BSD...).',
    'type is purchase for spending (bill payments and pre-authorized debits included), refund for money returned on a purchase, cash for an ATM withdrawal, fee for bank fees and interest charged, income for salary, deposits and interest earned, transfer for credit card payments, e-transfers, investment contributions and moves between accounts.',
    'merchant is the business or person as written, without the card or bank name; leave it empty when there is none.',
    'card is a short label such as "Visa ••1234" when the notification names the card; otherwise leave it empty.',
    'category is one of the user\'s categories. Follow the user\'s rules first, then the category already used for the same merchant.',
    'confidence is high when the amount and the merchant are stated plainly, and low when you had to guess either one.',
    'When is_transaction is false, set amount to 0, the text fields to empty strings, type to "purchase" and category to "Other".'
  ].join('\n\n');
  var lines = ['Default currency: ' + ctx.currency, 'Categories: ' + ctx.categories.join(', ')];
  lines.push('Rules (pattern -> category, the first match wins):' + (ctx.rules.length ? '' : ' none'));
  ctx.rules.slice(0, 50).forEach(function (r) { lines.push('- ' + r.pattern + ' -> ' + r.category); });
  lines.push('Categories used before for recent merchants:' + (ctx.past.length ? '' : ' none'));
  ctx.past.forEach(function (p) { lines.push('- ' + p); });
  lines.push('', 'Notification received ' + n.received.toISOString() + (n.app ? ' from the app "' + n.app + '"' : '') + ':');
  lines.push('title: ' + mask_(n.title));
  lines.push('subtitle: ' + mask_(n.subtitle));
  lines.push('body: ' + mask_(n.body));
  return { system: system, user: lines.join('\n') };
}

// Codes à usage unique et numéros de compte ne sortent pas de Google.
function mask_(s) {
  return SpendParser.redactCodes(s).replace(/\b\d{6,}\b/g, '••••••');
}

// L'objet JSON lu, ou null si l'appel échoue, est refusé ou coupé.
function claudeCall_(cfg, prompt, verbose) {
  var body = {
    model: cfg.model,
    max_tokens: 4000,
    system: prompt.system,
    messages: [{ role: 'user', content: prompt.user }],
    output_config: { effort: 'low', format: { type: 'json_schema', schema: CLAUDE_SCHEMA } }
  };
  var headers = { 'x-api-key': cfg.key, 'anthropic-version': '2026-10-21' };
  // Repli côté serveur si un classificateur refuse ; Haiku ne le propose pas.
  if (!/haiku/i.test(cfg.model)) {
    body.fallbacks = 'default';
    headers['anthropic-beta'] = 'server-side-fallback-2026-07-01';
  }
  try {
    var res = UrlFetchApp.fetch(CLAUDE_URL, {
      method: 'post', contentType: 'application/json', headers: headers, payload: JSON.stringify(body), muteHttpExceptions: true
    });
    var code = res.getResponseCode();
    var text = res.getContentText();
    if (code !== 200) {
      Logger.log('Claude : HTTP ' + code + ' ' + text.slice(0, 300));
      return null;
    }
    var msg = JSON.parse(text);
    claudeRecord_(msg);
    if (verbose) Logger.log('Claude : ' + msg.model + ', stop ' + msg.stop_reason + ', ' + claudeCost_(msg));
    if (msg.stop_reason === 'refusal' || msg.stop_reason === 'max_tokens') return null;
    var texts = (msg.content || []).filter(function (b) { return b.type === 'text' && b.text; });
    return texts.length ? JSON.parse(texts[texts.length - 1].text) : null;
  } catch (err) {
    Logger.log('Claude : ' + err);
    return null;
  }
}

function claudeCostUsd_(msg) {
  var u = (msg && msg.usage) || {};
  var tokensIn = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
  var tokensOut = u.output_tokens || 0;
  var price = CLAUDE_PRICES[msg && msg.model] || CLAUDE_PRICES[CLAUDE_DEFAULT_MODEL];
  return (tokensIn * price[0] + tokensOut * price[1]) / 1e6;
}

function claudeCost_(msg) {
  var u = msg.usage || {};
  var tokensIn = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
  return tokensIn + ' tokens in, ' + (u.output_tokens || 0) + ' out ≈ $' + claudeCostUsd_(msg).toFixed(4);
}

// La réponse de Claude vérifiée ; null = garder la lecture des règles.
function claudeRead_(cfg, ctx, n, verbose) {
  var j = claudeCall_(cfg, claudePrompt_(ctx, n), verbose);
  if (!j || typeof j.is_transaction !== 'boolean') return null;
  if (!j.is_transaction) return { kind: 'ignore', reason: CLAUDE_REASONS.indexOf(j.ignore_reason) > 0 ? j.ignore_reason : 'other' };
  var amount = Math.abs(Number(j.amount));
  if (!(amount > 0) || !isFinite(amount)) return null;
  var type = SpendParser.TYPES.indexOf(j.type) >= 0 ? j.type : 'purchase';
  var currency = String(j.currency || '').trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) currency = ctx.currency;
  var merchant = str_(j.merchant, 60);
  var spending = type === 'purchase' || type === 'refund';
  var category;
  if (!spending) {
    category = SpendParser.categorize('', ctx.rules, type);
  } else {
    var fm = SpendParser.fold(merchant);
    var ruled = '';
    ctx.rules.forEach(function (r) { if (!ruled && SpendParser.matchRule(fm, r.pattern)) ruled = r.category; });
    category = ruled || (ctx.categories.indexOf(j.category) >= 0 ? j.category : SpendParser.categorize(merchant, ctx.rules, type));
  }
  return {
    kind: 'transaction', type: type, amount: Math.round(amount * 100) / 100, currency: currency, merchant: merchant,
    card: str_(j.card, 40), category: category, status: j.confidence === 'low' || (spending && !merchant) ? 'review' : 'ok'
  };
}

/** Lit trois notifications d'exemple avec Claude et note le résultat et le coût. */
function testClaude() {
  var cfg = claudeConfig_();
  if (!cfg) { Logger.log('Claude est désactivé : ajoutez ANTHROPIC_API_KEY dans Paramètres du projet > Propriétés du script.'); return; }
  var ss = ss_();
  var ctx = claudeContext_(sheet_(ss, TX_SHEET, TX_COLS), readRules_(ss), currency_());
  [
    { app: 'Banque Scotia', title: 'InfoAlerte Scotia', body: 'Un achat de 54,21 $ a été effectué chez IGA EXTRA avec votre carte se terminant par 1234.' },
    { app: 'Cartes', title: 'Visa Scotia', subtitle: 'Starbucks', body: '5,75 $' },
    { app: 'Capital One', title: 'Capital One', body: 'Your verification code is 482913' }
  ].forEach(function (n) {
    var out = claudeRead_(cfg, ctx, { app: n.app, title: n.title || '', subtitle: n.subtitle || '', body: n.body, received: now_() }, true);
    Logger.log(JSON.stringify(n) + '\n  -> ' + JSON.stringify(out));
  });
}

/* ================================================================== feuille */

function ss_() {
  var id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  var ss = id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Lancez setup() dans l\'éditeur Apps Script d\'abord.');
  return ss;
}

function ensureSheet_(ss, name, cols) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  var header = sh.getRange(1, 1, 1, cols.length).getValues()[0];
  if (header.join('') === '') {
    sh.getRange(1, 1, 1, cols.length).setValues([cols]).setFontWeight('bold');
    sh.setFrozenRows(1);
  } else {
    for (var i = 0; i < cols.length; i++) {
      if (header[i] !== '' && String(header[i]).trim().toLowerCase() !== cols[i]) {
        throw new Error('L\'onglet « ' + name + ' » a été modifié : la colonne ' + (i + 1) + ' devrait s\'appeler « ' + cols[i] + ' » et s\'appelle « ' + header[i] + ' ». Remettez les colonnes dans l\'ordre d\'origine.');
      }
    }
    if (header.some(function (h) { return h === ''; })) {
      // Une version plus récente a ajouté des colonnes : on écrit leur titre.
      sh.getRange(1, 1, 1, cols.length).setValues([cols.map(function (c, i) { return header[i] === '' ? c : header[i]; })]);
    }
  }
  return sh;
}

function sheet_(ss, name, cols) {
  return ss.getSheetByName(name) || ensureSheet_(ss, name, cols);
}

function currency_() {
  return PropertiesService.getScriptProperties().getProperty('CURRENCY') || 'CAD';
}

function currencyFromLocale_(ss) {
  var loc = '';
  try { loc = String(ss.getSpreadsheetLocale ? ss.getSpreadsheetLocale() : ''); } catch (e) { loc = ''; }
  var region = (loc.split(/[_-]/)[1] || '').toUpperCase();
  var map = { CA: 'CAD', US: 'USD', GB: 'GBP', CH: 'CHF', AU: 'AUD', NZ: 'NZD', BS: 'BSD', MX: 'MXN', JP: 'JPY', IN: 'INR' };
  if (map[region]) return map[region];
  if (/^(FR|BE|DE|ES|IT|NL|PT|IE|AT|FI|LU|GR|SK|SI|EE|LV|LT|MT|CY|HR)$/.test(region)) return 'EUR';
  if (/^fr$/i.test(loc)) return 'EUR';
  return 'CAD';
}

function rowObj_(values) {
  var o = {};
  for (var j = 0; j < TX_COLS.length; j++) o[TX_COLS[j]] = values[j];
  ['currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id', 'reader', 'flags'].forEach(function (k) {
    o[k] = o[k] === null || o[k] === undefined ? '' : String(o[k]).trim();
  });
  o.status = o.status.toLowerCase();
  o.type = o.type.toLowerCase();
  o.currency = o.currency.toUpperCase();
  if (o.status && STATUSES.indexOf(o.status) < 0) o.status = /dou?bl|dup/.test(o.status) ? 'duplicate' : /excl|ignor/.test(o.status) ? 'excluded' : /v[ée]rif|review|check/.test(o.status) ? 'review' : 'ok';
  if (o.type && SpendParser.TYPES.indexOf(o.type) < 0) o.type = /rembours|refund/.test(o.type) ? 'refund' : /virement|transfer/.test(o.type) ? 'transfer' : /revenu|income/.test(o.type) ? 'income' : /comptant|cash/.test(o.type) ? 'cash' : /frais|fee/.test(o.type) ? 'fee' : 'purchase';
  o.amount = Number(o.amount) || 0;
  o.date = date_(o.date);
  o.captured_at = date_(o.captured_at);
  return o;
}

function readTx_(sheet, lastN) {
  var last = sheet.getLastRow();
  if (last < 2) return [];
  var start = lastN ? Math.max(2, last - lastN + 1) : 2;
  var values = sheet.getRange(start, 1, last - start + 1, TX_COLS.length).getValues();
  var out = [];
  for (var i = 0; i < values.length; i++) {
    if (values[i].join('') === '') continue;
    var o = rowObj_(values[i]);
    o._row = start + i;
    out.push(o);
  }
  return out;
}

function readIgnored_(ss, days) {
  var sh = ss.getSheetByName(IGNORED_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  var last = sh.getLastRow();
  var start = Math.max(2, last - 400 + 1);
  var since = now_().getTime() - days * 86400000;
  return sh.getRange(start, 1, last - start + 1, IGNORED_COLS.length).getValues().reverse().map(function (r) {
    var d = date_(r[0]);
    return { captured_at: d ? d.toISOString() : null, source: String(r[1]), reason: String(r[2]), raw: String(r[3]) };
  }).filter(function (x) { return !x.captured_at || new Date(x.captured_at).getTime() >= since; });
}

function readRules_(ss) {
  var sh = ss.getSheetByName(RULES_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, RULES_COLS.length).getValues()
    .filter(function (r) { return String(r[0]).trim() && String(r[1]).trim(); })
    .map(function (r) { return { pattern: String(r[0]).trim(), category: String(r[1]).trim(), name: String(r[2] || '').trim() }; });
}

function writeRules_(ss, rules) {
  var sh = sheet_(ss, RULES_SHEET, RULES_COLS);
  var last = sh.getLastRow();
  if (last >= 2) sh.getRange(2, 1, last - 1, RULES_COLS.length).clearContent();
  if (!rules.length) return;
  sh.getRange(2, 1, rules.length, RULES_COLS.length)
    .setNumberFormats(rules.map(function () { return ['@', '@', '@']; }))
    .setValues(rules.map(function (r) { return [r.pattern, r.category, r.name || '']; }));
}

function appendRow_(sheet, cols, formats, o) {
  var row = sheet.getLastRow() + 1;
  writeRow_(sheet, row, cols, formats, o);
  return row;
}

// Les colonnes de texte sont mises en format texte d'abord, pour que « 7-11 » ne devienne jamais une date.
function writeRow_(sheet, row, cols, formats, o) {
  var range = sheet.getRange(row, 1, 1, cols.length);
  range.setNumberFormats([formats]);
  range.setValues([cols.map(function (c) { return o[c] === null || o[c] === undefined ? '' : o[c]; })]);
}

function appendIgnored_(ss, o) {
  var sh = sheet_(ss, IGNORED_SHEET, IGNORED_COLS);
  appendRow_(sh, IGNORED_COLS, IGNORED_FORMATS, o);
  var extra = sh.getLastRow() - 1 - IGNORED_MAX;
  if (extra > 0) sh.deleteRows(2, extra);
}

function findRow_(sheet, id) {
  if (!id) return 0;
  var last = sheet.getLastRow();
  if (last < 2) return 0;
  var ids = sheet.getRange(2, TX_COLS.indexOf('id') + 1, last - 1, 1).getValues();
  for (var i = ids.length - 1; i >= 0; i--) {
    if (String(ids[i][0]) === String(id)) return i + 2;
  }
  return 0;
}

/* ================================================================== petits utilitaires */

function out_(o, cur) {
  var type = o.type || (o.amount < 0 ? 'refund' : 'purchase');
  return {
    id: o.id, date: o.date ? o.date.toISOString() : null, amount: Math.round(o.amount * 100) / 100,
    currency: o.currency || cur, merchant: o.merchant || '', category: o.category || 'Other', type: type,
    card: o.card || '', status: o.status || 'ok', note: o.note || '', source: o.source || 'sheet', raw: o.raw || '',
    captured_at: o.captured_at ? o.captured_at.toISOString() : null, reader: o.reader || '', flags: o.flags || ''
  };
}

function message_(tx) {
  var amount = Math.abs(tx.amount).toFixed(2).replace('.', ',') + ' ' + (tx.currency === 'CAD' ? '$' : tx.currency);
  var cat = catLabel_(tx.category);
  var s = (tx.amount < 0 ? '+' : '') + amount + ' · ' + (tx.merchant || '?') + ' · ' + cat;
  if (tx.status === 'review') s += ' (à vérifier)';
  if (tx.status === 'duplicate') s += ' (doublon probable, non compté)';
  if (tx.status === 'excluded') s += ' (ignoré par une règle)';
  return '✓ ' + s;
}

function catLabel_(name) {
  for (var i = 0; i < SpendParser.CATEGORIES.length; i++) if (SpendParser.CATEGORIES[i].name === name) return SpendParser.CATEGORIES[i].fr || name;
  return name;
}

function reasonLabel_(reason) {
  return { 'no-amount': 'aucun montant', 'not-a-spend': 'solde ou récompense', promo: 'promotion', declined: 'refusée', upcoming: 'à venir', statement: 'relevé', empty: 'vide', raccourci: 'raccourci mal configuré', 'rate-limit': 'trop de notifications', suspect: 'courriel suspect', other: 'autre' }[reason] || reason;
}

function sourceLabel_(source) {
  var parts = String(source || '').split(':');
  var chan = { phone: 'iPhone', email: 'courriel', manual: 'saisie', paste: 'texte collé', statement: 'relevé', applepay: 'Apple Pay', sheet: 'feuille' }[parts[0]] || parts[0];
  var bank = { scotia: 'Scotia', capitalone: 'Capital One', wealthsimple: 'Wealthsimple', cartes: 'Cartes', desjardins: 'Desjardins', rbc: 'RBC', td: 'TD', bmo: 'BMO', cibc: 'CIBC', tangerine: 'Tangerine' }[parts[1]] || parts[1];
  return bank ? bank + ' · ' + chan : chan;
}

function cardDigits_(c) {
  var m = /(\d{4,5})\D*$/.exec(String(c || ''));
  return m ? m[1] : '';
}

function minutesAgo_(a, b) { return Math.max(0, Math.round(Math.abs(b.getTime() - a.getTime()) / 60000)); }

function ago_(iso, now) {
  var ms = now.getTime() - new Date(iso).getTime();
  if (!isFinite(ms)) return '?';
  var m = Math.round(ms / 60000);
  if (m < 60) return 'il y a ' + m + ' min';
  var h = Math.round(m / 60);
  if (h < 48) return 'il y a ' + h + ' h';
  return 'il y a ' + Math.round(h / 24) + ' jours';
}

// L'heure d'une capture : la date du téléphone seulement si elle est proche ; celle d'un courriel ou d'un relevé toujours.
function when_(v, trusted) {
  var d = date_(v);
  if (!d) return null;
  if (trusted) return d;
  var n = now_();
  return Math.abs(d.getTime() - n.getTime()) < 3 * 86400000 ? d : null;
}

function date_(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v.getTime === 'function') return isNaN(v.getTime()) ? null : v;
  var d = typeof v === 'number' ? new Date(v < 1e12 ? v * 1000 : v) : new Date(String(v));
  return isNaN(d.getTime()) ? null : d;
}

// Remplacée dans les tests pour fixer l'heure.
function now_() { return new Date(); }

function tz_() {
  try { return Session.getScriptTimeZone() || 'America/Toronto'; } catch (e) { return 'America/Toronto'; }
}
function dayKey_(d) { return Utilities.formatDate(d, tz_(), 'yyyy-MM-dd'); }
function hourLocal_(d) { return Number(Utilities.formatDate(d, tz_(), 'H')); }
function weekdayLocal_(d) { return Number(Utilities.formatDate(d, tz_(), 'u')) % 7; } // 1 = lundi … 0 = dimanche
function weekKey_(d) {
  // Semaine ISO, calculée sur la date locale.
  var key = dayKey_(d).split('-');
  var date = new Date(Date.UTC(Number(key[0]), Number(key[1]) - 1, Number(key[2])));
  var day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  var yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return date.getUTCFullYear() + '-W' + Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
}

function insights_() { return typeof SpendInsights !== 'undefined' ? SpendInsights : null; }

function str_(v, max) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/\s+/g, ' ').trim().slice(0, max || 200);
}

function blank_(v) {
  return v === null || v === undefined || String(v).trim() === '';
}

function first_() {
  for (var i = 0; i < arguments.length; i++) {
    if (!blank_(arguments[i])) return arguments[i];
  }
  return '';
}

function base64url_(s) {
  var bytes = Utilities.newBlob(s).getBytes();
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, '');
}

function newId_() {
  return 't' + Utilities.getUuid().replace(/-/g, '').slice(0, 12);
}

function newToken_() {
  return Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '').slice(0, 8);
}
