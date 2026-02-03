const path = require("path");

const pino = require("pino");
const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
} = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");

const BACKEND_INGEST_URL =
  process.env.BACKEND_INGEST_URL || "http://backend:8000/news";
const BACKEND_SOURCES_URL = new URL("/sources", BACKEND_INGEST_URL).toString();
const BACKEND_SETTINGS_URL = new URL(
  "/settings/runtime",
  BACKEND_INGEST_URL,
).toString();
const SESSION_DIR =
  process.env.WA_SESSION_DIR || path.join(process.cwd(), "session");
const DEFAULT_LOG_LEVEL = process.env.WA_LOG_LEVEL || "info";
const DEFAULT_PHONE_NUMBER = (process.env.WA_PHONE_NUMBER || "").replace(/\D/g, "");
const DEFAULT_SYNC_INTERVAL_MS = Number(process.env.WA_SYNC_INTERVAL_MS || 300000);
const SETTINGS_CACHE_TTL_MS = 30 * 1000;

function ingestHeaders() {
  const token = (process.env.INGEST_TOKEN || "").trim();
  if (!token) return {};
  return { "X-Ingest-Token": token };
}

let pairingRequested = false;
let groupsLogged = false;
let syncIntervalId = null;
const GROUP_CACHE_TTL_MS = 10 * 60 * 1000;
const groupCache = new Map();
const settingsCache = { fetchedAt: 0, data: null };

async function requestPairingCode(socket, state, phoneNumber) {
  if (!phoneNumber) return;
  if (state.creds.registered) return;
  if (!socket.ws?.isOpen) return;
  if (pairingRequested) return;

  pairingRequested = true;
  try {
    const code = await socket.requestPairingCode(phoneNumber);
    console.log(`Pairing code: ${code}`);
    console.log("WhatsApp -> Linked Devices -> Link with phone number.");
  } catch (err) {
    pairingRequested = false;
    console.error("pairing code failed", err);
  }
}

function extractText(message) {
  if (!message) return null;
  return (
    message.conversation ||
    message.extendedTextMessage?.text ||
    message.imageMessage?.caption ||
    message.videoMessage?.caption ||
    message.documentMessage?.caption ||
    message.buttonsResponseMessage?.selectedDisplayText ||
    message.listResponseMessage?.title ||
    message.templateButtonReplyMessage?.selectedId ||
    null
  );
}

async function sendToBackend(payload) {
  try {
    const response = await fetch(BACKEND_INGEST_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...ingestHeaders() },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const body = await response.text();
      console.error("ingest failed", response.status, body);
    }
  } catch (err) {
    console.error("ingest error", err);
  }
}

async function fetchRuntimeSettings() {
  try {
    const response = await fetch(BACKEND_SETTINGS_URL, { headers: ingestHeaders() });
    if (!response.ok) {
      const body = await response.text();
      console.error("settings fetch failed", response.status, body);
      return null;
    }
    const data = await response.json();
    return data && typeof data === "object" ? data : null;
  } catch (err) {
    console.error("settings fetch error", err);
    return null;
  }
}

function mergeWhatsAppSettings(raw) {
  const settings = raw || {};
  const phoneNumber = (settings.phone_number || DEFAULT_PHONE_NUMBER || "").replace(
    /\D/g,
    "",
  );
  return {
    enabled: settings.enabled !== false,
    phoneNumber,
    logLevel: settings.log_level || DEFAULT_LOG_LEVEL,
  };
}

async function getWhatsAppSettings() {
  const now = Date.now();
  if (!settingsCache.fetchedAt || now - settingsCache.fetchedAt > SETTINGS_CACHE_TTL_MS) {
    const data = await fetchRuntimeSettings();
    if (data && data.whatsapp) {
      settingsCache.data = data.whatsapp;
    }
    settingsCache.fetchedAt = now;
  }
  return mergeWhatsAppSettings(settingsCache.data);
}

async function waitForWhatsAppSettings() {
  while (true) {
    const settings = await getWhatsAppSettings();
    if (settings.enabled) {
      return settings;
    }
    console.log("WhatsApp connector disabled; waiting 30s.");
    await new Promise((resolve) => setTimeout(resolve, 30000));
  }
}

async function fetchSourcesFromBackend() {
  try {
    const url = new URL(BACKEND_SOURCES_URL);
    url.searchParams.set("platform", "whatsapp");
    const response = await fetch(url.toString(), { headers: ingestHeaders() });
    if (!response.ok) {
      const body = await response.text();
      console.error("source list failed", response.status, body);
      return null;
    }
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error("source list error", err);
    return null;
  }
}

async function createSource(payload) {
  try {
    const response = await fetch(BACKEND_SOURCES_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...ingestHeaders() },
      body: JSON.stringify(payload),
    });
    if (response.ok || response.status === 409) {
      return;
    }
    const body = await response.text();
    console.error("source sync failed", response.status, body);
  } catch (err) {
    console.error("source sync error", err);
  }
}

