// Paste this into Extensions > Apps Script of your private Google Sheet.
// It serves the "add link" page and writes links into the sheet's Queue tab.

const QUEUE = 'Queue';
const FAILED = 'Failed';
const FB_LINK = /^https?:\/\/(?:[\w-]+\.)?(?:facebook\.com|fb\.watch|fb\.com)\/\S+$/i;

function doGet() {
  ensureTabs_();
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Reel Queue')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function ensureTabs_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const headers = {};
  headers[QUEUE] = ['Link', 'Added'];
  headers[FAILED] = ['Link', 'Attempts', 'Last error', 'Last try'];
  Object.keys(headers).forEach(function (name) {
    const sh = ss.getSheetByName(name) || ss.insertSheet(name);
    if (sh.getRange(1, 1).getValue() !== headers[name][0]) {
      sh.getRange(1, 1, 1, headers[name].length).setValues([headers[name]]);
      sh.setFrozenRows(1);
    }
  });
}

function links_(name) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  return sh.getRange(2, 1, n, 1).getValues()
    .map(function (r) { return String(r[0]).trim(); })
    .filter(Boolean);
}

function getStatus() {
  ensureTabs_();
  return { queue: links_(QUEUE).length, failed: links_(FAILED).length };
}

function addLinks(text) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    ensureTabs_();
    const q = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(QUEUE);
    const seen = {};
    links_(QUEUE).concat(links_(FAILED)).forEach(function (l) { seen[l] = true; });
    const res = { added: 0, duplicate: 0, invalid: 0 };
    const rows = [];
    String(text || '').split(/\s+/).forEach(function (raw) {
      const l = raw.trim();
      if (!l) return;
      if (!FB_LINK.test(l)) res.invalid++;
      else if (seen[l]) res.duplicate++;
      else { seen[l] = true; rows.push([l, new Date()]); res.added++; }
    });
    if (rows.length) q.getRange(q.getLastRow() + 1, 1, rows.length, 2).setValues(rows);
    const st = getStatus();
    res.queue = st.queue;
    res.failed = st.failed;
    return res;
  } finally {
    lock.releaseLock();
  }
}
