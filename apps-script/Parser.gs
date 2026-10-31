// Generated from src/parser.js by tools/build.mjs. Edit that file, not this one.
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

  var VERSION = '0.1.0';

  /* ------------------------------------------------------------------ categories */

  var CATEGORIES = [
    { name: 'Groceries', icon: '🛒' },
    { name: 'Dining', icon: '🍽️' },
    { name: 'Transport', icon: '🚗' },
    { name: 'Travel', icon: '✈️' },
    { name: 'Shopping', icon: '🛍️' },
    { name: 'Subscriptions', icon: '🔁' },
    { name: 'Bills', icon: '🧾' },
    { name: 'Health', icon: '💊' },
    { name: 'Entertainment', icon: '🎟️' },
    { name: 'Cash', icon: '💵' },
    { name: 'Fees', icon: '🏦' },
    { name: 'Other', icon: '🏷️' },
    { name: 'Income', icon: '💰' },
    { name: 'Transfers', icon: '🔄' }
  ];

  // purchase / cash / fee are money out; refund is money back on a purchase.
  // income and transfer are recorded but never count as spending.
  var TYPES = ['purchase', 'refund', 'cash', 'fee', 'income', 'transfer'];
  var SPENDING_TYPES = { purchase: true, refund: true, cash: true, fee: true };

  // Matched against the merchant, accents removed and lower-cased. First match wins;
  // user rules (Rules sheet) are checked before these.
  var DEFAULT_RULES = [
    [/uber ?\*? ?eats|ubereats|doordash|skip ?the ?dishes|deliveroo|just ?eat|foodora|grubhub/, 'Dining'],
    [/amazon prime|prime video|amzn digital|kindle|audible|apple\.com|itunes|icloud|netflix|spotify|disney|crave|hbo|paramount|dazn|youtube|google \*|google play|google one|adobe|microsoft|game ?pass|playstation plus|dropbox|openai|chatgpt|anthropic|claude\.ai|patreon|substack|nytimes|duolingo|deezer|tidal|siriusxm/, 'Subscriptions'],
    [/pharma|pharmacy|jean coutu|shoppers drug|uniprix|familiprix|proxim|brunet|\bcvs\b|walgreens|rexall|london drugs|clinic|clinique|dental|dentist|dentaire|medical|medecin|doctor|hospital|hopital|optometr|optique|lunetterie|physio|massotherap|chiro|\bgym\b|fitness|yoga|crossfit|goodlife|econofitness|energie cardio|ymca/, 'Health'],
    [/hydro|electric|electricite|energir|gaz metro|\bbell\b|rogers|videotron|telus|\bfido\b|koodo|virgin plus|freedom mobile|public mobile|chatr|verizon|at&t|t-mobile|comcast|xfinity|\bsfr\b|bouygues|free mobile|insurance|assurance|\bintact\b|belairdirect|\bloyer\b|\brent\b|internet|\bpower\b|utilit|wireless|telecom|phone co\b|mobile phone|\bbpl\b|\bbtc\b|\baliv\b/, 'Bills'],
    [/restaurant|resto\b|cafe|coffee|starbucks|tim hortons|\btims\b|second cup|mcdonald|\bmcdo\b|burger|pizz|sushi|subway|\bkfc\b|a&w|wendy|chipotle|taco|poutine|st-?hubert|boulangerie|bakery|patisserie|bistro|brasserie|grill|\bpub\b|\bbar\b|tavern|pret a manger|\bpret\b|dunkin|five guys|domino|nando|\bthai\b|\bpho\b|ramen|diner|eatery|cantina|creperie|bagel|donut|doughnut|smoothie|gelato|dairy queen|chick-fil-a|panera|popeyes|benny|la belle province|trattoria|taqueria|\bbbq\b|steakhouse|cafeteria/, 'Dining'],
    [/grocer|supermarket|supermarche|epicerie|marche|market|\biga\b|\bmetro\b|\bmaxi\b|provigo|loblaw|sobeys|safeway|super ?c\b|adonis|costco|walmart|wal-mart|whole ?foods|trader joe|kroger|publix|\baldi\b|\blidl\b|carrefour|monoprix|monop\b|franprix|leclerc|auchan|intermarche|super ?u\b|picard|solomon|super ?value|food ?store|no ?frills|freshco|save-on|instacart|fruiterie|boucherie|fromagerie|depanneur|couche-tard|circle k|7-?eleven/, 'Groceries'],
    [/shell|esso|petro|ultramar|chevron|exxon|\bmobil\b|\bbp\b|texaco|sunoco|irving|husky|total ?energies|gas station|\bgas\b|fuel|essence|carburant|uber|lyft|taxi|\bcab\b|\bstm\b|\bopus\b|presto|transit|bixi|communauto|\bratp\b|\bsncf\b|navigo|via rail|amtrak|greyhound|parking|stationnement|impark|indigo park|\btoll\b|peage|407 etr|zipcar|car wash|lave-auto|\bsaaq\b|\bdmv\b/, 'Transport'],
    [/air canada|westjet|porter air|air transat|\bflair\b|delta air|united air|american air|jetblue|southwest|spirit air|air france|\bklm\b|british airways|lufthansa|bahamasair|airline|airways|airbnb|\bvrbo\b|booking\.com|expedia|hotels\.com|hotel|marriott|hilton|hyatt|sheraton|westin|fairmont|holiday inn|best western|resort|motel|auberge|\binn\b|hostel|ferry|ferries|cruise|car rental|hertz|\bavis\b|enterprise rent|budget rent|\bturo\b|duty free|airport|aeroport/, 'Travel'],
    [/amazon|amzn|best ?buy|ikea|winners|marshalls|homesense|tj ?maxx|h&m|\bzara\b|uniqlo|\bgap\b|old navy|simons|la baie|hudson'?s bay|sephora|etsy|ebay|shein|temu|aliexpress|canadian tire|home depot|\brona\b|lowe'?s|dollarama|dollar tree|target|apple store|\bapple\b|chapters|\bmec\b|sport chek|decathlon|\bfnac\b|darty|\bboulanger\b|lululemon|\bnike\b|adidas|john bull|staples|bureau en gros|structube|wayfair/, 'Shopping'],
    [/cinema|cineplex|theatre|theater|ticketmaster|evenko|stubhub|eventbrite|spectacle|concert|museum|musee|steam|playstation|nintendo|xbox|epic games|bowling|\bgolf\b|\bski\b|\bzoo\b|aquarium|escape|billetterie|festival|arcade/, 'Entertainment'],
    [/\batm\b|guichet|withdrawal|retrait/, 'Cash'],
    [/\bfees?\b|\bfrais\b|interest|interets/, 'Fees']
  ];

  /* ------------------------------------------------------------------ text helpers */

  function clean(s) {
    return String(s == null ? '' : s).replace(/[​-‍﻿]/g, '').replace(/\s+/g, ' ').trim();
  }

  // Lower-case and strip accents: "Débité à Montréal" -> "debite a montreal".
  function fold(s) {
    return String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
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
    return kept;
  }

  // Context right before / after an amount that says it is not a spend (matched on folded text).
  var NEG_BEFORE = /\b(balance|available|avail|limit|remaining|owing|outstanding|minimum|statement|due|earn(?:ed)?|rewards?|points?|cash ?back|bonus|win|solde|disponible|plafond|limite|restant|reste|releve|echeance|gagne\w*|recompense\w*|remise)\b\W*(?:\w+\W+){0,2}$/;
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
    return best;
  }

  /* ------------------------------------------------------------------ classification */

  var DECLINED_RE = /\b(declined|denied|refused|rejected|unsuccessful|not approved|could not be (?:processed|approved|completed)|was blocked|we blocked|blocked a|refusee?s?|declinee?s?|rejetee?s?|non autorisee?s?|n'a pas ete (?:autorisee?|approuvee?|acceptee?))\b/;
  var UPCOMING_RE = /\b(upcoming|scheduled|will be (?:charged|debited|withdrawn|processed|paid|renewed)|renews? (?:on|soon|tomorrow)|is due|due (?:on|soon|tomorrow|today|in)|reminder|rappel|a venir|sera (?:preleve|debite|paye|renouvele)e?|prevue?s?|echeance)\b/;
  var STATEMENT_RE = /\b(statement (?:is )?(?:ready|available)|new statement|statement balance|minimum payment|payment due|due date|releve (?:est )?disponible|nouveau releve|paiement minimum|date d'echeance|solde du releve)\b/;
  var PROMO_RE = /\b(offer|offre|promo\w*|limited time|ends soon|sign up|refer|parrain\w*|chance to win|win|gagne[rz]|concours|exclusive|exclusi\w*|unlock|save up to|economisez|bonus|boost|deal|special)\b/;
  var STRONG_TX_RE = /\b(purchase (?:of|at|approved|made|for)|was made|were made|was charged|been charged|charged (?:to|on|at)|was approved|was authori[sz]ed|was used|you made|you spent|you paid|you(?:'ve| have) (?:paid|spent)|paid|spent|transaction (?:of|at|with|for)|withdrawal of|achat (?:de|chez|par|effectue)|paiement (?:de|chez|par)|effectue\w*|debite\w*|transaction de|retrait de|refund of|rembours\w*|deposit of|depot de|large purchase|charge of|depense de)\b/;
  var TRANSFER_RE = /\b(received your payment|thank you for your payment|thanks for your payment|autopay|e-?transfer|virement|wire transfer|transfer(?:red)? (?:to|from)|zelle|venmo|merci (?:pour|de) votre paiement|vous avez (?:envoye|recu)|you (?:sent|received)|sent you)\b|\b(?:payment|paiement)\b(?:[^.!?]|\.(?=\d)){0,40}\b(?:received|posted|applied|credited|recu|credite|applique)\b|\b(?:received|recu)\b(?:[^.!?]|\.(?=\d)){0,20}\b(?:payment|paiement)\b/;
  var INCOME_RE = /\b(direct deposit|deposit(?:ed)? (?:of|to|into)|a deposit|payroll|salary|paycheque|paycheck|depot (?:direct|de)|salaire|paie)\b/;
  var CASH_RE = /\b(atm|cash withdrawal|withdrawal|withdrew|cash advance|retrait|guichet|gab|dab)\b/;
  var PREAUTH_RE = /\b(pre-?authori[sz]ed (?:debit|withdrawal|payment)|preautorise\w*|prelevement)\b/;
  var FEE_RE = /\b(?:(?:annual|monthly|service|overdraft|late|foreign transaction|account|maintenance|nsf) fee (?:of|charged|has|was)|fee of|frais (?:de|mensuels|annuels|bancaires)|interest charge|interets? (?:de|factur\w*))/;

  function detectType(f) {
    if (/\b(refund\w*|rembours\w*|reversal|reversed|returned|annulation|merchant credit)\b/.test(f)) return 'refund';
    if (TRANSFER_RE.test(f)) return 'transfer';
    if (INCOME_RE.test(f)) return 'income';
    if (/\b(has been credited|credited to|credit of|credite\w*|credit de)\b/.test(f)) return 'refund';
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
    { re: /(?:^|\s)à\s+(?!(?:\d|votre|vos|la|le|les|l['’]|un|une|partir|compter|payer|venir)\b)/gi, w: 0.5 }
  ];

  var STOP_RE = new RegExp([
    '\\s+(?:on|using|with|was|were|has|have|had|is|are|for|via|through|at|from)\\s',
    '\\s+(?:le|la)\\s+\\d',
    '\\s+(?:avec|sur|par|au moyen|effectu\\S*|en date|ce jour|aujourd\\S*|hier|pour un montant|d.un montant)(?=\\s|$)',
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

  var GENERIC_MERCHANT = /^(?:your|you|votre|vos|card|carte|account|compte|transaction|purchase|achat|payment|paiement|a|an|the|un|une|my|mon|ma|it|this)$/;
  var GENERIC_WORDS = /\b(alert|alerte|notification|transaction|purchase|achat|payment|paiement|debit|credit|card|carte|account|compte|security|securite|new|nouveau|nouvelle|activity|activite|spent|depense|approved|approuve|update|reminder|rappel|message|info|pending|posted|authori[sz]\w*|notice|avis)\b/;
  // Words that mean the text next to an amount is a sentence, not a merchant name.
  var TX_WORDS = /\b(purchase\w*|paid|pay\w*|spent|spend\w*|charge\w*|transaction\w*|achat\w*|paiement\w*|paye\w*|depense\w*|debit\w*|credit\w*|deposit\w*|depot\w*|refund\w*|rembours\w*|withdraw\w*|retrait\w*|transfer\w*|virement\w*|received|sent|recu|envoye|you|your|vous|votre|was|has|made|alert\w*|amount|montant|total)\b/;
  var FUNC_START = /^(at|on|in|was|were|has|have|had|is|are|been|with|to|from|for|of|via|using|de|du|des|chez|a|au|aux|sur|avec|par|pour|le|la|les|et|and|or|your|you|votre|vos|approved|authori[sz]ed|pending|declined)\b/;
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
  function adjacentMerchant(parts, value, app) {
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      if (!part) continue;
      var hit = findAmounts(part, 'USD').filter(function (c) { return c.value === value && c.form !== 'bare'; })[0];
      if (!hit) continue;
      var after = part.slice(hit.end).replace(/^[\s–—\-:|•·]+/, '');
      var stop = after.search(STOP_RE);
      var a = tidyMerchant(stop >= 0 ? after.slice(0, stop) : after);
      var fa = fold(a);
      if (a && a.length <= 40 && !FUNC_START.test(fa) && !TX_WORDS.test(fa) && !GENERIC_WORDS.test(fa) && !BANK_WORDS.test(fa)) return a;
      var before = part.slice(0, hit.index).replace(/[-−+]$/, '');
      var b = tidyMerchant(before);
      var fb = fold(b);
      if (b && b.length <= 40 && !/\d{3,}/.test(b) && !TX_WORDS.test(fb) && !TRAILING_PREP.test(fb) && !GENERIC_WORDS.test(fb) &&
          !BANK_WORDS.test(fb) && fb !== fold(app)) return b;
    }
    return '';
  }

  function findMerchant(title, subtitle, body, app, value) {
    var parts = [body, subtitle, title];
    var best = { merchant: '', weight: 0 };
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

    var adj = adjacentMerchant([body, subtitle, title], value, app);
    if (adj) return { merchant: adj, weight: 0.3 };

    // "NETFLIX: $16.99 charged to your card"
    var pre = /^([^:\n]{2,40}):\s/.exec(body || '');
    if (pre) {
      var p = tidyMerchant(pre[1]);
      var fp = fold(p);
      if (p && !GENERIC_WORDS.test(fp) && !BANK_WORDS.test(fp) && fp !== fold(app)) return { merchant: p, weight: 0.4 };
    }

    // Apps that put the merchant in the title or subtitle (Wallet: title = card, subtitle = merchant).
    var cands = [subtitle, title];
    for (var i = 0; i < cands.length; i++) {
      var c = cands[i];
      if (!c || c.length > 40 || hasAmount(c)) continue;
      var f = fold(c);
      if (GENERIC_WORDS.test(f) || BANK_WORDS.test(f) || (app && f === fold(app))) continue;
      var name = tidyMerchant(c);
      if (name) return { merchant: name, weight: 0.3 };
    }
    return best;
  }

  /* ------------------------------------------------------------------ card */

  var CARD_DIGITS_RE = /(?:ending(?:\s+(?:in|with))?|ends?\s+(?:in|with)|(?:se\s+)?terminant\s+par|finissant\s+par|last\s+(?:4|four)(?:\s+digits)?(?:\s+of)?|(?:card|carte)\s+(?:no\.?|number|num[ée]ro|#)?|x{2,}|\*+|•+|·{2,}|\.{2,}|…)\s*[:#]?\s*(\d{4,5})(?!\d)/i;
  var BRAND_RE = /\b(visa|master\s?card|amex|american express|discover|interac|apple card|apple cash|debit card|carte de d[ée]bit|credit card|carte de cr[ée]dit)\b/i;
  var BRAND_LABEL = { visa: 'Visa', mastercard: 'Mastercard', 'master card': 'Mastercard', amex: 'Amex', 'american express': 'Amex', discover: 'Discover', interac: 'Interac', 'apple card': 'Apple Card', 'apple cash': 'Apple Cash', 'debit card': 'Debit', 'carte de debit': 'Debit', 'credit card': 'Credit', 'carte de credit': 'Credit' };

  function findCard(text, title, app) {
    var d = CARD_DIGITS_RE.exec(text);
    var b = BRAND_RE.exec(text);
    var brand = b ? BRAND_LABEL[fold(b[1]).replace(/\s+/g, ' ')] || '' : '';
    if (d) return (brand ? brand + ' ' : '') + '••' + d[1];
    if (/wallet/.test(fold(app)) && title && !hasAmount(title)) return tidyMerchant(title) || brand;
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
    var strong = STRONG_TX_RE.test(f);
    if (DECLINED_RE.test(f)) return ignore('declined', def);
    if (!strong && UPCOMING_RE.test(f)) return ignore('upcoming', def);
    if (!strong && STATEMENT_RE.test(f)) return ignore('statement', def);
    if (!strong && PROMO_RE.test(f)) return ignore('promo', def);

    var amt = pickAmount(text, def);
    if (!amt) return ignore('no-amount', def);
    if (amt.score < 0) return ignore('not-a-spend', def);

    var type = detectType(f);
    var m = findMerchant(title, subtitle, body, app, amt.value);
    var card = findCard(text, title, app);
    var conf = 0.4 + (amt.form !== 'bare' ? 0.2 : 0) + (amt.pos ? 0.2 : 0) + (strong ? 0.1 : 0) +
      (m.weight >= 2 ? 0.2 : m.weight >= 1 ? 0.1 : m.weight > 0 ? 0.05 : -0.2);
    conf = round2(Math.max(0, Math.min(1, conf)));
    var needsMerchant = type === 'purchase' || type === 'refund';
    return {
      kind: 'transaction', reason: '', type: type, amount: round2(amt.value), currency: amt.currency,
      merchant: m.merchant, card: card, category: categorize(m.merchant, opts.rules, type),
      confidence: conf, status: conf < 0.6 || (needsMerchant && !m.merchant) ? 'review' : 'ok'
    };
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
    fold: fold,
    clean: clean
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SpendParser;
