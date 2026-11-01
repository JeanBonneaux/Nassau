/*
 * SpendParser: reads the text of a bank or credit-card notification and pulls out
 * the transaction in it (amount, currency, merchant, card, type, category).
 *
 * One source, two consumers:
 *   - the Google Apps Script backend (tools/build.mjs copies this file to apps-script/Parser.gs)
 *   - the dashboard (inlined into index.html for the "paste a notification" preview and demo data)
 * Plain JavaScript, no dependencies, no modules: it defines one global, `SpendParser`.
 */
var SpendParser = (function () {
  'use strict';

  var VERSION = '0.2.0';

  /* ------------------------------------------------------------------ categories */

  // Stored keys stay in English (rules, sheet); `fr` is the display label.
  var CATEGORIES = [
    { name: 'Groceries', fr: 'Épicerie', icon: '🛒' },
    { name: 'Dining', fr: 'Restos', icon: '🍽️' },
    { name: 'Transport', fr: 'Transport', icon: '🚗' },
    { name: 'Travel', fr: 'Voyage', icon: '✈️' },
    { name: 'Shopping', fr: 'Achats', icon: '🛍️' },
    { name: 'Subscriptions', fr: 'Abonnements', icon: '🔁' },
    { name: 'Bills', fr: 'Factures', icon: '🧾' },
    { name: 'Health', fr: 'Santé', icon: '💊' },
    { name: 'Entertainment', fr: 'Sorties', icon: '🎟️' },
    { name: 'Cash', fr: 'Comptant', icon: '💵' },
    { name: 'Fees', fr: 'Frais', icon: '🏦' },
    { name: 'Other', fr: 'Autre', icon: '🏷️' },
    { name: 'Income', fr: 'Revenus', icon: '💰' },
    { name: 'Transfers', fr: 'Virements', icon: '🔄' }
  ];

  // purchase / cash / fee are money out; refund is money back on a purchase.
  // income and transfer are recorded but never count as spending.
  var TYPES = ['purchase', 'refund', 'cash', 'fee', 'income', 'transfer'];
  var SPENDING_TYPES = { purchase: true, refund: true, cash: true, fee: true };

  // Matched against the merchant, accents removed and lower-cased. First match wins;
  // user rules (Rules sheet) are checked before these.
  var DEFAULT_RULES = [
    [/uber ?\*? ?eats|ubereats|doordash|skip ?the ?dishes|deliveroo|just ?eat|foodora|grubhub/, 'Dining'],
    [/amazon prime|prime video|amzn digital|kindle|audible|apple\.com|itunes|icloud|netflix|spotify|disney ?(?:plus|\+)|disneyplus|crave|hbo|paramount|dazn|youtube|google \*|google play|google one|\bgoogle\b|adobe|microsoft|game ?pass|playstation plus|dropbox|openai|chatgpt|anthropic|claude\.ai|patreon|substack|nytimes|duolingo|deezer|tidal|siriusxm|illico|tou\.tv/, 'Subscriptions'],
    [/pharma|pharmacy|jean coutu|shoppers drug|uniprix|familiprix|proxim|brunet|\bcvs\b|walgreens|rexall|london drugs|clinic|clinique|dental|dentist|dentaire|medical|medecin|doctor|hospital|hopital|optometr|optique|lunetterie|physio|massotherap|chiro|\bgym\b|fitness|yoga|crossfit|goodlife|econofitness|energie cardio|ymca|nautilus/, 'Health'],
    [/hydro|electric|electricite|energir|gaz metro|(?<!centre )\bbell\b(?! centre)|rogers|(?<!centre )videotron|telus|\bfido\b|koodo|virgin plus|freedom mobile|public mobile|chatr|\bfizz\b|cogeco|\boxio\b|\bebox\b|verizon|at&t|t-mobile|comcast|xfinity|\bsfr\b|bouygues|free mobile|insurance|assurance|\bintact\b|belairdirect|\bloyer\b|\brent\b(?!-?a-?car| a car)|internet|\bpower\b|utilit|wireless|telecom|phone co\b|mobile phone|\bbpl\b|\bbtc\b|\baliv\b/, 'Bills'],
    [/restaurant|resto\b|cafe|coffee|starbucks|tim hortons|\btims\b|second cup|mcdonald|\bmcdo\b|burger|pizz|sushi|subway|\bkfc\b|a&w|wendy|chipotle|taco|poutine|st-?hubert|boulangerie|bakery|patisserie|bistro|brasserie|grill|\bpub\b|(?<!gas )\bbar\b|tavern|pret a manger|\bpret\b|dunkin|five guys|domino|nando|\bthai\b|\bpho\b|ramen|diner|eatery|cantina|creperie|bagel|donut|doughnut|smoothie|gelato|dairy queen|chick-fil-a|panera|popeyes|benny|la belle province|trattoria|taqueria|\bbbq\b|steakhouse|cafeteria|chez cora|\bcora\b|valentine|harvey'?s|normandin|ashton|lafleur|\bmikes\b|\bscores\b|pacini|van houtte|cafe depot|premiere moisson|juice|jus\b/, 'Dining'],
    [/grocer|supermarket|supermarche|epicerie|marche|market|\biga\b|\bmetro\b|\bmaxi\b|provigo|loblaw|sobeys|safeway|super ?c\b|adonis|costco(?! ?(?:gas|essence|fuel))|walmart|wal-mart|whole ?foods|trader joe|kroger|publix|\baldi\b|\blidl\b|carrefour|monoprix|monop\b|franprix|leclerc|auchan|intermarche|super ?u\b|picard|solomon|super ?value|food ?store|no ?frills|freshco|save-on|instacart|fruiterie|boucherie|fromagerie|depanneur|couche-tard|circle k|7-?eleven|pa nature|\bavril\b|rachelle|bulk barn|kim phat|mayrand|\bsaq\b|\bsqdc\b|\blcbo\b|beer store/, 'Groceries'],
    [/shell|\besso\b|petro|ultramar|harnois|crevier|costco ?(?:gas|essence|fuel)|gas bar|chevron|exxon|\bmobil\b|\bbp\b|texaco|sunoco|irving|husky|total ?energies|gas station|\bgas\b|fuel|essence|carburant|uber|lyft|taxi|\bcab\b|\bstm\b|\bopus\b|presto|transit|\bexo\b|\brem\b|\brtl\b|\bstl\b|p\$ ?mobile|\bflo\b|circuit electrique|chargepoint|supercharger|bixi|communauto|\bratp\b|\bsncf\b|navigo|via rail|amtrak|greyhound|parking|stationnement|impark|indigo park|\btoll\b|peage|407 etr|zipcar|car wash|lave-auto|\bsaaq\b|\bdmv\b/, 'Transport'],
    [/air canada|westjet|porter air|air transat|\bflair\b|delta air|united air|american air|jetblue|southwest|spirit air|air france|\bklm\b|british airways|lufthansa|bahamasair|airline|airways|airbnb|\bvrbo\b|booking\.com|expedia|hotels\.com|hotel|marriott|hilton|hyatt|sheraton|westin|fairmont|holiday inn|best western|resort|motel|auberge|\binn\b|hostel|ferry|ferries|cruise|car rental|hertz|\bavis\b|enterprise rent|budget rent|\bturo\b|duty free|airport|aeroport/, 'Travel'],
    [/amazon|amzn|best ?buy|ikea|winners|marshalls|homesense|tj ?maxx|h&m|\bzara\b|uniqlo|\bgap\b|old navy|simons|la baie|hudson'?s bay|sephora|etsy|ebay|shein|temu|aliexpress|canadian tire|home depot|\brona\b|lowe'?s|dollarama|dollar tree|target|apple store|\bapple\b|chapters|\bmec\b|sport chek|decathlon|\bfnac\b|darty|\bboulanger\b|lululemon|\bnike\b|adidas|john bull|staples|bureau en gros|structube|wayfair|renaud-?bray|archambault|reno-?depot|\bbmr\b|patrick morin|sports experts|ardene|aubainerie|brault|linen chest|\bjysk\b/, 'Shopping'],
    [/cinema|cineplex|theatre|theater|ticketmaster|evenko|stubhub|eventbrite|spectacle|concert|museum|musee|steam|playstation|nintendo|xbox|epic games|bowling|\bgolf\b|\bski\b|\bzoo\b|aquarium|escape|billetterie|festival|arcade|guzzo|la ronde|centre bell|bell centre|centre videotron/, 'Entertainment'],
    [/\b(?:atm|abm|gab)\b|guichet|withdrawal|retrait/, 'Cash'],
    [/\bfees?\b|\bfrais\b|interest|interets/, 'Fees']
  ];

  /* ------------------------------------------------------------------ text helpers */

  function clean(s) {
    return String(s == null ? '' : s).replace(/[\u200b-\u200d\ufeff]/g, '').replace(/\s+/g, ' ').trim();
  }

  // Lower-case and strip accents: "Débité à Montréal" -> "debite a montreal".
  function fold(s) {
    return String(s == null ? '' : s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function round2(n) { return Math.round(n * 100) / 100; }

  function normCurrency(c) {
    var s = clean(c).toUpperCase();
    return /^[A-Z]{3}$/.test(s) ? s : '';
  }

  var DOLLAR_CURRENCIES = { USD: 1, CAD: 1, AUD: 1, NZD: 1, BSD: 1, MXN: 1, HKD: 1, SGD: 1 };

  // Map a currency marker to an ISO code. A bare "$" means the default currency when that
  // is a dollar currency, otherwise USD.
  function currencyOf(sym, def) {
    var s = String(sym || '').toUpperCase().replace(/\s+/g, '');
    var bare = DOLLAR_CURRENCIES[def] ? def : 'USD';
    if (!s || s === '$' || s === 'DOLLAR' || s === 'DOLLARS') return bare;
    if (/^(CA\$|C\$|CAD\$?|\$CA|\$CAN|\$CAD)$/.test(s)) return 'CAD';
    if (/^(US\$|U\.S\.\$|USD\$?|\$US|\$USD)$/.test(s)) return 'USD';
    if (/^(AU\$|A\$|AUD|\$AU)$/.test(s)) return 'AUD';
    if (/^(NZ\$|NZD|\$NZ)$/.test(s)) return 'NZD';
    if (/^(BS\$|B\$|BSD|BD\$|\$BS)$/.test(s)) return 'BSD';
    if (/^(MX\$|MXN)$/.test(s)) return 'MXN';
    if (/^(HK\$|HKD)$/.test(s)) return 'HKD';
    if (/^(S\$|SGD)$/.test(s)) return 'SGD';
    if (s === '€' || s === 'EUR' || s === 'EURO' || s === 'EUROS') return 'EUR';
    if (s === '£' || s === 'GBP') return 'GBP';
    if (s === '¥' || s === 'JPY') return 'JPY';
    if (s === '₹' || s === 'INR') return 'INR';
    if (s === 'CHF') return 'CHF';
    return bare;
  }

  // "1,234.56" "1 234,56" "1.234,56" "45,5" -> number. A separator followed by exactly
  // three digits at the end is a thousands separator ("1,234" = 1234).
  function toNumber(s) {
    s = String(s).replace(/\s/g, ' ').trim();
    var m = /^(.*?)[.,](\d{1,2})$/.exec(s);
    var intPart = m ? m[1] : s;
    var dec = m ? m[2] : '';
    var digits = intPart.replace(/\D/g, '');
    if (!digits && !dec) return NaN;
    return parseFloat((digits || '0') + (dec ? '.' + dec : ''));
  }

  /* ------------------------------------------------------------------ amounts */

  var NUM = '(?:\\d{1,3}(?:[,. ]\\d{3})+|\\d+)(?:[.,]\\d{1,2})?(?!\\d)';
  // "$45.20" "CA$ 12" "USD 45" "€4.50" "B$45" ...
  var PRE_RE = new RegExp('(?<![A-Za-z])(CA\\$|C\\$|CAD ?\\$?|US\\$|U\\.S\\.\\$|USD ?\\$?|AU\\$|A\\$|AUD|NZ\\$|NZD|BS\\$|B\\$|BSD|BD\\$|MX\\$|MXN|HK\\$|HKD|S\\$|SGD|EUR|€|GBP|£|CHF|JPY|¥|INR|₹|\\$) ?([-−]?) ?(' + NUM + ')', 'g');
  // "54,21 $" "45,00 $ CA" "12.50 USD" "4,50 €" "4,50 euros" ...
  var POST_RE = new RegExp('(?<![A-Za-z0-9.,])(' + NUM + ') ?(\\$ ?(?:CA|CAN|CAD|US|USD|AU|NZ|BS)\\b|\\$|€|£|¥|₹|(?:CAD|USD|EUR|GBP|BSD|CHF|AUD|NZD|MXN|JPY|INR|SGD|HKD)\\b|euros?\\b|dollars?\\b)', 'gi');
  // Last resort when no currency marker is present: "Amount: 45.20".
  var BARE_RE = /\b(?:amount|montant|total|purchase|achat|transaction|paid|pay[ée]|debit|d[ée]bit)\s*(?:of|de|:|=)?\s*([-−]?\d{1,3}(?:[,. ]\d{3})*[.,]\d{2})(?!\d)/gi;

  function signBefore(text, idx) {
    var c = text.charAt(idx - 1);
    if (c === ' ') c = text.charAt(idx - 2);
    return c === '-' || c === '−' ? '-' : c === '+' ? '+' : '';
  }

  function findAmounts(text, def) {
    var out = [];
    var m;
    PRE_RE.lastIndex = 0;
    while ((m = PRE_RE.exec(text))) {
      out.push({
        index: m.index, end: m.index + m[0].length, value: toNumber(m[3]),
        currency: currencyOf(m[1], def), explicit: m[1] !== '$', decimals: /[.,]\d{1,2}$/.test(m[3]),
        sign: m[2] ? '-' : signBefore(text, m.index), form: 'pre'
      });
    }
    POST_RE.lastIndex = 0;
    while ((m = POST_RE.exec(text))) {
      var sym = m[2];
      out.push({
        index: m.index, end: m.index + m[0].length, value: toNumber(m[1]),
        currency: currencyOf(sym, def), explicit: sym !== '$' && !/^dollars?$/i.test(sym), decimals: /[.,]\d{1,2}$/.test(m[1]),
        sign: signBefore(text, m.index), form: 'post'
      });
    }
    out.sort(function (a, b) { return a.index - b.index; });
    // "$45.00 USD" is matched by both forms; keep the better reading of each overlap.
    var kept = [];
    out.forEach(function (c) {
      if (!(c.value > 0)) return;
      var prev = kept[kept.length - 1];
      if (prev && c.index < prev.end) {
        var better = c.decimals !== prev.decimals ? c.decimals : c.explicit !== prev.explicit ? c.explicit : prev.form === 'post' && c.form === 'pre';
        if (better) kept[kept.length - 1] = c;
        return;
      }
      kept.push(c);
    });
    if (!kept.length) {
      BARE_RE.lastIndex = 0;
      while ((m = BARE_RE.exec(text))) {
        var v = toNumber(m[1].replace(/^[-−]/, ''));
        if (v > 0) kept.push({ index: m.index + m[0].length - m[1].length, end: m.index + m[0].length, value: v, currency: def, explicit: false, decimals: true, sign: /^[-−]/.test(m[1]) ? '-' : '', form: 'bare' });
      }
    }
    // A short notification with exactly one decimal number and no currency marker ("Cafe Olimpico 7.50"):
    // kept, in the default currency, but with low confidence so it lands in review.
    if (!kept.length && text.length <= 80 && !/\b(code|codes|otp|pin|version|verification)\b/i.test(text)) {
      var only = text.match(/(?<![\d.,])\d{1,3}(?:[ ,]\d{3})*[.,]\d{2}(?!\d)(?!\s?%)/g);
      if (only && only.length === 1) {
        var at = text.indexOf(only[0]);
        kept.push({ index: at, end: at + only[0].length, value: toNumber(only[0]), currency: def, explicit: false, decimals: true, sign: signBefore(text, at), form: 'bare' });
      }
    }
    return kept;
  }

  // Context right before / after an amount that says it is not a spend (matched on folded text).
  var NEG_BEFORE = /\b(balance|available|avail|limit|remaining|owing|outstanding|minimum|statement|due|earn(?:ed)?|rewards?|points?|cash ?back|bonus|win|below|under|above|exceed\w*|reached|less than|more than|threshold|solde|disponible|plafond|limite|restant|reste|releve|echeance|gagne\w*|recompense\w*|remise|inferieur\w*|superieur\w*|depasse\w*|atteint|moins de|plus de|seuil)\b\W*(?:\w+\W+){0,2}$/;
  var UPDATE_RE = /\b(updated to|passee? a|adjusted to|ajuste a|mis a jour a)\b/;
  var NEG_AFTER = /^\W{0,3}(?:is |est )?(?:due|left|remaining|available|disponible|restant|of credit|de credit|credit limit|limit|cash ?back|points|in rewards|en recompenses|rewards?)\b/;
  var POS_BEFORE = /\b(purchase\w*|spent|spend\w*|charge[ds]?|transaction|payment|paid|debit\w*|withdrawal|withdrew|authori[sz]\w*|approved|amount|refund\w*|credit(?:ed)?|deposit\w*|transfer\w*|sent|received|achat|depense\w*|paiement|paye\w*|retrait|montant|autoris\w*|approuv\w*|rembours\w*|depot|virement|envoy\w*|recu|used for)\b\W*(?:\w+\W+){0,3}$/;
  var WEAK_BEFORE = /\b(of|de|for|pour|du)\W*$/;

  function lastSentenceBreak(s) {
    var re = /[.!?|](?=\s|$)/g;
    var m;
    var idx = -1;
    while ((m = re.exec(s))) idx = m.index;
    return idx;
  }

  function pickAmount(text, def) {
    var cands = findAmounts(text, def);
    if (!cands.length) return null;
    var best = null;
    cands.forEach(function (c, i) {
      var before = text.slice(Math.max(0, c.index - 48), c.index);
      before = before.slice(lastSentenceBreak(before) + 1);
      var b = fold(before);
      var a = fold(text.slice(c.end, c.end + 28));
      var score = (i === 0 ? 0.5 : 0) + (c.explicit ? 0.25 : 0);
      c.pos = POS_BEFORE.test(b);
      if (c.pos) score += 3; else if (WEAK_BEFORE.test(b)) score += 1;
      if (NEG_BEFORE.test(b) || NEG_AFTER.test(a)) score -= 6;
      c.score = score;
      if (!best || score > best.score) best = c;
    });
    // "The pending transaction of $45.00 ... was updated to $52.00": the last amount is the real one.
    if (best && UPDATE_RE.test(fold(text))) {
      cands.forEach(function (c) { if (c.score > -1 && c.index > best.index) best = c; });
    }
    // Foreign purchase with the conversion in the text ("49.99 USD ($67.89 CAD)", "€45.00 (CAD 66.20)"):
    // keep the amount in the default currency so it counts in the totals, and remember the original.
    if (best && best.currency !== def && best.explicit) {
      var alt = null;
      cands.forEach(function (c) {
        if (c !== best && c.currency === def && c.explicit && c.score > -1 && Math.abs(c.index - best.index) < 45 && (!alt || c.score > alt.score)) alt = c;
      });
      if (alt) {
        alt.original = { amount: round2(best.value), currency: best.currency };
        alt.pos = alt.pos || best.pos;
        best = alt;
      }
    }
    return best;
  }

  /* ------------------------------------------------------------------ classification */

  var DECLINED_RE = /\b(declined|denied|refused|rejected|unsuccessful|not approved|could not be (?:processed|approved|completed)|was blocked|we blocked|blocked a|refusee?s?|declinee?s?|rejetee?s?|non autorisee?s?|n'a pas ete (?:autorisee?|approuvee?|acceptee?))\b/;
  var UPCOMING_RE = /\b(upcoming|scheduled|will be (?:charged|debited|withdrawn|processed|paid|renewed)|renews? (?:on|soon|tomorrow)|is due|due (?:on|soon|tomorrow|today|in)|reminder|rappel|a venir|sera (?:preleve|debite|paye|renouvele)e?|prevue?s?|echeance|has requested|requested .{0,20} from you|request for|money request|vous a demande|demande de (?:paiement|virement|fonds)|demande d.argent)\b/;
  var STATEMENT_RE = /\b(statement (?:is )?(?:ready|available)|new statement|statement balance|minimum payment|payment due|due date|releve (?:est )?disponible|nouveau releve|paiement minimum|date d'echeance|solde du releve)\b/;
  var PROMO_RE = /\b(offer|offre|promo\w*|limited time|ends soon|sign up|refer|parrain\w*|chance to win|win|gagne[rz]|concours|exclusive|exclusi\w*|unlock|save up to|economisez|bonus|boost|deal|special)\b/;
  var STRONG_TX_RE = /\b(purchase (?:of|at|approved|made|for)|was made|were made|was charged|been charged|charged (?:to|on|at)|was approved|was authori[sz]ed|was used|you made|you spent|you paid|you(?:'ve| have) (?:paid|spent)|paid|spent|transaction (?:of|at|with|for)|withdrawal of|achat (?:de|chez|par|effectue)|paiement (?:de|chez|par)|effectue\w*|debite\w*|transaction de|retrait de|refund of|rembours\w*|deposit of|depot de|large purchase|charge of|depense de)\b/;
  var TRANSFER_RE = /\b(received your payment|thank you for your payment|thanks for your payment|autopay|e-?transfer|virement|wire transfer|transfer\w* (?:to|from|of|between)|transfert\w*|contribution (?:of|de)|cotisation|tfsa|rrsp|fhsa|resp|celi|reer|celiapp|recurring investment|\bplacement\b|order to (?:buy|sell)|ordre (?:d.achat|de vente)|shares?|actions? de|etf|fnb|you bought|vous avez achete \d|zelle|venmo|merci (?:pour|de) votre paiement|vous avez (?:envoye|recu)|you (?:sent|received)|sent you)\b|\b(?:payment|paiement)\b(?:[^.!?]|\.(?=\d)){0,40}\b(?:to your (?:credit card|card|account)|(?:sur|a) votre (?:carte|compte))|\b(?:payment|paiement)\b(?:[^.!?]|\.(?=\d)){0,40}\b(?:received|posted|applied|credited|recu|credite|applique)\b|\b(?:received|recu)\b(?:[^.!?]|\.(?=\d)){0,20}\b(?:payment|paiement)\b/;
  var INCOME_RE = /\b(direct deposit|deposit(?:ed)? (?:of|to|into)|a deposit|payroll|salary|paycheque|paycheck|depot (?:direct|de)|salaire|paie|interest (?:earned|paid|payment|credited)|interets? (?:gagnes?|verses?|credites?|payes?)|(?:was|were|been|ete|ont ete|a ete) depos\w*|deposited (?:in|into|to)|deposes? (?:dans|sur)|remuneration)\b/;
  var CASH_RE = /\b(atm|abm|gab|dab|guichet|cash withdrawal|cash advance|avance de fonds|retrait (?:d.especes|comptant|au guichet|a un gab)|withdrawal at an? (?:atm|abm))\b/;
  // A hold, a pre-authorization or an amount update: kept, but for review.
  var HOLD_RE = /\b(pre-?authori[sz]ation|preautorisation|temporary hold|hold of|retenue temporaire|was updated to|est passee? a|adjusted to|ajuste a|mis a jour a)\b/;
  var PREAUTH_RE = /\b(pre-?authori[sz]ed (?:debit|withdrawal|payment)|preautorise\w*|prelevement)\b/;
  var FEE_RE = /\b(?:(?:annual|monthly|service|overdraft|late|foreign transaction|account|maintenance|nsf) fee (?:of|charged|has|was)|fee of|frais (?:de|mensuels|annuels|bancaires)|interest charge|interets? (?:de|factur\w*))/;

  function detectType(f) {
    if (/\b(refund\w*|rembours\w*|reversal|reversed|returned|annulation|merchant credit)\b/.test(f)) return 'refund';
    if (TRANSFER_RE.test(f)) return 'transfer';
    if (INCOME_RE.test(f)) return 'income';
    if (/\b(has been credited|credited to|(?<!card )credit of|credite\w*|(?<!carte de )credit de)\b/.test(f)) return 'refund';
    if (CASH_RE.test(f) && !PREAUTH_RE.test(f)) return 'cash';
    if (FEE_RE.test(f)) return 'fee';
    return 'purchase';
  }

  /* ------------------------------------------------------------------ merchant */

  var CUES = [
    { re: /\b(?:merchant|marchand|commer[çc]ant|payee|b[ée]n[ée]ficiaire|description|where)\s*[:\-–]\s*/gi, w: 3 },
    { re: /\bchez\s+/gi, w: 3 },
    { re: /\baupr[eè]s de\s+/gi, w: 3 },
    { re: /\b(?:at|@)\s+(?!\d{1,2}[:h.]\d{2}|\d{1,2}\s?(?:am|pm)\b)/gi, w: 2 },
    { re: /\bwith\s+(?!(?:your|a|an|the|card|apple|google|samsung|my|this)\b)/gi, w: 1 },
    { re: /\bto\s+(?!(?:your|you|the|my|account|card|be|a|an)\b)/gi, w: 1 },
    { re: /\bfrom\s+(?!(?:your|you|the|my|account|card)\b)/gi, w: 1 },
    { re: /\bde la part de\s+/gi, w: 3 },
    // "de MARCHAND" only when a name follows (capitalised, not an amount or an article)
    { re: /\bde\s+(?=(?!\d|votre|vos|la |le |les |l['’]|facture|conversion|frais|compte|carte|credit|crédit|paiement|transaction|virement|dépôt|depot)[A-Z0-9][^\s]*)/g, w: 0.8 },
    { re: /(?:^|\s)à\s+(?!(?:\d|votre|vos|la|le|les|l['’]|un|une|partir|compter|payer|venir)\b)/gi, w: 0.5 }
  ];

  var STOP_RE = new RegExp([
    '\\s+(?:on|using|with|was|were|has|have|had|is|are|for|via|through|at|from)\\s',
    '\\s+(?:le|la)\\s+\\d',
    '\\s+(?:avec|sur|par|au moyen|effectu\\S*|cr[ée]dit[ée]e?s?|d[ée]bit[ée]e?s?|port[ée]e?s?|envoy[ée]e?s?|re[çc]ue?s?|trait[ée]e?s?|en date|ce jour|aujourd\\S*|hier|pour un montant|d.un montant|depuis|dans|vers|de la part)(?=\\s|$)',
    '\\s+(?:a|ont|est|sont|sera|seront)\\s+(?:[ée]t[ée]|pass[ée]e?s?|termin[ée]e?s?|arriv[ée]e?s?|effectu|port[ée]|d[ée]bit|cr[ée]dit|envoy|re[çc]u|trait)',
    '\\s+(?:à|a)\\s+\\d',
    '\\s+\\d{1,2}\\s?h\\s?\\d{2}\\b',
    '\\s+\\d{4}-\\d{2}-\\d{2}',
    '\\s+(?:ending|ends|se terminant|terminant|finissant|card|carte|account|compte|approved|authori[sz]ed|declined|pending|totaling|totalling|today|yesterday)(?=\\s|$)',
    '\\s*[,;!|•·()\\[\\]{}"“”«»\\n]',
    '\\s+[-–—]\\s',
    '\\.(?:\\s|$)',
    '\\s+\\d{1,2}[:h]\\d{2}',
    '\\s+\\d{1,2}[/.-]\\d{1,2}(?!\\d)',
    '\\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\.?\\s+\\d',
    '\\s+\\d{1,2}\\s+(?:janv|f[ée]vr|mars|avr|mai|juin|juil|ao[uû]t|sept|oct|nov|d[ée]c)',
    '\\s*[-−+]?(?:[A-Z]{1,3})?[$€£¥₹]\\s?\\d',
    '\\s+[-−+]?\\d+(?:[.,]\\d{3})*[.,]\\d{2}(?!\\d)',
    '\\s+(?:CAD|USD|EUR|GBP|BSD)\\b'
  ].join('|'), 'i');

  var GENERIC_MERCHANT = /^(?:your|you|votre|vos|card|carte|account|compte|transaction|purchase|achat|payment|paiement|a|an|the|un|une|my|mon|ma|it|this|an (?:atm|abm)|un (?:gab|guichet))$/;
  var GENERIC_WORDS = /\b(alert|alerte|notification|transaction|purchase|achat|payment|paiement|debit|credit|card|carte|account|compte|security|securite|new|nouveau|nouvelle|activity|activite|spent|depense|approved|approuve|update|reminder|rappel|message|info|pending|posted|authori[sz]\w*|notice|avis|en attente|express transit)\b/;
  var TAIL_JUNK = /^\d+\s?%|cash ?back|remise|\bpoints?\b|en attente|pending/i;
  // Words that mean the text next to an amount is a sentence, not a merchant name.
  var TX_WORDS = /\b(purchase\w*|paid|pay\w*|spent|spend\w*|charge\w*|transaction\w*|achat\w*|paiement\w*|paye\w*|depense\w*|debit\w*|credit\w*|deposit\w*|depot\w*|refund\w*|rembours\w*|withdraw\w*|retrait\w*|transfer\w*|virement\w*|received|sent|recu|envoye|you|your|vous|votre|was|has|made|alert\w*|amount|montant|total)\b/;
  var FUNC_START = /^(at|on|in|was|were|has|have|had|is|are|been|with|to|from|for|of|via|using|de|du|des|chez|a|au|aux|sur|avec|par|pour|le|la|les|et|and|or|your|you|votre|vos|approved|authori[sz]ed|pending|declined|est|sont|ont|ete)\b/;
  var TRAILING_PREP = /\b(of|de|du|for|pour|at|a|to|from|chez|sur)$/;
  var BANK_WORDS = /\b(rbc|royal bank|td|scotia\w*|bmo|cibc|desjardins|banque|bank|national bank|bnc|tangerine|simplii|wealthsimple|koho|chase|wells fargo|citi\w*|capital one|amex|american express|discover|usaa|revolut|n26|wise|monzo|boursorama|bnp|societe generale|credit agricole|lcl|caisse|lydia|paypal|apple cash|wallet|firstcaribbean|card services|visa|mastercard)\b/;

  function tidyMerchant(m) {
    m = clean(m).replace(/^[\s:–—-]+/, '').replace(/[\s.,:;!?–—-]+$/, '');
    if (m.length > 48) m = m.slice(0, 48).replace(/\s+\S*$/, '');
    if (!/[A-Za-zÀ-ÿ]/.test(m)) return '';
    if (GENERIC_MERCHANT.test(fold(m))) return '';
    return m;
  }

  function hasAmount(s) {
    return findAmounts(s, 'USD').some(function (c) { return c.form !== 'bare'; });
  }

  // "$45.00 SHELL", "STARBUCKS $5.75", "Pending: $3.25 – DUNKIN #3345 – Visa ••8812"
  function adjacentMerchant(parts, amt, app) {
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      if (!part) continue;
      var hit = findAmounts(part, 'USD').filter(function (c) { return c.value === amt.value && (c.form !== 'bare' || amt.form === 'bare'); })[0];
      if (!hit) continue;
      // Separators such as "·" and "|" are kept so STOP_RE stops on them.
      var after = part.slice(hit.end).replace(/^[\s–—\-:]+/, '');
      var stop = after.search(STOP_RE);
      var a = tidyMerchant(stop >= 0 ? after.slice(0, stop) : after);
      var fa = fold(a);
      var afterOk = a && a.length <= 40 && !FUNC_START.test(fa) && !TX_WORDS.test(fa) && !GENERIC_WORDS.test(fa) && !BANK_WORDS.test(fa) && !TAIL_JUNK.test(a);
      var before = part.slice(0, hit.index).replace(/[-−+]$/, '');
      var b = tidyMerchant(before);
      var fb = fold(b);
      var beforeOk = b && b.length <= 40 && !/\d{3,}/.test(b) && !TX_WORDS.test(fb) && !TRAILING_PREP.test(fb) && !GENERIC_WORDS.test(fb) &&
        !BANK_WORDS.test(fb) && fb !== fold(app);
      // A short text without a currency marker ("Cafe Olimpico 7.50") names the merchant before the amount.
      if (amt.form === 'bare') { if (beforeOk) return b; if (afterOk) return a; }
      else { if (afterOk) return a; if (beforeOk) return b; }
    }
    return '';
  }

  function usableName(c, app) {
    if (!c || c.length > 40 || hasAmount(c)) return '';
    var f = fold(c);
    if (GENERIC_WORDS.test(f) || BANK_WORDS.test(f) || (app && f === fold(app))) return '';
    return tidyMerchant(c);
  }

  function findMerchant(title, subtitle, body, app, amt, walletLike) {
    var parts = [body, subtitle, title];
    var best = { merchant: '', weight: 0 };
    // Wallet layout (title = card, subtitle = merchant, body = amount): the subtitle is the merchant.
    if (walletLike) {
      var sub = usableName(subtitle, app);
      if (sub) best = { merchant: sub, weight: 2 };
    }
    parts.forEach(function (part) {
      if (!part) return;
      CUES.forEach(function (cue) {
        if (cue.w <= best.weight) return;
        cue.re.lastIndex = 0;
        var m;
        while ((m = cue.re.exec(part))) {
          var rest = part.slice(m.index + m[0].length);
          var stop = rest.search(STOP_RE);
          var name = tidyMerchant(stop >= 0 ? rest.slice(0, stop) : rest);
          if (name && cue.w > best.weight) { best = { merchant: name, weight: cue.w }; break; }
        }
      });
    });
    if (best.merchant) return best;

    var adj = adjacentMerchant([body, subtitle, title], amt, app);
    if (adj) return { merchant: adj, weight: 0.3 };

    // "NETFLIX: $16.99 charged to your card"
    var pre = /^([^:\n]{2,40}):\s/.exec(body || '');
    if (pre) {
      var p = tidyMerchant(pre[1]);
      var fp = fold(p);
      if (p && !GENERIC_WORDS.test(fp) && !TX_WORDS.test(fp) && !BANK_WORDS.test(fp) && fp !== fold(app)) return { merchant: p, weight: 0.4 };
    }

    // Apps that put the merchant in the title or subtitle (Wallet: title = card, subtitle = merchant).
    var cands = [subtitle, title];
    for (var i = 0; i < cands.length; i++) {
      var name = usableName(cands[i], app);
      if (name) return { merchant: name, weight: 0.3 };
    }
    return best;
  }

  /* ------------------------------------------------------------------ card */

  var CARD_DIGITS_RE = /(?:ending(?:\s+(?:in|with))?|ends?\s+(?:in|with)|(?:se\s+)?terminant\s+par|finissant\s+par|last\s+(?:4|four)(?:\s+digits)?(?:\s+of)?|(?:card|carte)\s+(?:no\.?|number|num[ée]ro|#)?|x{2,}|\*+|•+|·{2,}|\.{2,}|…)\s*[:#]?\s*(\d{4,5})(?!\d)/i;
  var BRAND_RE = /\b(visa|master\s?card|amex|american express|discover|interac|apple card|apple cash|debit card|carte de d[ée]bit|credit card|carte de cr[ée]dit)\b/i;
  var BRAND_LABEL = { visa: 'Visa', mastercard: 'Mastercard', 'master card': 'Mastercard', amex: 'Amex', 'american express': 'Amex', discover: 'Discover', interac: 'Interac', 'apple card': 'Apple Card', 'apple cash': 'Apple Cash', 'debit card': 'Debit', 'carte de debit': 'Debit', 'credit card': 'Credit', 'carte de credit': 'Credit' };

  function findCard(text, title, app, walletLike) {
    var d = CARD_DIGITS_RE.exec(text);
    var b = BRAND_RE.exec(text);
    var brand = b ? BRAND_LABEL[fold(b[1]).replace(/\s+/g, ' ')] || '' : '';
    if (d) return (brand ? brand + ' ' : '') + '••' + d[1];
    if ((walletLike || /wallet|\bcartes?\b/.test(fold(app))) && title && !hasAmount(title)) return tidyMerchant(title) || brand;
    return brand;
  }

  /* ------------------------------------------------------------------ categories */

  function matchRule(foldedMerchant, pattern) {
    var p = clean(pattern);
    if (!p) return false;
    var re = /^\/(.+)\/([a-z]*)$/.exec(p);
    if (re) {
      try { return new RegExp(re[1], re[2].indexOf('i') >= 0 ? re[2] : re[2] + 'i').test(foldedMerchant); } catch (e) { return false; }
    }
    return foldedMerchant.indexOf(fold(p)) >= 0;
  }

  function categorize(merchant, rules, type) {
    if (type === 'cash') return 'Cash';
    if (type === 'fee') return 'Fees';
    if (type === 'income') return 'Income';
    if (type === 'transfer') return 'Transfers';
    var m = fold(merchant);
    if (!m) return 'Other';
    var user = rules || [];
    for (var i = 0; i < user.length; i++) {
      var r = user[i];
      if (r && r.pattern && r.category && matchRule(m, r.pattern)) return clean(r.category);
    }
    for (var j = 0; j < DEFAULT_RULES.length; j++) {
      if (DEFAULT_RULES[j][0].test(m)) return DEFAULT_RULES[j][1];
    }
    return 'Other';
  }

  /* ------------------------------------------------------------------ source helpers */

  // Wallet layout: title = card, subtitle = merchant, body = just the amount.
  function isWalletLayout(title, subtitle, body, def) {
    title = clean(title); subtitle = clean(subtitle); body = clean(body);
    return !!subtitle && !hasAmount(title) && !hasAmount(subtitle) &&
      /^[+\-−]?\s*[^A-Za-z]*\d/.test(body) && findAmounts(body, def || 'USD').length === 1;
  }

  // Which bank sent a notification, from its text (the iOS trigger does not say which app it came from).
  function inferBank(fields) {
    fields = fields || {};
    var all = fold([fields.app, fields.title, fields.subtitle, fields.body, fields.from].join(' '));
    // The Wallet app ("Cartes" on a French iPhone) is its own channel, whatever card it shows.
    if (/\b(wallet|cartes?)\b/.test(fold(fields.app)) || isWalletLayout(fields.title, fields.subtitle, fields.body)) return 'cartes';
    if (/scotia|infoalert/.test(all)) return 'scotia';
    if (/capital ?one/.test(all)) return 'capitalone';
    if (/wealthsimple/.test(all)) return 'wealthsimple';
    if (/desjardins/.test(all)) return 'desjardins';
    if (/\b(rbc|royal bank|banque royale)\b/.test(all)) return 'rbc';
    if (/\btd\b/.test(all)) return 'td';
    if (/\bbmo\b/.test(all)) return 'bmo';
    if (/\bcibc\b/.test(all)) return 'cibc';
    if (/tangerine/.test(all)) return 'tangerine';
    return '';
  }

  // The Shortcut was built with the words typed in instead of the variables ("Titre", "corps"...).
  var PLACEHOLDER_RE = /^(?:titre|title|sous-?titre|subtitle|corps|body|message|texte|text|contenu|content|notification|entree du raccourci|shortcut input|input|valeur|value)$/;
  function isPlaceholder(fields) {
    fields = fields || {};
    var vals = [fields.title, fields.subtitle, fields.body].map(function (v) { return fold(clean(v)); }).filter(String);
    return vals.length > 0 && vals.some(function (v) { return PLACEHOLDER_RE.test(v); });
  }

  /* ------------------------------------------------------------------ public API */

  function ignore(reason, def) {
    return { kind: 'ignore', reason: reason, type: '', amount: 0, currency: def, merchant: '', card: '', category: '', confidence: 0, status: '' };
  }

  /**
   * parse({title, subtitle, body, app}, {defaultCurrency, rules}) or parse("raw text", opts)
   * -> {kind: 'transaction'|'ignore', reason, type, amount (always positive), currency,
   *     merchant, card, category, confidence (0-1), status: 'ok'|'review'}
   */
  function parse(input, opts) {
    opts = opts || {};
    var def = normCurrency(opts.defaultCurrency) || 'USD';
    if (typeof input === 'string') input = { body: input };
    input = input || {};
    var title = clean(input.title);
    var subtitle = clean(input.subtitle);
    var body = clean(input.body != null ? input.body : input.text != null ? input.text : input.message);
    var app = clean(input.app);
    var parts = [];
    [title, subtitle, body].forEach(function (p) { if (p && parts.indexOf(p) < 0) parts.push(p); });
    var text = parts.join('\n');
    if (!text) return ignore('empty', def);

    var f = fold(text);
    // Wallet layout: title = card, subtitle = merchant, body = just the amount. Such a notification
    // is a transaction whatever words the merchant name contains ("Boost Juice", "Dollar Deal").
    var walletLike = isWalletLayout(title, subtitle, body, def);
    var strong = STRONG_TX_RE.test(f) || walletLike;
    var promoText = fold([title, body].join('\n'));
    if (DECLINED_RE.test(f)) return ignore('declined', def);
    if (!strong && UPCOMING_RE.test(f)) return ignore('upcoming', def);
    if (!strong && STATEMENT_RE.test(f)) return ignore('statement', def);
    if (!strong && PROMO_RE.test(promoText)) return ignore('promo', def);

    var amt = pickAmount(text, def);
    if (!amt) return ignore('no-amount', def);
    if (amt.score < 0) return ignore('not-a-spend', def);
    // "Le solde de votre compte ... est inférieur à 100,00 $": a balance notice, not a spend.
    if (!strong && !amt.pos && /\b(solde|balance)\b/.test(f)) return ignore('not-a-spend', def);

    var type = detectType(f);
    if (type === 'purchase' && amt.sign === '+') type = 'refund';
    var m = findMerchant(title, subtitle, body, app, amt, walletLike);
    var card = findCard(text, title, app, walletLike);
    var needsMerchant = type === 'purchase' || type === 'refund';
    var mTerm = m.weight >= 2 ? 0.2 : m.weight >= 1 ? 0.1 : m.weight > 0 ? 0.05 : needsMerchant ? -0.2 : 0;
    var conf = 0.4 + (amt.form !== 'bare' ? 0.2 : 0) + (amt.pos ? 0.2 : 0) + (strong ? 0.1 : 0) + mTerm;
    var reason = '';
    if (HOLD_RE.test(f)) { conf = Math.min(conf, 0.5); reason = 'hold'; }
    conf = round2(Math.max(0, Math.min(1, conf)));
    var out = {
      kind: 'transaction', reason: reason, type: type, amount: round2(amt.value), currency: amt.currency,
      merchant: m.merchant, card: card, category: categorize(m.merchant, opts.rules, type),
      confidence: conf, status: conf < 0.6 || (needsMerchant && !m.merchant) ? 'review' : 'ok'
    };
    if (amt.original) out.original = amt.original;
    if (walletLike) out.layout = 'wallet';
    return out;
  }

  /**
   * Build a transaction from fields that are already split out (Apple Pay automation,
   * manual entry): {amount: "$12.50" | 12.5, merchant, card, currency, type, category}.
   */
  function fromFields(fields, opts) {
    opts = opts || {};
    fields = fields || {};
    var def = normCurrency(opts.defaultCurrency) || 'USD';
    var cur = normCurrency(fields.currency);
    var value = NaN;
    var currency = cur || def;
    if (typeof fields.amount === 'number') {
      value = Math.abs(fields.amount);
    } else if (fields.amount != null && clean(fields.amount)) {
      var s = clean(fields.amount);
      var found = findAmounts(s, def);
      if (found.length && found[0].form !== 'bare') { value = found[0].value; currency = cur || found[0].currency; }
      else value = toNumber(s.replace(/[^\d.,\s]/g, ''));
    }
    var type = TYPES.indexOf(fields.type) >= 0 ? fields.type : 'purchase';
    var merchant = tidyMerchant(fields.merchant);
    var ok = value > 0;
    return {
      kind: 'transaction', reason: '', type: type, amount: ok ? round2(value) : 0, currency: currency,
      merchant: merchant, card: clean(fields.card).slice(0, 40),
      category: clean(fields.category) || categorize(merchant, opts.rules, type),
      confidence: ok ? 0.9 : 0.3, status: ok && (merchant || !(type === 'purchase' || type === 'refund')) ? 'ok' : 'review'
    };
  }

  // Money in (refund, income) is stored negative so a refund reduces spending.
  function signedAmount(amount, type) {
    var a = Math.abs(Number(amount) || 0);
    return type === 'refund' || type === 'income' ? -a : a;
  }

  // Never keep one-time codes: "Your verification code is 482913" becomes "… is ••••••".
  function redactCodes(s) {
    var t = String(s == null ? '' : s);
    if (!/\b(code|codes|otp|passcode|password|pin|verification|verify|one[- ]time|2fa|mot de passe|v[ée]rification|s[ée]curit[ée]|security)\b/i.test(t)) return t;
    return t.replace(/\b\d{4,10}\b/g, '••••••');
  }

  function countsAsSpending(tx) {
    return !!tx && SPENDING_TYPES[tx.type] === true && tx.status !== 'duplicate' && tx.status !== 'excluded';
  }

  return {
    VERSION: VERSION,
    CATEGORIES: CATEGORIES,
    TYPES: TYPES,
    DEFAULT_RULES: DEFAULT_RULES,
    parse: parse,
    fromFields: fromFields,
    categorize: categorize,
    matchRule: matchRule,
    findAmounts: findAmounts,
    toNumber: toNumber,
    signedAmount: signedAmount,
    countsAsSpending: countsAsSpending,
    redactCodes: redactCodes,
    isWalletLayout: isWalletLayout,
    inferBank: inferBank,
    isPlaceholder: isPlaceholder,
    fold: fold,
    clean: clean
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SpendParser;