async function updateSource(sourceId, payload) {
  try {
    const response = await fetch(`${BACKEND_SOURCES_URL}/${sourceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...ingestHeaders() },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const body = await response.text();
      console.error("source update failed", response.status, body);
    }
  } catch (err) {
    console.error("source update error", err);
  }
}


async function syncGroupSources(groups) {
  const existingSources = (await fetchSourcesFromBackend()) || [];
  const existingById = new Map(
    existingSources.map((source) => [source.identifier, source]),
  );
  const currentIds = new Set(groups.map((group) => group.id).filter(Boolean));
  let created = 0;
  let renamed = 0;
  let disabled = 0;
  for (const group of groups) {
    if (!group?.id) continue;
    const name = group.subject || group.id;
    const existing = existingById.get(group.id);
    if (existing) {
      if (existing.name !== name) {
        await updateSource(existing.id, { name });
        renamed += 1;
      }
      continue;
    }
    await createSource({
      name,
      platform: "whatsapp",
      identifier: group.id,
      is_active: true,
    });
    created += 1;
  }
  for (const [identifier, source] of existingById.entries()) {
    if (!currentIds.has(identifier)) {
      if (source.is_active === true) {
        await updateSource(source.id, { is_active: false });
        disabled += 1;
      }
    }
  }
  if (created > 0 || renamed > 0 || disabled > 0) {
    console.log(`Sources synced: added ${created}, renamed ${renamed}, disabled ${disabled}.`);
  }
}

async function syncGroups(socket) {
  const groups = await socket.groupFetchAllParticipating();
  const entries = Object.values(groups).sort((a, b) =>
    (a.subject || "").localeCompare(b.subject || ""),
  );
  const currentIds = new Set(entries.map((group) => group.id));
  for (const id of groupCache.keys()) {
    if (!currentIds.has(id)) {
      groupCache.delete(id);
    }
  }
  for (const group of entries) {
    groupCache.set(group.id, {
      subject: group.subject,
      expiresAt: Date.now() + GROUP_CACHE_TTL_MS,
    });
  }
  await syncGroupSources(entries);
  return entries;
}

function scheduleGroupSync(socket) {
  if (syncIntervalId) {
    clearInterval(syncIntervalId);
    syncIntervalId = null;
  }
  const interval = Number.isFinite(DEFAULT_SYNC_INTERVAL_MS)
    ? Math.max(DEFAULT_SYNC_INTERVAL_MS, 30000)
    : 300000;
  syncIntervalId = setInterval(() => {
    syncGroups(socket).catch((err) => {
      console.error("group source sync failed", err);
    });
  }, interval);
}

async function getGroupSubject(socket, groupJid) {
  const now = Date.now();
  const cached = groupCache.get(groupJid);
  if (cached?.subject && cached.expiresAt > now) {
    return cached.subject;
  }
  if (cached?.pending) {
    return cached.pending;
  }

  const pending = socket
    .groupMetadata(groupJid)
    .then((meta) => {
      const subject = meta?.subject || groupJid;
      groupCache.set(groupJid, {
        subject,
        expiresAt: now + GROUP_CACHE_TTL_MS,
      });
      return subject;
    })
    .catch((err) => {
      groupCache.delete(groupJid);
      console.error("group metadata failed", groupJid, err);
      return groupJid;
    });

  groupCache.set(groupJid, { pending });
  return pending;
}

async function start() {
  const runtimeSettings = await waitForWhatsAppSettings();
  const phoneNumber = runtimeSettings.phoneNumber;
  const usePairing = Boolean(phoneNumber);
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
  const socket = makeWASocket({
    auth: state,
    printQRInTerminal: !usePairing,
    logger: pino({ level: runtimeSettings.logLevel }),
  });

  if (usePairing) {
    socket.ws.on("open", () => {
      requestPairingCode(socket, state, phoneNumber);
    });
  }

  socket.ev.on("creds.update", saveCreds);

  socket.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log(`QR data: ${qr}`);
      qrcode.generate(qr, { small: true });
      console.log("Scan the QR from WhatsApp -> Linked Devices.");
    }
    if (connection === "open" && !groupsLogged) {
      groupsLogged = true;
      syncGroups(socket)
        .then((entries) => {
          console.log(`Groups (${entries.length}):`);
          for (const group of entries) {
            console.log(`- ${group.subject} (${group.id})`);
          }
        })
        .catch((err) => {
          groupsLogged = false;
          console.error("group list failed", err);
        });
      scheduleGroupSync(socket);
    }
    if (connection === "close") {
      if (syncIntervalId) {
        clearInterval(syncIntervalId);
        syncIntervalId = null;
      }
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const message =
        lastDisconnect?.error?.output?.payload?.message ||
        lastDisconnect?.error?.message;
      if (statusCode || message) {
        console.error("connection closed", statusCode, message);
      }
      const shouldReconnect =
        lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      if (shouldReconnect) {
        start();
      } else {
        console.error("logged out, delete session and re-scan QR");
      }
    }
  });

  socket.ev.on("messages.upsert", async (event) => {
    const message = event.messages?.[0];
    if (!message || message.key.fromMe) return;
    if (message.key.remoteJid === "status@broadcast") return;

    const settings = await getWhatsAppSettings();
    if (!settings.enabled) return;

    const text = extractText(message.message);
    if (!text) return;

    const timestampSec = Number(message.messageTimestamp || Date.now() / 1000);
    const remoteJid = message.key.remoteJid;
    const isGroup = remoteJid?.endsWith("@g.us");
    let sourceName = message.pushName || remoteJid;
    let authorName = message.pushName || null;

    if (isGroup) {
      sourceName = await getGroupSubject(socket, remoteJid);
      if (!authorName) {
        const participant = message.key.participant;
        authorName = participant ? participant.split("@")[0] : null;
      }
    }

    const payload = {
      source_name: sourceName,
      source_identifier: remoteJid,
      platform: "whatsapp",
      source_message_id: message.key.id,
      author_name: authorName,
      content: text,
      timestamp: new Date(timestampSec * 1000).toISOString(),
    };

    await sendToBackend(payload);
  });
}

start().catch((err) => {
  console.error("baileys init failed", err);
  process.exit(1);
});
