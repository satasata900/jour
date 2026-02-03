const { useEffect, useMemo, useState } = React;

const API_BASE = "";
const BASE_PATH = "/dashboard";

const NAV_ITEMS = [
  { key: "overview", label: "Overview", path: "/dashboard" },
  { key: "feed", label: "Live Feed", path: "/dashboard/feed" },
  { key: "sources", label: "Sources", path: "/dashboard/sources" },
  { key: "settings", label: "Settings", path: "/dashboard/settings" },
  { key: "agents", label: "Agents", path: "/dashboard/agents" },
];

const PLATFORM_OPTIONS = [
  { value: "all", label: "All" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "telegram", label: "Telegram" },
  { value: "rss", label: "RSS" },
];

const SOURCE_STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

const SOURCE_TABS = [
  { value: "all", label: "All" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "telegram", label: "Telegram" },
  { value: "rss", label: "RSS" },
];

const AGENT_TYPE_OPTIONS = [
  { value: "router", label: "Router" },
  { value: "monitor", label: "Monitor" },
  { value: "editor", label: "Editor" },
  { value: "search", label: "Search" },
  { value: "general", label: "General" },
  { value: "custom", label: "Custom" },
];

const LLM_PROVIDER_OPTIONS = [
  { value: "openrouter", label: "OpenRouter (recommended)" },
  { value: "gemini", label: "Gemini" },
];

const AGENT_TEMPLATE_FIELDS = {
  router: ["{task}", "{context}", "{format_instructions}"],
  monitor: ["{window}", "{stats}"],
  editor: ["{task}", "{content}"],
  search: ["{task}"],
  general: ["{task}", "{context}"],
  custom: ["{task}"],
};

function formatTimestamp(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function normalizeLabelList(labels) {
  const items = Array.isArray(labels) ? labels : [];
  const seen = new Set();
  const result = [];
  for (const raw of items) {
    const value = String(raw || "").trim();
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result;
}

function parseLabelText(value) {
  if (!value) return [];
  return normalizeLabelList(value.split(","));
}

function labelsToText(labels) {
  return normalizeLabelList(labels).join(", ");
}

function normalizeRssUrl(value) {
  if (!value) return "";
  let url = String(value || "").trim();
  if (!url) return "";
  if (!/^https?:\/\//i.test(url)) {
    url = `https://${url}`;
  }
  return url;
}

function deriveRssName(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch (_) {
    return url;
  }
}

function platformBadgeClass(platform) {
  if (platform === "whatsapp") return "badge-whatsapp";
  if (platform === "telegram") return "badge-telegram";
  if (platform === "rss") return "badge-rss";
  return "";
}

function resolveRoute(pathname) {
  if (!pathname.startsWith(BASE_PATH)) return "overview";
  let path = pathname.slice(BASE_PATH.length);
  if (!path || path === "/") return "overview";
  if (path.startsWith("/")) path = path.slice(1);
  const key = path.split("/")[0];
  return NAV_ITEMS.some((item) => item.key === key) ? key : "overview";
}

function resolveAgentKey(pathname) {
  if (!pathname.startsWith(BASE_PATH)) return null;
  let path = pathname.slice(BASE_PATH.length);
  if (!path || path === "/") return null;
  if (path.startsWith("/")) path = path.slice(1);
  const parts = path.split("/").filter(Boolean);
  if (parts[0] !== "agents") return null;
  return parts[1] || null;
}

function App() {
  const [route, setRoute] = useState(() => resolveRoute(window.location.pathname));
  const [agentFocusKey, setAgentFocusKey] = useState(() =>
    resolveAgentKey(window.location.pathname)
  );
  const [agentFocusTab, setAgentFocusTab] = useState("profile");
  const [items, setItems] = useState([]);
  const [sources, setSources] = useState([]);
  const [sourcesStatus, setSourcesStatus] = useState("idle");
  const [sourcesError, setSourcesError] = useState("");
  const [newsStats, setNewsStats] = useState({
    total: 0,
    latest_timestamp: null,
    by_platform: [],
    by_source: [],
  });
  const [newsStatsStatus, setNewsStatsStatus] = useState("idle");
  const [newsStatsError, setNewsStatsError] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [platform, setPlatform] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [minScore, setMinScore] = useState("any");
  const [limit, setLimit] = useState(50);
  const [query, setQuery] = useState("");
  const [sourceQuery, setSourceQuery] = useState("");
  const [sourcePlatformFilter, setSourcePlatformFilter] = useState("all");
  const [sourceActiveFilter, setSourceActiveFilter] = useState("all");
  const [rssDraft, setRssDraft] = useState({
    name: "",
    url: "",
    isSaving: false,
    error: "",
  });
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [sourceEdits, setSourceEdits] = useState({});
  const [agents, setAgents] = useState([]);
  const [agentsStatus, setAgentsStatus] = useState("idle");
  const [agentsError, setAgentsError] = useState("");
  const [agentEdits, setAgentEdits] = useState({});
  const [agentCreate, setAgentCreate] = useState({
    key: "",
    name: "",
    description: "",
    agent_type: "custom",
    system_prompt: "You are a newsroom assistant. Write the response in Arabic.",
    user_prompt: "Task: {task}\nContext: {context}",
    is_active: true,
  });
  const [agentCreateStatus, setAgentCreateStatus] = useState("idle");
  const [agentCreateError, setAgentCreateError] = useState("");
  const [openAgentId, setOpenAgentId] = useState(null);
  const [agentTask, setAgentTask] = useState("");
  const [agentContext, setAgentContext] = useState("");
  const [agentRoute, setAgentRoute] = useState("auto");
  const [agentWindowHours, setAgentWindowHours] = useState(24);
  const [agentMaxItems, setAgentMaxItems] = useState(50);
  const [agentStatus, setAgentStatus] = useState("idle");
  const [agentError, setAgentError] = useState("");
  const [agentOutput, setAgentOutput] = useState("");
  const [agentMeta, setAgentMeta] = useState(null);
  const [agentResultRoute, setAgentResultRoute] = useState("");
  const [agentHealth, setAgentHealth] = useState("idle");
  const [agentHealthError, setAgentHealthError] = useState("");
  const [agentHealthData, setAgentHealthData] = useState(null);
  const [agentLastRun, setAgentLastRun] = useState(null);
  const [settingsStatus, setSettingsStatus] = useState("idle");
  const [settingsError, setSettingsError] = useState("");
  const [openrouterModels, setOpenrouterModels] = useState([]);
  const [openrouterStatus, setOpenrouterStatus] = useState("idle");
  const [openrouterError, setOpenrouterError] = useState("");
  const [openrouterFreeOnly, setOpenrouterFreeOnly] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState({
    keys: false,
    ai: false,
    search: false,
    retention: false,
    chat_retention: false,
    telegram: false,
    telegram_bot: false,
    whatsapp: false,
  });
  const [settingsData, setSettingsData] = useState({
    keys: { gemini_api_key: "", openrouter_api_key: "", tavily_api_key: "" },
    ai: {
      gemini_api_version: "v1",
      agent_llm_provider: "openrouter",
      summary_model: "",
      agent_llm_model: "",
      summary_timezone: "Asia/Damascus",
      summary_run_interval_seconds: 300,
      summary_max_messages: 200,
      summary_max_chars: 120000,
    },
    search: {
      provider: "searxng",
      searxng_base_url: "",
      searxng_timeout_seconds: 15,
      searxng_max_results: 5,
      searxng_language: "all",
      searxng_safe_search: 0,
      searxng_time_range: "",
      searxng_categories: "",
      searxng_engines: "",
    },
    retention: { days: 1, min_days: 1, max_days: 365, source: "default" },
    chat_retention: { days: 7, min_days: 1, max_days: 30, source: "default" },
    telegram: {
      enabled: true,
      api_id: "",
      api_hash: "",
      phone_number: "",
      session_name: "telegram",
      log_level: "info",
      include_private: false,
      log_groups: false,
    },
    telegram_bot: { enabled: false, token: "", username: "" },
    whatsapp: { enabled: true, phone_number: "", log_level: "info" },
  });
  const [settingsDraft, setSettingsDraft] = useState({
    keys: { gemini_api_key: "", openrouter_api_key: "", tavily_api_key: "" },
    ai: {
      gemini_api_version: "v1",
      agent_llm_provider: "openrouter",
      summary_model: "",
      agent_llm_model: "",
      summary_timezone: "Asia/Damascus",
      summary_run_interval_seconds: "300",
      summary_max_messages: "200",
      summary_max_chars: "120000",
    },
    search: {
      provider: "searxng",
      searxng_base_url: "",
      searxng_timeout_seconds: "15",
      searxng_max_results: "5",
      searxng_language: "all",
      searxng_safe_search: "0",
      searxng_time_range: "",
      searxng_categories: "",
      searxng_engines: "",
    },
    retention: { days: "1" },
    chat_retention: { days: "7" },
    telegram: {
      enabled: true,
      api_id: "",
      api_hash: "",
      phone_number: "",
      session_name: "telegram",
      log_level: "info",
      include_private: false,
      log_groups: false,
    },
    telegram_bot: { enabled: false, token: "", username: "" },
    whatsapp: { enabled: true, phone_number: "", log_level: "info" },
  });

  const fetchSources = async () => {
    setSourcesStatus("loading");
    setSourcesError("");
    try {
      const response = await fetch(`${API_BASE}/sources`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setSources(Array.isArray(data) ? data : []);
      setSourcesStatus("ready");
    } catch (err) {
      setSources([]);
      setSourcesStatus("error");
      setSourcesError(err.message || "Failed to fetch sources");
    }
  };

  const applySettings = (data) => {
    const normalized = {
      keys: {
        gemini_api_key: data?.keys?.gemini_api_key || "",
        openrouter_api_key: data?.keys?.openrouter_api_key || "",
        tavily_api_key: data?.keys?.tavily_api_key || "",
      },
      ai: {
        gemini_api_version: data?.ai?.gemini_api_version || "v1",
        agent_llm_provider: data?.ai?.agent_llm_provider || "openrouter",
        summary_model: data?.ai?.summary_model || "",
        agent_llm_model: data?.ai?.agent_llm_model || "",
        summary_timezone: data?.ai?.summary_timezone || "UTC",
        summary_run_interval_seconds: data?.ai?.summary_run_interval_seconds ?? 900,
        summary_max_messages: data?.ai?.summary_max_messages ?? 200,
        summary_max_chars: data?.ai?.summary_max_chars ?? 120000,
      },
      search: {
        provider: data?.search?.provider || "searxng",
        searxng_base_url: data?.search?.searxng_base_url || "",
        searxng_timeout_seconds: data?.search?.searxng_timeout_seconds ?? 15,
        searxng_max_results: data?.search?.searxng_max_results ?? 5,
        searxng_language: data?.search?.searxng_language || "all",
        searxng_safe_search: data?.search?.searxng_safe_search ?? 0,
        searxng_time_range: data?.search?.searxng_time_range || "",
        searxng_categories: data?.search?.searxng_categories || "",
        searxng_engines: data?.search?.searxng_engines || "",
      },
      retention: {
        days: data?.retention?.days ?? 1,
        min_days: data?.retention?.min_days ?? 1,
        max_days: data?.retention?.max_days ?? 365,
        source: data?.retention?.source || "default",
      },
      chat_retention: {
        days: data?.chat_retention?.days ?? 7,
        min_days: data?.chat_retention?.min_days ?? 1,
        max_days: data?.chat_retention?.max_days ?? 30,
        source: data?.chat_retention?.source || "default",
      },
      telegram: {
        enabled: data?.telegram?.enabled ?? true,
        api_id: data?.telegram?.api_id || "",
        api_hash: data?.telegram?.api_hash || "",
        phone_number: data?.telegram?.phone_number || "",
        session_name: data?.telegram?.session_name || "telegram",
        log_level: data?.telegram?.log_level || "info",
        include_private: data?.telegram?.include_private ?? false,
        log_groups: data?.telegram?.log_groups ?? false,
      },
      telegram_bot: {
        enabled: data?.telegram_bot?.enabled ?? false,
        token: data?.telegram_bot?.token || "",
        username: data?.telegram_bot?.username || "",
      },
      whatsapp: {
        enabled: data?.whatsapp?.enabled ?? true,
        phone_number: data?.whatsapp?.phone_number || "",
        log_level: data?.whatsapp?.log_level || "info",
      },
    };

    setSettingsData(normalized);
    setSettingsDraft({
      keys: {
        gemini_api_key: normalized.keys.gemini_api_key,
        openrouter_api_key: normalized.keys.openrouter_api_key,
        tavily_api_key: normalized.keys.tavily_api_key,
      },
      ai: {
        gemini_api_version: normalized.ai.gemini_api_version,
        agent_llm_provider: normalized.ai.agent_llm_provider,
        summary_model: normalized.ai.summary_model,
        agent_llm_model: normalized.ai.agent_llm_model,
        summary_timezone: normalized.ai.summary_timezone,
        summary_run_interval_seconds: String(
          normalized.ai.summary_run_interval_seconds,
        ),
        summary_max_messages: String(normalized.ai.summary_max_messages),
        summary_max_chars: String(normalized.ai.summary_max_chars),
      },
      search: {
        provider: normalized.search.provider,
        searxng_base_url: normalized.search.searxng_base_url,
        searxng_timeout_seconds: String(normalized.search.searxng_timeout_seconds),
        searxng_max_results: String(normalized.search.searxng_max_results),
        searxng_language: normalized.search.searxng_language,
        searxng_safe_search: String(normalized.search.searxng_safe_search),
        searxng_time_range: normalized.search.searxng_time_range,
        searxng_categories: normalized.search.searxng_categories,
        searxng_engines: normalized.search.searxng_engines,
      },
      retention: { days: String(normalized.retention.days) },
      chat_retention: { days: String(normalized.chat_retention.days) },
      telegram: { ...normalized.telegram },
      telegram_bot: { ...normalized.telegram_bot },
      whatsapp: { ...normalized.whatsapp },
    });
  };

  const updateSettingsDraft = (section, field, value) => {
    setSettingsDraft((prev) => ({
      ...prev,
      [section]: { ...(prev[section] || {}), [field]: value },
    }));
  };

  const fetchSettings = async () => {
    setSettingsStatus("loading");
    setSettingsError("");
    try {
      const response = await fetch(`${API_BASE}/settings`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      applySettings(data);
      setSettingsStatus("ready");
    } catch (err) {
      setSettingsStatus("error");
      setSettingsError(err.message || "Failed to fetch settings");
    }
  };

  const fetchOpenRouterModels = async (keyOverride) => {
    const apiKey =
      typeof keyOverride === "string" && keyOverride.trim()
        ? keyOverride.trim()
        : settingsDraft.keys.openrouter_api_key.trim();
    setOpenrouterStatus("loading");
    setOpenrouterError("");
    try {
      const headers = {};
      if (apiKey) {
        headers["X-OpenRouter-Key"] = apiKey;
      }
      const response = await fetch(`${API_BASE}/settings/openrouter/models`, {
        headers,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      const models = Array.isArray(data.models) ? data.models : [];
      setOpenrouterModels(models);
      setOpenrouterStatus("ready");
    } catch (err) {
      setOpenrouterModels([]);
      setOpenrouterStatus("error");
      setOpenrouterError(err.message || "Failed to load OpenRouter models");
    }
  };

  const saveSettingsSection = async (section) => {
    setSettingsSaving((prev) => ({ ...prev, [section]: true }));
    setSettingsError("");
    try {
      const payload = {};
      if (section === "keys") {
        payload.keys = {
          gemini_api_key: settingsDraft.keys.gemini_api_key.trim(),
          openrouter_api_key: settingsDraft.keys.openrouter_api_key.trim(),
          tavily_api_key: settingsDraft.keys.tavily_api_key.trim(),
        };
      } else if (section === "ai") {
        const runInterval = Number.parseInt(
          settingsDraft.ai.summary_run_interval_seconds,
          10,
        );
        const maxMessages = Number.parseInt(
          settingsDraft.ai.summary_max_messages,
          10,
        );
        const maxChars = Number.parseInt(settingsDraft.ai.summary_max_chars, 10);
        if (!Number.isFinite(runInterval)) {
          throw new Error("Summary interval must be a number.");
        }
        if (!Number.isFinite(maxMessages)) {
          throw new Error("Summary max messages must be a number.");
        }
        if (!Number.isFinite(maxChars)) {
          throw new Error("Summary max chars must be a number.");
        }
        payload.ai = {
          gemini_api_version: settingsDraft.ai.gemini_api_version.trim(),
          agent_llm_provider: settingsDraft.ai.agent_llm_provider.trim(),
          summary_model: settingsDraft.ai.summary_model.trim(),
          agent_llm_model: settingsDraft.ai.agent_llm_model.trim(),
          summary_timezone: settingsDraft.ai.summary_timezone.trim(),
          summary_run_interval_seconds: runInterval,
          summary_max_messages: maxMessages,
          summary_max_chars: maxChars,
        };
      } else if (section === "search") {
        const timeoutSeconds = Number.parseInt(
          settingsDraft.search.searxng_timeout_seconds,
          10,
        );
        const maxResults = Number.parseInt(
          settingsDraft.search.searxng_max_results,
          10,
        );
        const safeSearch = Number.parseInt(
          settingsDraft.search.searxng_safe_search,
          10,
        );
        if (!Number.isFinite(timeoutSeconds)) {
          throw new Error("Search timeout must be a number.");
        }
        if (!Number.isFinite(maxResults)) {
          throw new Error("Search max results must be a number.");
        }
        if (!Number.isFinite(safeSearch)) {
          throw new Error("Safe search must be a number.");
        }
        const baseUrl = settingsDraft.search.searxng_base_url.trim();
        if (!baseUrl) {
          throw new Error("SearXNG base URL is required.");
        }
        payload.search = {
          provider: settingsDraft.search.provider.trim() || "searxng",
          searxng_base_url: baseUrl,
          searxng_timeout_seconds: timeoutSeconds,
          searxng_max_results: maxResults,
          searxng_language: settingsDraft.search.searxng_language.trim(),
          searxng_safe_search: safeSearch,
          searxng_time_range: settingsDraft.search.searxng_time_range.trim(),
          searxng_categories: settingsDraft.search.searxng_categories.trim(),
          searxng_engines: settingsDraft.search.searxng_engines.trim(),
        };
      } else if (section === "retention") {
        const days = Number.parseInt(settingsDraft.retention.days, 10);
        if (!Number.isFinite(days)) {
          throw new Error("Retention days must be a number.");
        }
        payload.retention = { days };
      } else if (section === "chat_retention") {
        const days = Number.parseInt(settingsDraft.chat_retention.days, 10);
        if (!Number.isFinite(days)) {
          throw new Error("Chat retention days must be a number.");
        }
        payload.chat_retention = { days };
      } else if (section === "telegram") {
        payload.telegram = {
          enabled: Boolean(settingsDraft.telegram.enabled),
          api_id: settingsDraft.telegram.api_id.trim(),
          api_hash: settingsDraft.telegram.api_hash.trim(),
          phone_number: settingsDraft.telegram.phone_number.trim(),
          session_name: settingsDraft.telegram.session_name.trim(),
          log_level: settingsDraft.telegram.log_level.trim(),
          include_private: Boolean(settingsDraft.telegram.include_private),
          log_groups: Boolean(settingsDraft.telegram.log_groups),
        };
      } else if (section === "telegram_bot") {
        const token = settingsDraft.telegram_bot.token.trim();
        const username = settingsDraft.telegram_bot.username.trim();
        const enabled = Boolean(settingsDraft.telegram_bot.enabled);
        if (enabled && !token) {
          throw new Error("Telegram bot token is required.");
        }
        payload.telegram_bot = {
          enabled,
          token,
          username,
        };
      } else if (section === "whatsapp") {
        payload.whatsapp = {
          enabled: Boolean(settingsDraft.whatsapp.enabled),
          phone_number: settingsDraft.whatsapp.phone_number.trim(),
          log_level: settingsDraft.whatsapp.log_level.trim(),
        };
      }

      const response = await fetch(`${API_BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      applySettings(data);
      setSettingsStatus("ready");
    } catch (err) {
      setSettingsStatus("error");
      setSettingsError(err.message || "Failed to update settings");
    } finally {
      setSettingsSaving((prev) => ({ ...prev, [section]: false }));
    }
  };

  const fetchNews = async () => {
    setStatus("loading");
    setError("");
    try {
      const params = new URLSearchParams();
      params.set("limit", limit.toString());
      params.set("active_only", "true");
      if (platform !== "all") {
        params.set("platform", platform);
      }
      if (minScore !== "any") {
        params.set("min_score", minScore);
      }
      if (sourceFilter !== "all") {
        params.set("source_id", sourceFilter);
      }
      const response = await fetch(`${API_BASE}/news?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setItems(Array.isArray(data) ? data : []);
      setLastUpdated(new Date());
      setStatus("ready");
    } catch (err) {
      setStatus("error");
      setError(err.message || "Failed to fetch news");
    }
  };

  const fetchNewsStats = async () => {
    setNewsStatsStatus("loading");
    setNewsStatsError("");
    try {
      const response = await fetch(`${API_BASE}/news/stats`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setNewsStats({
        total: Number(data?.total) || 0,
        latest_timestamp: data?.latest_timestamp || null,
        by_platform: Array.isArray(data?.by_platform) ? data.by_platform : [],
        by_source: Array.isArray(data?.by_source) ? data.by_source : [],
      });
      setNewsStatsStatus("ready");
    } catch (err) {
      setNewsStatsStatus("error");
      setNewsStatsError(err.message || "Failed to fetch message stats");
    }
  };

  const updateSource = async (sourceId, payload) => {
    setSourceEdits((prev) => ({
      ...prev,
      [sourceId]: { ...(prev[sourceId] || {}), isSaving: true, error: "" },
    }));
    try {
      const response = await fetch(`${API_BASE}/sources/${sourceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const updated = await response.json();
      setSources((prev) =>
        prev.map((source) => (source.id === sourceId ? updated : source))
      );
      setSourceEdits((prev) => ({
        ...prev,
        [sourceId]: {
          ...(prev[sourceId] || {}),
          labelsText: labelsToText(updated.labels),
          isSaving: false,
          error: "",
        },
      }));
    } catch (err) {
      setSourceEdits((prev) => ({
        ...prev,
        [sourceId]: {
          ...(prev[sourceId] || {}),
          isSaving: false,
          error: err.message || "Failed to update source",
        },
      }));
    }
  };

  const createSource = async (payload) => {
    const response = await fetch(`${API_BASE}/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    return data;
  };

  const deleteSource = async (sourceId) => {
    const response = await fetch(`${API_BASE}/sources/${sourceId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
  };

  const fetchAgents = async () => {
    setAgentsStatus("loading");
    setAgentsError("");
    try {
      const response = await fetch(`${API_BASE}/agents`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setAgents(Array.isArray(data) ? data : []);
      setAgentsStatus("ready");
    } catch (err) {
      setAgents([]);
      setAgentsStatus("error");
      setAgentsError(err.message || "Failed to fetch agents");
    }
  };

  const updateAgentProfile = async (agentId, payload) => {
    setAgentEdits((prev) => ({
      ...prev,
      [agentId]: { ...(prev[agentId] || {}), isSaving: true, error: "" },
    }));
    try {
      const response = await fetch(`${API_BASE}/agents/${agentId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      setAgents((prev) =>
        prev.map((agent) => (agent.id === agentId ? data : agent))
      );
      setAgentEdits((prev) => ({
        ...prev,
        [agentId]: {
          ...(prev[agentId] || {}),
          ...data,
          isSaving: false,
          error: "",
        },
      }));
    } catch (err) {
      setAgentEdits((prev) => ({
        ...prev,
        [agentId]: {
          ...(prev[agentId] || {}),
          isSaving: false,
          error: err.message || "Failed to update agent",
        },
      }));
    }
  };

  const deleteAgentProfile = async (agent) => {
    if (!window.confirm(`Delete agent "${agent.name}"?`)) return;
    setAgentsStatus("loading");
    setAgentsError("");
    try {
      const response = await fetch(`${API_BASE}/agents/${agent.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      setAgents((prev) => prev.filter((item) => item.id !== agent.id));
      setAgentsStatus("ready");
    } catch (err) {
      setAgentsStatus("error");
      setAgentsError(err.message || "Failed to delete agent");
    }
  };

  const createAgentProfile = async () => {
    setAgentCreateStatus("loading");
    setAgentCreateError("");
    try {
      const payload = {
        key: agentCreate.key.trim(),
        name: agentCreate.name.trim(),
        description: agentCreate.description.trim() || null,
        agent_type: agentCreate.agent_type,
        system_prompt: agentCreate.system_prompt.trim(),
        user_prompt: agentCreate.user_prompt.trim(),
        is_active: Boolean(agentCreate.is_active),
      };
      const response = await fetch(`${API_BASE}/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      setAgents((prev) => [...prev, data]);
      setAgentCreateStatus("ready");
      setAgentCreateError("");
      setAgentCreate({
        key: "",
        name: "",
        description: "",
        agent_type: "custom",
        system_prompt: "You are a newsroom assistant. Write the response in Arabic.",
        user_prompt: "Task: {task}\nContext: {context}",
        is_active: true,
      });
    } catch (err) {
      setAgentCreateStatus("error");
      setAgentCreateError(err.message || "Failed to create agent");
    }
  };

  const checkAgentHealth = async () => {
    setAgentHealth("loading");
    setAgentHealthError("");
    try {
      const response = await fetch(`${API_BASE}/agents/health`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      setAgentHealth("ready");
      setAgentHealthData(data);
    } catch (err) {
      setAgentHealth("error");
      setAgentHealthData(null);
      setAgentHealthError(err.message || "Failed to reach agent service");
    }
  };

  const runAgent = async (routeOverride) => {
    const task = agentTask.trim();
    if (!task) return;
    setAgentStatus("loading");
    setAgentError("");
    setAgentOutput("");
    setAgentMeta(null);
    setAgentResultRoute("");
    try {
      const windowHours = Math.min(Math.max(agentWindowHours || 24, 1), 168);
      const maxItems = Math.min(Math.max(agentMaxItems || 50, 1), 200);
      const payload = {
        task,
        window_hours: windowHours,
        max_items: maxItems,
      };
      const context = agentContext.trim();
      if (context) payload.context = context;
      if (typeof routeOverride === "string" && routeOverride.trim()) {
        payload.route = routeOverride.trim();
      } else if (agentRoute !== "auto") {
        payload.route = agentRoute;
      }
      const response = await fetch(`${API_BASE}/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      setAgentOutput(data.output || "");
      setAgentMeta(data.meta || null);
      setAgentResultRoute(data.route || "");
      setAgentStatus("ready");
      setAgentLastRun(new Date());
    } catch (err) {
      setAgentStatus("error");
      setAgentError(err.message || "Agent run failed");
    }
  };

  const openrouterFreeCount = useMemo(
    () => openrouterModels.filter((model) => model.is_free).length,
    [openrouterModels],
  );

  const openrouterVisibleModels = useMemo(() => {
    if (!openrouterFreeOnly) return openrouterModels;
    return openrouterModels.filter((model) => model.is_free);
  }, [openrouterModels, openrouterFreeOnly]);

    useEffect(() => {
      fetchSources();
    }, []);

    useEffect(() => {
      fetchAgents();
    }, []);

    useEffect(() => {
      fetchSettings();
    }, []);

    useEffect(() => {
      if (settingsDraft.ai.agent_llm_provider !== "openrouter") {
        setOpenrouterModels([]);
        setOpenrouterStatus("idle");
        setOpenrouterError("");
        return;
      }
      const handle = setTimeout(() => {
        fetchOpenRouterModels();
      }, 400);
      return () => clearTimeout(handle);
    }, [settingsDraft.ai.agent_llm_provider, settingsDraft.keys.openrouter_api_key]);

    useEffect(() => {
      fetchNewsStats();
    }, []);

    useEffect(() => {
      if (route === "sources" || route === "overview") {
        fetchNewsStats();
      }
    }, [route]);

  useEffect(() => {
    if (!agentFocusKey) return;
    if (agentFocusKey === "search") {
      setAgentFocusTab("engine");
    } else {
      setAgentFocusTab("profile");
    }
  }, [agentFocusKey]);

  useEffect(() => {
    setSourceEdits((prev) => {
      const next = { ...prev };
      for (const source of sources) {
        if (!next[source.id]) {
          next[source.id] = {
            labelsText: labelsToText(source.labels || []),
            isSaving: false,
            error: "",
          };
        }
      }
      return next;
    });
  }, [sources]);

  useEffect(() => {
    setAgentEdits((prev) => {
      const next = { ...prev };
      for (const agent of agents) {
        if (!next[agent.id]) {
          next[agent.id] = {
            ...agent,
            isSaving: false,
            error: "",
          };
        }
      }
      return next;
    });
  }, [agents]);

  useEffect(() => {
    fetchNews();
  }, [platform, minScore, limit, sourceFilter]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const id = setInterval(fetchNews, 30000);
    return () => clearInterval(id);
  }, [autoRefresh, platform, minScore, limit, sourceFilter]);

  useEffect(() => {
    const handlePop = () => {
      const path = window.location.pathname;
      setRoute(resolveRoute(path));
      setAgentFocusKey(resolveAgentKey(path));
    };
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  useEffect(() => {
    const baseLabel = NAV_ITEMS.find((item) => item.key === route)?.label || "Overview";
    const agentLabel = agentFocusKey
      ? agents.find((agent) => agent.key === agentFocusKey)?.name || agentFocusKey
      : null;
    const label =
      route === "agents" && agentLabel ? `Agents ? ${agentLabel}` : baseLabel;
    document.title = `Jour2 Dashboard ? ${label}`;
  }, [route, agentFocusKey, agents]);

  const navigate = (path) => {
    if (window.location.pathname === path) return;
    window.history.pushState({}, "", path);
    setRoute(resolveRoute(path));
    setAgentFocusKey(resolveAgentKey(path));
  };

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    const sourceMatch = sourceFilter !== "all" ? sourceFilter : null;
    return items.filter((item) => {
      const itemSourceId =
        item.source_id === null || item.source_id === undefined
          ? null
          : String(item.source_id);
      if (sourceMatch && itemSourceId !== sourceMatch) {
        return false;
      }
      if (!term) return true;
      const content = (item.content || "").toLowerCase();
      const source = (item.source_name || "").toLowerCase();
      const author = (item.author_name || "").toLowerCase();
      return (
        content.includes(term) ||
        source.includes(term) ||
        author.includes(term)
      );
    });
  }, [items, query, sourceFilter]);

  const counts = useMemo(() => {
    const base = { whatsapp: 0, telegram: 0, rss: 0 };
    for (const item of items) {
      if (item.platform === "whatsapp") base.whatsapp += 1;
      if (item.platform === "telegram") base.telegram += 1;
      if (item.platform === "rss") base.rss += 1;
    }
    return base;
  }, [items]);

  const sourceMessageCounts = useMemo(() => {
    const map = new Map();
    const rows = Array.isArray(newsStats.by_source) ? newsStats.by_source : [];
    for (const row of rows) {
      if (row?.source_id === null || row?.source_id === undefined) continue;
      map.set(String(row.source_id), Number(row.count) || 0);
    }
    return map;
  }, [newsStats]);

  const platformMessageCounts = useMemo(() => {
    const base = { whatsapp: 0, telegram: 0, rss: 0 };
    const rows = Array.isArray(newsStats.by_platform) ? newsStats.by_platform : [];
    for (const row of rows) {
      const key = String(row.platform || "").toLowerCase();
      if (Object.prototype.hasOwnProperty.call(base, key)) {
        base[key] = Number(row.count) || 0;
      }
    }
    return base;
  }, [newsStats]);

  const filteredSources = useMemo(() => {
    const term = sourceQuery.trim().toLowerCase();
    return [...sources]
      .filter((source) => {
        if (sourcePlatformFilter !== "all" && source.platform !== sourcePlatformFilter) {
          return false;
        }
        if (sourceActiveFilter === "active" && !source.is_active) return false;
        if (sourceActiveFilter === "inactive" && source.is_active) return false;
        if (!term) return true;
        const labelText = labelsToText(source.labels || []).toLowerCase();
        return (
          (source.name || "").toLowerCase().includes(term) ||
          (source.identifier || "").toLowerCase().includes(term) ||
          labelText.includes(term)
        );
      })
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [sources, sourceActiveFilter, sourcePlatformFilter, sourceQuery]);

  const sourceStats = useMemo(() => {
    const stats = { total: sources.length, active: 0, inactive: 0 };
    for (const source of sources) {
      if (source.is_active) stats.active += 1;
      else stats.inactive += 1;
    }
    return stats;
  }, [sources]);

  const sourcePlatformCounts = useMemo(() => {
    const counts = { all: sources.length, whatsapp: 0, telegram: 0, rss: 0 };
    for (const source of sources) {
      if (counts[source.platform] !== undefined) {
        counts[source.platform] += 1;
      }
    }
    return counts;
  }, [sources]);

  const sourceOptions = useMemo(() => {
    return sources
      .filter((source) => source.is_active)
      .slice()
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [sources]);

  const agentRouteOptions = useMemo(() => {
    const options = [{ value: "auto", label: "Auto route" }];
    const sorted = [...agents].sort((a, b) =>
      (a.name || a.key || "").localeCompare(b.name || b.key || "")
    );
    for (const agent of sorted) {
      if (!agent.is_active) continue;
      options.push({
        value: agent.key,
        label: `${agent.name || agent.key} (${agent.key})`,
      });
    }
    return options;
  }, [agents]);

  const agentNavItems = useMemo(() => {
    return [...agents]
      .sort((a, b) => (a.name || a.key || "").localeCompare(b.name || b.key || ""))
      .map((agent) => ({
        key: agent.key,
        label: agent.name || agent.key || "Agent",
        isActive: agent.is_active,
      }));
  }, [agents]);

  const focusedAgent = useMemo(() => {
    if (!agentFocusKey) return null;
    return agents.find((agent) => agent.key === agentFocusKey) || null;
  }, [agents, agentFocusKey]);

  const latestItems = useMemo(() => items.slice(0, 6), [items]);
  const statusLabel = status === "loading" ? "Syncing" : status === "error" ? "Issue" : "Live";
  const sourcesStatusLabel =
    sourcesStatus === "loading"
      ? "Syncing"
      : sourcesStatus === "error"
      ? "Issue"
      : "Ready";
  const agentsStatusLabel =
    agentsStatus === "loading"
      ? "Syncing"
      : agentsStatus === "error"
      ? "Issue"
      : "Ready";
  const settingsStatusLabel =
    settingsStatus === "loading"
      ? "Loading"
      : settingsStatus === "error"
      ? "Issue"
      : settingsStatus === "ready"
      ? "Ready"
      : "Idle";
  const newsStatsStatusLabel =
    newsStatsStatus === "loading"
      ? "Syncing"
      : newsStatsStatus === "error"
      ? "Issue"
      : newsStatsStatus === "ready"
      ? "Ready"
      : "Idle";
  const agentStatusLabel =
    agentStatus === "loading"
      ? "Running"
      : agentStatus === "error"
      ? "Error"
      : agentStatus === "ready"
      ? "Ready"
      : "Idle";
  const agentHealthLabel =
    agentHealth === "loading"
      ? "Checking"
      : agentHealth === "error"
      ? "Offline"
      : agentHealth === "ready"
      ? "Online"
      : "Idle";

  const handleSourceToggle = (source) => {
    const edit = sourceEdits[source.id];
    if (edit?.isSaving) return;
    updateSource(source.id, { is_active: !source.is_active });
  };

  const handleSourceLabelChange = (sourceId, value) => {
    setSourceEdits((prev) => ({
      ...prev,
      [sourceId]: { ...(prev[sourceId] || {}), labelsText: value },
    }));
  };

  const handleSourceSave = (source) => {
    const edit = sourceEdits[source.id];
    const labels = parseLabelText(edit?.labelsText || "");
    updateSource(source.id, { labels });
  };

  const handleRssCreate = async () => {
    const normalizedUrl = normalizeRssUrl(rssDraft.url);
    if (!normalizedUrl) {
      setRssDraft((prev) => ({
        ...prev,
        error: "RSS URL is required.",
      }));
      return;
    }
    const nameInput = rssDraft.name.trim();
    const name = nameInput || deriveRssName(normalizedUrl);
    setRssDraft((prev) => ({ ...prev, isSaving: true, error: "" }));
    try {
      const created = await createSource({
        name,
        platform: "rss",
        identifier: normalizedUrl,
        is_active: true,
        schedule_interval_minutes: 30,
        labels: [],
      });
      setSources((prev) => [created, ...prev]);
      setRssDraft({ name: "", url: "", isSaving: false, error: "" });
    } catch (err) {
      setRssDraft((prev) => ({
        ...prev,
        isSaving: false,
        error: err.message || "Failed to add RSS feed.",
      }));
    }
  };

  const handleRssDelete = async (source) => {
    const edit = sourceEdits[source.id];
    if (edit?.isDeleting) return;
    const confirmed = window.confirm(
      `Delete RSS feed \"${source.name || source.identifier}\"?`
    );
    if (!confirmed) return;
    setSourceEdits((prev) => ({
      ...prev,
      [source.id]: { ...(prev[source.id] || {}), isDeleting: true, error: "" },
    }));
    try {
      await deleteSource(source.id);
      setSources((prev) => prev.filter((item) => item.id !== source.id));
      setSourceEdits((prev) => {
        const next = { ...prev };
        delete next[source.id];
        return next;
      });
    } catch (err) {
      setSourceEdits((prev) => ({
        ...prev,
        [source.id]: {
          ...(prev[source.id] || {}),
          isDeleting: false,
          error: err.message || "Failed to delete source.",
        },
      }));
    }
  };

  const handleAgentToggle = (agent) => {
    const edit = agentEdits[agent.id];
    if (edit?.isSaving) return;
    updateAgentProfile(agent.id, { is_active: !agent.is_active });
  };

  const handleAgentEditChange = (agentId, field, value) => {
    setAgentEdits((prev) => ({
      ...prev,
      [agentId]: { ...(prev[agentId] || {}), [field]: value },
    }));
  };

  const handleAgentSave = (agent) => {
    const edit = agentEdits[agent.id] || {};
    const payload = {};
    if (edit.key && edit.key.trim() !== agent.key) payload.key = edit.key.trim();
    if (edit.name && edit.name.trim() !== agent.name) payload.name = edit.name.trim();
    if ((edit.description || "") !== (agent.description || "")) {
      payload.description = edit.description?.trim() || null;
    }
    if (edit.system_prompt && edit.system_prompt.trim() !== agent.system_prompt) {
      payload.system_prompt = edit.system_prompt.trim();
    }
    if (edit.user_prompt && edit.user_prompt.trim() !== agent.user_prompt) {
      payload.user_prompt = edit.user_prompt.trim();
    }
    if (typeof edit.is_active === "boolean" && edit.is_active !== agent.is_active) {
      payload.is_active = edit.is_active;
    }
    if (Object.keys(payload).length === 0) return;
    updateAgentProfile(agent.id, payload);
  };

  const handleAgentCreateChange = (field, value) => {
    setAgentCreate((prev) => ({ ...prev, [field]: value }));
  };

  const toggleAgentOpen = (agentId) => {
    setOpenAgentId((prev) => (prev === agentId ? null : agentId));
  };

  const renderAgentBody = (agent) => {
    if (!agent) return null;
    const edit = agentEdits[agent.id] || agent;
    const required = AGENT_TEMPLATE_FIELDS[agent.agent_type] || [];
    const missing = required.filter(
      (token) => !(edit.user_prompt || "").includes(token)
    );
    const hasChanges =
      (edit.key || "") !== (agent.key || "") ||
      (edit.name || "") !== (agent.name || "") ||
      (edit.description || "") !== (agent.description || "") ||
      (edit.system_prompt || "") !== (agent.system_prompt || "") ||
      (edit.user_prompt || "") !== (agent.user_prompt || "");

    return (
      <div className="agent-body">
        <div className="agent-header">
          <div>
            <div className="text-sm text-[color:var(--muted)]">Name</div>
            <input
              className="input"
              value={edit.name || ""}
              onChange={(event) =>
                handleAgentEditChange(agent.id, "name", event.target.value)
              }
            />
          </div>
          <div>
            <div className="text-sm text-[color:var(--muted)]">Key</div>
            <input
              className="input"
              value={edit.key || ""}
              onChange={(event) =>
                handleAgentEditChange(agent.id, "key", event.target.value)
              }
            />
          </div>
          <div className="agent-toggle">
            <div className="text-xs uppercase tracking-[0.28em] text-[color:var(--muted)]">
              Active
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={Boolean(agent.is_active)}
                onChange={() => handleAgentToggle(agent)}
              />
              <span className="switch-slider" />
            </label>
            <div className="text-xs text-[color:var(--muted)]">
              {agent.is_active ? "Enabled" : "Paused"}
            </div>
          </div>
        </div>

        <div className="agent-info">
          <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
            Type
          </div>
          <div className="mt-1">
            <span className="badge">{agent.agent_type}</span>
            {agent.is_system ? <span className="agent-flag">System</span> : null}
          </div>
        </div>

        <div>
          <div className="text-sm text-[color:var(--muted)]">Description</div>
          <input
            className="input"
            value={edit.description || ""}
            onChange={(event) =>
              handleAgentEditChange(agent.id, "description", event.target.value)
            }
          />
        </div>

        <div className="agent-prompts">
          <div>
            <div className="text-sm text-[color:var(--muted)]">System prompt</div>
            <textarea
              className="input agent-textarea"
              value={edit.system_prompt || ""}
              onChange={(event) =>
                handleAgentEditChange(agent.id, "system_prompt", event.target.value)
              }
            />
          </div>
          <div>
            <div className="text-sm text-[color:var(--muted)]">
              User prompt template
            </div>
            <textarea
              className="input agent-textarea"
              value={edit.user_prompt || ""}
              onChange={(event) =>
                handleAgentEditChange(agent.id, "user_prompt", event.target.value)
              }
            />
            <div className="mt-2 text-xs text-[color:var(--muted)]">
              Required fields: {required.join(", ") || "--"}
            </div>
            {missing.length > 0 ? (
              <div className="mt-1 text-xs text-[#c23b32]">
                Missing: {missing.join(", ")}
              </div>
            ) : null}
          </div>
        </div>

        <div className="agent-actions">
          <button
            className="btn btn-accent"
            onClick={() => handleAgentSave(agent)}
            disabled={!hasChanges || edit.isSaving}
          >
            {edit.isSaving ? "Saving..." : "Save changes"}
          </button>
          <button
            className="btn btn-danger"
            onClick={() => deleteAgentProfile(agent)}
            disabled={edit.isSaving}
          >
            Delete
          </button>
          {edit.error ? (
            <div className="text-xs text-[#c23b32]">{edit.error}</div>
          ) : null}
        </div>
      </div>
    );
  };

  return (
    <div className="page-shell px-6 py-10 md:px-10 lg:px-16">
      <div className="panel p-8 md:p-10 fade-in">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="kicker">Jour2 Operations</div>
            <h1 className="title-display text-4xl md:text-5xl lg:text-6xl">
              Intelligence Dashboard
            </h1>
            <p className="mt-3 max-w-xl text-base text-[color:var(--muted)]">
              Track live signals, triage what matters, and keep every channel in sync.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="status-pill">
              <span className={`status-dot status-${status}`} />
              <span>{statusLabel}</span>
            </div>
            <button className="btn btn-accent" onClick={fetchNews}>
              Refresh feed
            </button>
            <label className="btn flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(event) => setAutoRefresh(event.target.checked)}
              />
              Auto refresh 30s
            </label>
          </div>
        </div>

      </div>

      <div className="dashboard-shell mt-8">
        <aside className="panel nav-panel p-6">
          <div className="kicker">Sections</div>
          <div className="mt-4 flex flex-col gap-2">
            {NAV_ITEMS.map((item) => (
              <div key={item.key} className="nav-group">
                <button
                  className={`nav-link ${route === item.key ? "active" : ""}`}
                  onClick={() => navigate(item.path)}
                >
                  {item.label}
                </button>
                {item.key === "agents" ? (
                  <div className="nav-sub">
                    <button
                      className={`nav-sub-link ${
                        route === "agents" && !agentFocusKey ? "active" : ""
                      }`}
                      onClick={() => navigate("/dashboard/agents")}
                    >
                      <span>Overview</span>
                    </button>
                    {agentNavItems.length === 0 ? (
                      <div className="nav-sub-empty">No agents loaded.</div>
                    ) : (
                      agentNavItems.map((agent) => (
                        <button
                          key={`nav-agent-${agent.key}`}
                          className={`nav-sub-link ${
                            agentFocusKey === agent.key ? "active" : ""
                          }`}
                          onClick={() =>
                            navigate(`/dashboard/agents/${agent.key}`)
                          }
                        >
                          <span>{agent.label}</span>
                          <span
                            className={`nav-sub-dot ${
                              agent.isActive ? "on" : "off"
                            }`}
                          />
                        </button>
                      ))
                    )}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
          <div className="mt-8 text-sm text-[color:var(--muted)]">
            Last update: {lastUpdated ? lastUpdated.toLocaleTimeString() : "--"}
          </div>
        </aside>

        <main className="dashboard-main space-y-6">
          {route === "overview" && (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="metric">
                  <div className="kicker">Loaded entries</div>
                  <div className="text-3xl font-semibold">{items.length}</div>
                  <div className="mt-2 text-sm text-[color:var(--muted)]">
                    {error ? `Error: ${error}` : "Latest sync ok"}
                  </div>
                </div>
                <div className="metric">
                  <div className="kicker">WhatsApp</div>
                  <div className="text-3xl font-semibold text-[color:var(--accent)]">
                    {counts.whatsapp}
                  </div>
                  <div className="mt-2 text-sm text-[color:var(--muted)]">Active rooms</div>
                </div>
                <div className="metric">
                  <div className="kicker">Telegram</div>
                  <div className="text-3xl font-semibold text-[#2a6fb0]">
                    {counts.telegram}
                  </div>
                  <div className="mt-2 text-sm text-[color:var(--muted)]">Awaiting link</div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="section-title">Message stats</div>
                    <p className="mt-2 text-sm text-[color:var(--muted)]">
                      Stored messages across every active source.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="status-pill">
                      <span className={`status-dot status-${newsStatsStatus}`} />
                      <span>{newsStatsStatusLabel}</span>
                    </div>
                    <button className="btn" onClick={fetchNewsStats}>
                      Refresh counts
                    </button>
                  </div>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      Total stored
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {newsStats.total} messages
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      Latest message
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {formatTimestamp(newsStats.latest_timestamp)}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      WhatsApp stored
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.whatsapp}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      Telegram stored
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.telegram}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      RSS stored
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.rss}
                    </div>
                  </div>
                </div>
                {newsStatsError ? (
                  <div className="mt-3 text-sm text-[#c23b32]">
                    Stats error: {newsStatsError}
                  </div>
                ) : null}
              </div>

              <div className="panel p-6">
                <div className="section-title">Latest signals</div>
                <div className="mt-4 grid gap-3">
                  {latestItems.length === 0 ? (
                    <div className="text-sm text-[color:var(--muted)]">
                      No news yet. Messages will appear once the pipelines ingest data.
                    </div>
                  ) : (
                    latestItems.map((item) => (
                      <div key={item.id} className="overview-row">
                        <div>
                          <div className="text-sm font-semibold">{item.source_name}</div>
                          <div className="text-sm text-[color:var(--muted)]">
                            {item.content}
                          </div>
                        </div>
                        <div className="text-xs text-[color:var(--muted)]">
                          {item.author_name ? `By ${item.author_name}` : "--"}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>
          )}

          {route === "feed" && (
            <div className="space-y-6">
              <div className="panel p-6 md:p-8">
                <div className="section-title">Live feed</div>
                <p className="mt-2 text-sm text-[color:var(--muted)]">
                  Search and filter across every incoming message.
                </p>
                <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                  <input
                    className="input"
                    placeholder="Search content, source, or author"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                  <select
                    className="input"
                    value={platform}
                    onChange={(event) => setPlatform(event.target.value)}
                  >
                    {PLATFORM_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <select
                    className="input"
                    value={sourceFilter}
                    onChange={(event) => setSourceFilter(event.target.value)}
                  >
                    <option value="all">Source: all</option>
                    {sourceOptions.map((source) => (
                      <option key={source.id} value={String(source.id)}>
                        {source.name} ? {source.platform}
                      </option>
                    ))}
                  </select>
                  <select
                    className="input"
                    value={minScore}
                    onChange={(event) => setMinScore(event.target.value)}
                  >
                    <option value="any">Score: any</option>
                    <option value="8">Score: 8+</option>
                    <option value="7">Score: 7+</option>
                    <option value="6">Score: 6+</option>
                    <option value="5">Score: 5+</option>
                    <option value="4">Score: 4+</option>
                    <option value="3">Score: 3+</option>
                    <option value="2">Score: 2+</option>
                    <option value="1">Score: 1+</option>
                  </select>
                  <select
                    className="input"
                    value={limit}
                    onChange={(event) => setLimit(Number(event.target.value))}
                  >
                    <option value={50}>Limit: 50</option>
                    <option value={100}>Limit: 100</option>
                    <option value={200}>Limit: 200</option>
                  </select>
                </div>
                <div className="mt-3 text-sm text-[color:var(--muted)]">
                  Showing {filtered.length} of {items.length}. Status: {status}.
                  {error ? ` Error: ${error}` : ""}
                </div>
              </div>

              <div className="grid gap-4">
                {filtered.length === 0 ? (
                  <div className="panel p-10 text-center text-[color:var(--muted)]">
                    No news yet. Send a message from WhatsApp or Telegram to populate the feed.
                  </div>
                ) : (
                  filtered.map((item, index) => (
                    <div
                      key={item.id || `${item.source_message_id}-${index}`}
                      className="news-card"
                      style={{ animationDelay: `${Math.min(index * 0.06, 0.6)}s` }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="source-chip">{item.source_name || "Unknown"}</span>
                          <span
                            className={`badge ${platformBadgeClass(item.platform)}`}
                          >
                            {item.platform || "unknown"}
                          </span>
                        </div>
                        <div className="text-sm text-[color:var(--muted)]">
                          {formatTimestamp(item.timestamp)}
                        </div>
                      </div>
                      <div className="mt-4 text-base leading-relaxed">{item.content}</div>
                      <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-[color:var(--muted)]">
                        <span>Author: {item.author_name || "--"}</span>
                        <span>Score: {item.importance_score ?? "--"}</span>
                        <span>Category: {item.category || "--"}</span>
                        <span>Source ID: {item.source_identifier || "--"}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {route === "sources" && (
            <div className="space-y-6">
              <div className="panel p-6 md:p-8">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="section-title">Sources</div>
                    <p className="mt-2 text-sm text-[color:var(--muted)]">
                      Review group coverage, toggle ingestion, and maintain labeling.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="status-pill">
                      <span className={`status-dot status-${sourcesStatus}`} />
                      <span>{sourcesStatusLabel}</span>
                    </div>
                    <div className="status-pill">
                      <span className={`status-dot status-${newsStatsStatus}`} />
                      <span>{newsStatsStatusLabel}</span>
                    </div>
                    <button className="btn" onClick={fetchSources}>
                      Refresh sources
                    </button>
                    <button className="btn" onClick={fetchNewsStats}>
                      Refresh counts
                    </button>
                  </div>
                </div>

                <div className="mt-6">
                  <div className="tab-group">
                    {SOURCE_TABS.map((tab) => (
                      <button
                        key={`source-tab-${tab.value}`}
                        className={`tab-btn ${
                          sourcePlatformFilter === tab.value ? "is-active" : ""
                        }`}
                        onClick={() => setSourcePlatformFilter(tab.value)}
                      >
                        <span>{tab.label}</span>
                        <span className="tab-count">
                          {sourcePlatformCounts[tab.value] ?? 0}
                        </span>
                      </button>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    <input
                      className="input"
                      placeholder="Search by name, ID, or label"
                      value={sourceQuery}
                      onChange={(event) => setSourceQuery(event.target.value)}
                    />
                    <select
                      className="input"
                      value={sourceActiveFilter}
                      onChange={(event) => setSourceActiveFilter(event.target.value)}
                    >
                      {SOURCE_STATUS_OPTIONS.map((option) => (
                        <option key={`status-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <div className="source-summary">
                      <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                        Sources
                      </div>
                      <div className="mt-1 text-sm font-semibold">
                        {sourceStats.total} total · {sourceStats.active} active
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      Messages stored
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {newsStats.total} total
                    </div>
                    <div className="mt-1 text-xs text-[color:var(--muted)]">
                      Latest: {formatTimestamp(newsStats.latest_timestamp)}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      WhatsApp messages
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.whatsapp}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      Telegram messages
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.telegram}
                    </div>
                  </div>
                  <div className="source-summary">
                    <div className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                      RSS messages
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {platformMessageCounts.rss}
                    </div>
                  </div>
                </div>

                <div className="mt-3 text-sm text-[color:var(--muted)]">
                  Showing {filteredSources.length} of {sources.length}. Status: {sourcesStatus}.
                  {sourcesError ? ` Error: ${sourcesError}` : ""}
                  {newsStatsError ? ` Stats error: ${newsStatsError}` : ""}
                </div>
            </div>

            {sourcePlatformFilter === "rss" && (
              <div className="panel p-6">
                <div className="section-title">RSS feeds</div>
                <p className="mt-2 text-sm text-[color:var(--muted)]">
                  Add or remove RSS feed URLs to track external sources.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1.5fr_auto]">
                  <input
                    className="input"
                    placeholder="Feed name (optional)"
                    value={rssDraft.name}
                    onChange={(event) =>
                      setRssDraft((prev) => ({
                        ...prev,
                        name: event.target.value,
                        error: "",
                      }))
                    }
                  />
                  <input
                    className="input"
                    placeholder="https://example.com/rss"
                    value={rssDraft.url}
                    onChange={(event) =>
                      setRssDraft((prev) => ({
                        ...prev,
                        url: event.target.value,
                        error: "",
                      }))
                    }
                  />
                  <button
                    className="btn btn-accent"
                    onClick={handleRssCreate}
                    disabled={rssDraft.isSaving}
                  >
                    {rssDraft.isSaving ? "Adding..." : "Add RSS"}
                  </button>
                </div>
                {rssDraft.error ? (
                  <div className="mt-2 text-xs text-[#c23b32]">{rssDraft.error}</div>
                ) : null}
              </div>
            )}

            <div className="grid gap-4">
                {filteredSources.length === 0 ? (
                  <div className="panel p-10 text-center text-[color:var(--muted)]">
                    {sourcePlatformFilter === "rss"
                      ? "No RSS feeds yet. Add a feed URL above to start tracking."
                      : "No sources yet. New groups will appear as connectors ingest data."}
                  </div>
                ) : (
                  filteredSources.map((source) => {
                    const edit = sourceEdits[source.id] || {
                      labelsText: labelsToText(source.labels || []),
                      isSaving: false,
                      error: "",
                    };
                    const labelsInput = edit.labelsText ?? labelsToText(source.labels || []);
                    const labelsPreview = parseLabelText(labelsInput);
                    const hasLabelChanges =
                      labelsToText(labelsPreview) !== labelsToText(source.labels || []);
                    const messageCount =
                      newsStatsStatus === "ready"
                        ? sourceMessageCounts.get(String(source.id)) ?? 0
                        : "--";

                    return (
                      <div key={source.id} className="panel source-row p-6">
                        <div className="source-details">
                          <div className="flex flex-wrap items-center gap-2">
                            <div className="source-title">{source.name}</div>
                            <span className={`badge ${platformBadgeClass(source.platform)}`}>
                              {source.platform}
                            </span>
                          </div>
                          {source.platform === "rss" ? (
                            <a
                              className="source-sub source-link"
                              href={source.identifier}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {source.identifier || "Unknown URL"}
                            </a>
                          ) : (
                            <div className="source-sub">
                              {source.identifier || "Unknown ID"}
                            </div>
                          )}
                          <div className="source-meta">
                            <span>Schedule: {source.schedule_interval_minutes}m</span>
                            <span>Last run: {formatTimestamp(source.last_run_at)}</span>
                            <span>Next run: {formatTimestamp(source.next_run_at)}</span>
                            <span>Messages: {messageCount}</span>
                          </div>
                        </div>

                        <div className="source-toggle">
                          <div className="text-xs uppercase tracking-[0.28em] text-[color:var(--muted)]">
                            Active
                          </div>
                          <label className="switch">
                            <input
                              type="checkbox"
                              checked={Boolean(source.is_active)}
                              onChange={() => handleSourceToggle(source)}
                            />
                            <span className="switch-slider" />
                          </label>
                          <div className="text-xs text-[color:var(--muted)]">
                            {source.is_active ? "Ingesting" : "Paused"}
                          </div>
                        </div>

                        <div className="source-tags">
                          <div className="tag-list">
                            {labelsPreview.length === 0 ? (
                              <span className="text-xs text-[color:var(--muted)]">
                                No labels yet
                              </span>
                            ) : (
                              labelsPreview.map((label) => (
                                <span key={`${source.id}-${label}`} className="tag-chip">
                                  {label}
                                </span>
                              ))
                            )}
                          </div>
                          <div className="tag-editor">
                            <input
                              className="input tag-input"
                              value={labelsInput}
                              onChange={(event) =>
                                handleSourceLabelChange(source.id, event.target.value)
                              }
                              placeholder="Add labels, comma separated"
                            />
                            <button
                              className="btn btn-accent"
                              onClick={() => handleSourceSave(source)}
                              disabled={!hasLabelChanges || edit.isSaving}
                            >
                              {edit.isSaving ? "Saving..." : "Save labels"}
                            </button>
                          </div>
                          {source.platform === "rss" ? (
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <button
                                className="btn btn-danger"
                                onClick={() => handleRssDelete(source)}
                                disabled={Boolean(edit.isDeleting)}
                              >
                                {edit.isDeleting ? "Deleting..." : "Delete feed"}
                              </button>
                              <span className="text-xs text-[color:var(--muted)]">
                                Removing a feed stops RSS ingestion immediately.
                              </span>
                            </div>
                          ) : null}
                          {edit.error ? (
                            <div className="text-xs text-[#c23b32]">{edit.error}</div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {route === "settings" && (
            <div className="space-y-6">
              <div className="panel p-6 md:p-8">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="section-title">Settings</div>
                    <p className="mt-2 text-sm text-[color:var(--muted)]">
                      Centralize API keys, AI models, retention, and connector
                      credentials.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="status-pill">
                      <span className={`status-dot status-${settingsStatus}`} />
                      <span>{settingsStatusLabel}</span>
                    </div>
                    <button
                      className="btn"
                      onClick={fetchSettings}
                      disabled={settingsStatus === "loading"}
                    >
                      {settingsStatus === "loading" ? "Refreshing..." : "Refresh"}
                    </button>
                  </div>
                </div>
                {settingsError ? (
                  <div className="mt-3 text-sm text-[#c23b32]">{settingsError}</div>
                ) : null}
              </div>

              <div className="panel p-6">
                <div className="section-title">API keys</div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      OpenRouter API key
                    </div>
                    <input
                      className="input mt-2"
                      type="password"
                      value={settingsDraft.keys.openrouter_api_key}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "keys",
                          "openrouter_api_key",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Gemini API key
                    </div>
                    <input
                      className="input mt-2"
                      type="password"
                      value={settingsDraft.keys.gemini_api_key}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "keys",
                          "gemini_api_key",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("keys")}
                    disabled={settingsSaving.keys}
                  >
                    {settingsSaving.keys ? "Saving..." : "Save keys"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Stored in the system config table.
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">AI configuration</div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Gemini API version
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.ai.gemini_api_version}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "gemini_api_version",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Agent LLM provider
                    </div>
                    <select
                      className="input mt-2"
                      value={settingsDraft.ai.agent_llm_provider}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "agent_llm_provider",
                          event.target.value,
                        )
                      }
                    >
                      {LLM_PROVIDER_OPTIONS.map((option) => (
                        <option key={`llm-provider-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  {settingsDraft.ai.agent_llm_provider === "openrouter" ? (
                    <div className="md:col-span-2">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                        Summary model (OpenRouter)
                      </div>
                      <input
                        className="input mt-2"
                        value={settingsDraft.ai.summary_model}
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "summary_model",
                            event.target.value,
                          )
                        }
                      />
                      <select
                        className="input mt-2"
                        value={
                          openrouterVisibleModels.some(
                            (model) => model.id === settingsDraft.ai.summary_model,
                          )
                            ? settingsDraft.ai.summary_model
                            : ""
                        }
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "summary_model",
                            event.target.value,
                          )
                        }
                      >
                        <option value="">Pick from OpenRouter models</option>
                        <option value="openrouter/auto">
                          openrouter/auto (auto routing)
                        </option>
                        {openrouterVisibleModels.map((model) => (
                          <option key={`summary-${model.id}`} value={model.id}>
                            {model.name || model.id}
                            {model.is_free ? " (free)" : ""}
                          </option>
                        ))}
                      </select>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <button
                          className="btn"
                          onClick={() => fetchOpenRouterModels()}
                          disabled={openrouterStatus === "loading"}
                        >
                          {openrouterStatus === "loading"
                            ? "Loading models..."
                            : "Refresh models"}
                        </button>
                        <label className="flex items-center gap-2 text-xs text-[color:var(--muted)]">
                          <input
                            type="checkbox"
                            checked={openrouterFreeOnly}
                            onChange={(event) =>
                              setOpenrouterFreeOnly(event.target.checked)
                            }
                          />
                          Free models only ({openrouterFreeCount})
                        </label>
                        <div className="text-xs text-[color:var(--muted)]">
                          {openrouterVisibleModels.length} shown /{" "}
                          {openrouterModels.length} total
                        </div>
                      </div>
                      {openrouterError ? (
                        <div className="mt-2 text-xs text-[#c23b32]">
                          {openrouterError}
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                        Summary model
                      </div>
                      <input
                        className="input mt-2"
                        value={settingsDraft.ai.summary_model}
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "summary_model",
                            event.target.value,
                          )
                        }
                      />
                    </div>
                  )}
                  {settingsDraft.ai.agent_llm_provider === "openrouter" ? (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                        Agent model (OpenRouter)
                      </div>
                      <input
                        className="input mt-2"
                        value={settingsDraft.ai.agent_llm_model}
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "agent_llm_model",
                            event.target.value,
                          )
                        }
                      />
                      <select
                        className="input mt-2"
                        value={
                          openrouterVisibleModels.some(
                            (model) => model.id === settingsDraft.ai.agent_llm_model,
                          )
                            ? settingsDraft.ai.agent_llm_model
                            : ""
                        }
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "agent_llm_model",
                            event.target.value,
                          )
                        }
                      >
                        <option value="">Pick from OpenRouter models</option>
                        <option value="openrouter/auto">
                          openrouter/auto (auto routing)
                        </option>
                        {openrouterVisibleModels.map((model) => (
                          <option key={`agent-${model.id}`} value={model.id}>
                            {model.name || model.id}
                            {model.is_free ? " (free)" : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                        Agent model
                      </div>
                      <input
                        className="input mt-2"
                        value={settingsDraft.ai.agent_llm_model}
                        onChange={(event) =>
                          updateSettingsDraft(
                            "ai",
                            "agent_llm_model",
                            event.target.value,
                          )
                        }
                      />
                    </div>
                  )}
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Summary timezone
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.ai.summary_timezone}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "summary_timezone",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Summary interval (seconds)
                    </div>
                    <input
                      className="input mt-2"
                      type="number"
                      min="60"
                      max="86400"
                      value={settingsDraft.ai.summary_run_interval_seconds}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "summary_run_interval_seconds",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Summary max messages
                    </div>
                    <input
                      className="input mt-2"
                      type="number"
                      min="1"
                      max="5000"
                      value={settingsDraft.ai.summary_max_messages}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "summary_max_messages",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Summary max chars
                    </div>
                    <input
                      className="input mt-2"
                      type="number"
                      min="1000"
                      max="500000"
                      value={settingsDraft.ai.summary_max_chars}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "ai",
                          "summary_max_chars",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("ai")}
                    disabled={settingsSaving.ai}
                  >
                    {settingsSaving.ai ? "Saving..." : "Save AI settings"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Changes apply on the next summary run.
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">Retention policy</div>
                <p className="mt-2 text-sm text-[color:var(--muted)]">
                  Keep raw messages for a set number of days after daily summaries.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-[160px_140px_1fr] items-end">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Days to keep
                    </div>
                    <input
                      className="input mt-2"
                      type="number"
                      min={settingsData.retention.min_days}
                      max={settingsData.retention.max_days}
                      value={settingsDraft.retention.days}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "retention",
                          "days",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("retention")}
                    disabled={settingsSaving.retention}
                  >
                    {settingsSaving.retention ? "Saving..." : "Save"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Range: {settingsData.retention.min_days}-
                    {settingsData.retention.max_days} days · Source:{" "}
                    {settingsData.retention.source}
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">Chat retention</div>
                <p className="mt-2 text-sm text-[color:var(--muted)]">
                  Delete user chat messages after a chosen number of days (max 30).
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-[160px_140px_1fr] items-end">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Days to keep
                    </div>
                    <input
                      className="input mt-2"
                      type="number"
                      min={settingsData.chat_retention.min_days}
                      max={settingsData.chat_retention.max_days}
                      value={settingsDraft.chat_retention.days}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "chat_retention",
                          "days",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("chat_retention")}
                    disabled={settingsSaving.chat_retention}
                  >
                    {settingsSaving.chat_retention ? "Saving..." : "Save"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Range: {settingsData.chat_retention.min_days}-
                    {settingsData.chat_retention.max_days} days · Source:{" "}
                    {settingsData.chat_retention.source}
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">Telegram connection</div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(settingsDraft.telegram.enabled)}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "enabled",
                          event.target.checked,
                        )
                      }
                    />
                    Enabled
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(settingsDraft.telegram.include_private)}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "include_private",
                          event.target.checked,
                        )
                      }
                    />
                    Include private chats
                  </label>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      API ID
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.telegram.api_id}
                      onChange={(event) =>
                        updateSettingsDraft("telegram", "api_id", event.target.value)
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      API hash
                    </div>
                    <input
                      className="input mt-2"
                      type="password"
                      value={settingsDraft.telegram.api_hash}
                      onChange={(event) =>
                        updateSettingsDraft("telegram", "api_hash", event.target.value)
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Phone number
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.telegram.phone_number}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "phone_number",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Session name
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.telegram.session_name}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "session_name",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Log level
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.telegram.log_level}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "log_level",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(settingsDraft.telegram.log_groups)}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram",
                          "log_groups",
                          event.target.checked,
                        )
                      }
                    />
                    Log groups on connect
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("telegram")}
                    disabled={settingsSaving.telegram}
                  >
                    {settingsSaving.telegram ? "Saving..." : "Save Telegram"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Restart the Telegram service after changing credentials.
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">Telegram bot delivery</div>
                <p className="mt-2 text-sm text-[color:var(--muted)]">
                  Use a bot token to deliver summary notifications to subscribers.
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(settingsDraft.telegram_bot.enabled)}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram_bot",
                          "enabled",
                          event.target.checked,
                        )
                      }
                    />
                    Enabled
                  </label>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Bot token
                    </div>
                    <input
                      className="input mt-2"
                      type="password"
                      value={settingsDraft.telegram_bot.token}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram_bot",
                          "token",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Bot username
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.telegram_bot.username}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "telegram_bot",
                          "username",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("telegram_bot")}
                    disabled={settingsSaving.telegram_bot}
                  >
                    {settingsSaving.telegram_bot ? "Saving..." : "Save bot"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Users must link the bot with /start from the mobile app.
                  </div>
                </div>
              </div>

              <div className="panel p-6">
                <div className="section-title">WhatsApp connection</div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(settingsDraft.whatsapp.enabled)}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "whatsapp",
                          "enabled",
                          event.target.checked,
                        )
                      }
                    />
                    Enabled
                  </label>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Phone number (pairing)
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.whatsapp.phone_number}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "whatsapp",
                          "phone_number",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                      Log level
                    </div>
                    <input
                      className="input mt-2"
                      value={settingsDraft.whatsapp.log_level}
                      onChange={(event) =>
                        updateSettingsDraft(
                          "whatsapp",
                          "log_level",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-accent"
                    onClick={() => saveSettingsSection("whatsapp")}
                    disabled={settingsSaving.whatsapp}
                  >
                    {settingsSaving.whatsapp ? "Saving..." : "Save WhatsApp"}
                  </button>
                  <div className="text-sm text-[color:var(--muted)]">
                    Pairing code uses the phone number above when provided.
                  </div>
                </div>
              </div>
            </div>
          )}

          {route === "agents" && (
            <div className="space-y-6">
              {agentFocusKey ? (
                <div className="space-y-6">
                  <div className="panel p-6 md:p-8">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <div className="section-title">
                          {focusedAgent?.name || focusedAgent?.key || "Agent"}
                        </div>
                        <p className="mt-2 text-sm text-[color:var(--muted)]">
                          {focusedAgent?.description ||
                            "Manage agent profile and runtime settings."}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3">
                        {focusedAgent ? (
                          <span className="badge">{focusedAgent.agent_type}</span>
                        ) : null}
                        {focusedAgent ? (
                          <span
                            className={`agent-state ${
                              focusedAgent.is_active ? "on" : "off"
                            }`}
                          >
                            {focusedAgent.is_active ? "Enabled" : "Paused"}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  {!focusedAgent ? (
                    <div className="panel p-6 md:p-8 text-sm text-[color:var(--muted)]">
                      This agent is not available. Refresh agents from the overview.
                    </div>
                  ) : (
                    <>
                      <div className="panel p-6 md:p-8">
                        <div className="section-title">
                          {agentFocusKey === "search" ? "Run search" : "Run agent"}
                        </div>
                        <p className="mt-2 text-sm text-[color:var(--muted)]">
                          {agentFocusKey === "search"
                            ? "Send a query to the search agent."
                            : "Run the selected agent with custom context."}
                        </p>
                        <div className="mt-6 grid gap-4 md:grid-cols-2">
                          <input
                            className="input md:col-span-2"
                            placeholder={
                              agentFocusKey === "search"
                                ? "Search query"
                                : "Task to run"
                            }
                            value={agentTask}
                            onChange={(event) => setAgentTask(event.target.value)}
                          />
                          {agentFocusKey === "search" ? null : (
                            <>
                              <div>
                                <input
                                  className="input"
                                  type="number"
                                  min="1"
                                  max="168"
                                  value={agentWindowHours}
                                  onChange={(event) =>
                                    setAgentWindowHours(Number(event.target.value))
                                  }
                                  placeholder="Window hours"
                                />
                                <div className="mt-2 text-xs text-[color:var(--muted)]">
                                  Lookback window (hours) used for recent message retrieval.
                                </div>
                              </div>
                              <div>
                                <input
                                  className="input"
                                  type="number"
                                  min="1"
                                  max="200"
                                  value={agentMaxItems}
                                  onChange={(event) =>
                                    setAgentMaxItems(Number(event.target.value))
                                  }
                                  placeholder="Max items"
                                />
                                <div className="mt-2 text-xs text-[color:var(--muted)]">
                                  Maximum number of messages sent to the agent (1-200).
                                </div>
                              </div>
                              <textarea
                                className="input agent-textarea md:col-span-2"
                                placeholder="Optional context to send with the task"
                                value={agentContext}
                                onChange={(event) =>
                                  setAgentContext(event.target.value)
                                }
                              />
                            </>
                          )}
                        </div>
                        <div className="mt-4 flex flex-wrap items-center gap-3">
                          <button
                            className="btn btn-accent"
                            onClick={() => runAgent(agentFocusKey)}
                            disabled={!agentTask.trim() || agentStatus === "loading"}
                          >
                            {agentStatus === "loading"
                              ? "Running..."
                              : agentFocusKey === "search"
                              ? "Run search"
                              : "Run agent"}
                          </button>
                          <div className="text-sm text-[color:var(--muted)]">
                            Last run:{" "}
                            {agentLastRun ? agentLastRun.toLocaleTimeString() : "--"}
                          </div>
                        </div>
                        {agentError ? (
                          <div className="mt-3 text-sm text-[#c23b32]">
                            {agentError}
                          </div>
                        ) : null}
                      </div>

                      {agentFocusKey === "search" ? (
                        <div className="panel p-6 md:p-8">
                          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                            <div>
                              <div className="section-title">Search agent setup</div>
                              <p className="mt-2 text-sm text-[color:var(--muted)]">
                                Configure SearXNG query parameters and defaults.
                              </p>
                            </div>
                            <div className="tab-group">
                              <button
                                className={`tab-btn ${
                                  agentFocusTab === "engine" ? "is-active" : ""
                                }`}
                                onClick={() => setAgentFocusTab("engine")}
                              >
                                Search engine
                              </button>
                              <button
                                className={`tab-btn ${
                                  agentFocusTab === "profile" ? "is-active" : ""
                                }`}
                                onClick={() => setAgentFocusTab("profile")}
                              >
                                Agent profile
                              </button>
                            </div>
                          </div>
                          <div className="mt-6">
                            {agentFocusTab === "profile" ? (
                              renderAgentBody(focusedAgent)
                            ) : (
                              <div className="space-y-4">
                                <div className="grid gap-4 md:grid-cols-2">
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Provider
                                    </div>
                                    <select
                                      className="input mt-2"
                                      value={settingsDraft.search.provider}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "provider",
                                          event.target.value
                                        )
                                      }
                                    >
                                      <option value="searxng">SearXNG</option>
                                      <option value="disabled">Disabled</option>
                                    </select>
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Base URL
                                    </div>
                                    <input
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_base_url}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_base_url",
                                          event.target.value
                                        )
                                      }
                                    />
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Timeout (seconds)
                                    </div>
                                    <input
                                      className="input mt-2"
                                      type="number"
                                      min="3"
                                      max="60"
                                      value={settingsDraft.search.searxng_timeout_seconds}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_timeout_seconds",
                                          event.target.value
                                        )
                                      }
                                    />
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Max results
                                    </div>
                                    <input
                                      className="input mt-2"
                                      type="number"
                                      min="1"
                                      max="50"
                                      value={settingsDraft.search.searxng_max_results}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_max_results",
                                          event.target.value
                                        )
                                      }
                                    />
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Language
                                    </div>
                                    <input
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_language}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_language",
                                          event.target.value
                                        )
                                      }
                                      placeholder="all / en / ar"
                                    />
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Safe search
                                    </div>
                                    <select
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_safe_search}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_safe_search",
                                          event.target.value
                                        )
                                      }
                                    >
                                      <option value="0">Off (0)</option>
                                      <option value="1">Moderate (1)</option>
                                      <option value="2">Strict (2)</option>
                                    </select>
                                  </div>
                                  <div>
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Time range
                                    </div>
                                    <select
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_time_range}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_time_range",
                                          event.target.value
                                        )
                                      }
                                    >
                                      <option value="">Any time</option>
                                      <option value="day">Last day</option>
                                      <option value="week">Last week</option>
                                      <option value="month">Last month</option>
                                      <option value="year">Last year</option>
                                    </select>
                                  </div>
                                  <div className="md:col-span-2">
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Categories (comma separated)
                                    </div>
                                    <input
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_categories}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_categories",
                                          event.target.value
                                        )
                                      }
                                      placeholder="news, science"
                                    />
                                  </div>
                                  <div className="md:col-span-2">
                                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted)]">
                                      Engines (comma separated)
                                    </div>
                                    <input
                                      className="input mt-2"
                                      value={settingsDraft.search.searxng_engines}
                                      onChange={(event) =>
                                        updateSettingsDraft(
                                          "search",
                                          "searxng_engines",
                                          event.target.value
                                        )
                                      }
                                      placeholder="google, bing"
                                    />
                                  </div>
                                </div>
                                <div className="mt-4 flex flex-wrap items-center gap-3">
                                  <button
                                    className="btn btn-accent"
                                    onClick={() => saveSettingsSection("search")}
                                    disabled={settingsSaving.search}
                                  >
                                    {settingsSaving.search
                                      ? "Saving..."
                                      : "Save search settings"}
                                  </button>
                                  <div className="text-sm text-[color:var(--muted)]">
                                    Base URL points to the SearXNG container.
                                  </div>
                                </div>
                                {settingsError ? (
                                  <div className="text-sm text-[#c23b32]">
                                    {settingsError}
                                  </div>
                                ) : null}
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="panel p-6 md:p-8">
                          <div className="section-title">Agent profile</div>
                          <div className="mt-4">
                            {renderAgentBody(focusedAgent)}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ) : null}
              {!agentFocusKey ? (
                <div className="grid gap-4 lg:grid-cols-2">
                <div className="panel p-6 md:p-8">
                  <div className="section-title">Run an agent</div>
                  <p className="mt-2 text-sm text-[color:var(--muted)]">
                    Pick a route or leave it on auto. Results return in Arabic.
                  </p>
                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <input
                      className="input"
                      placeholder="Task to run"
                      value={agentTask}
                      onChange={(event) => setAgentTask(event.target.value)}
                    />
                    <select
                      className="input"
                      value={agentRoute}
                      onChange={(event) => setAgentRoute(event.target.value)}
                    >
                      {agentRouteOptions.map((option) => (
                        <option key={`agent-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <div>
                      <input
                        className="input"
                        type="number"
                        min="1"
                        max="168"
                        value={agentWindowHours}
                        onChange={(event) =>
                          setAgentWindowHours(Number(event.target.value))
                        }
                        placeholder="Window hours"
                      />
                      <div className="mt-2 text-xs text-[color:var(--muted)]">
                        Lookback window (hours) used for recent message retrieval.
                      </div>
                    </div>
                    <div>
                      <input
                        className="input"
                        type="number"
                        min="1"
                        max="200"
                        value={agentMaxItems}
                        onChange={(event) =>
                          setAgentMaxItems(Number(event.target.value))
                        }
                        placeholder="Max items"
                      />
                      <div className="mt-2 text-xs text-[color:var(--muted)]">
                        Maximum number of messages sent to the agent (1-200).
                      </div>
                    </div>
                    <textarea
                      className="input agent-textarea md:col-span-2"
                      placeholder="Optional context to send with the task"
                      value={agentContext}
                      onChange={(event) => setAgentContext(event.target.value)}
                    />
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      className="btn btn-accent"
                      onClick={runAgent}
                      disabled={!agentTask.trim() || agentStatus === "loading"}
                    >
                      {agentStatus === "loading" ? "Running..." : "Run agent"}
                    </button>
                    <div className="text-sm text-[color:var(--muted)]">
                      Last run:{" "}
                      {agentLastRun ? agentLastRun.toLocaleTimeString() : "--"}
                    </div>
                  </div>
                  {agentError ? (
                    <div className="mt-3 text-sm text-[#c23b32]">{agentError}</div>
                  ) : null}
                </div>

                <div className="panel p-6 md:p-8">
                  <div className="section-title">Create agent</div>
                  <p className="mt-2 text-sm text-[color:var(--muted)]">
                    Custom agents use the general workflow and can be routed manually.
                  </p>
                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <input
                      className="input"
                      placeholder="Key (lowercase, no spaces)"
                      value={agentCreate.key}
                      onChange={(event) =>
                        handleAgentCreateChange("key", event.target.value)
                      }
                    />
                    <input
                      className="input"
                      placeholder="Name"
                      value={agentCreate.name}
                      onChange={(event) =>
                        handleAgentCreateChange("name", event.target.value)
                      }
                    />
                    <input
                      className="input"
                      placeholder="Description"
                      value={agentCreate.description}
                      onChange={(event) =>
                        handleAgentCreateChange("description", event.target.value)
                      }
                    />
                    <select
                      className="input"
                      value={agentCreate.agent_type}
                      onChange={(event) =>
                        handleAgentCreateChange("agent_type", event.target.value)
                      }
                    >
                      {AGENT_TYPE_OPTIONS.map((option) => (
                        <option key={`agent-type-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <textarea
                      className="input agent-textarea md:col-span-2"
                      placeholder="System prompt"
                      value={agentCreate.system_prompt}
                      onChange={(event) =>
                        handleAgentCreateChange("system_prompt", event.target.value)
                      }
                    />
                    <textarea
                      className="input agent-textarea md:col-span-2"
                      placeholder="User prompt template"
                      value={agentCreate.user_prompt}
                      onChange={(event) =>
                        handleAgentCreateChange("user_prompt", event.target.value)
                      }
                    />
                  </div>
                  <div className="mt-3 text-xs text-[color:var(--muted)]">
                    Required fields:{" "}
                    {(AGENT_TEMPLATE_FIELDS[agentCreate.agent_type] || []).join(", ")}
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      className="btn btn-accent"
                      onClick={createAgentProfile}
                      disabled={
                        agentCreateStatus === "loading" ||
                        !agentCreate.key.trim() ||
                        !agentCreate.name.trim() ||
                        !agentCreate.system_prompt.trim() ||
                        !agentCreate.user_prompt.trim()
                      }
                    >
                      {agentCreateStatus === "loading" ? "Creating..." : "Create agent"}
                    </button>
                    {agentCreateError ? (
                      <div className="text-xs text-[#c23b32]">{agentCreateError}</div>
                    ) : null}
                  </div>
                </div>
                </div>
              ) : null}

              {!agentFocusKey ? (
                <div className="panel p-6 md:p-8">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <div className="section-title">Agents control</div>
                      <p className="mt-2 text-sm text-[color:var(--muted)]">
                        Run multi-agent workflows and inspect results from the newsroom stack.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="status-pill">
                        <span className={`status-dot status-${agentHealth}`} />
                        <span>{agentHealthLabel}</span>
                      </div>
                      <button
                        className="btn"
                        onClick={checkAgentHealth}
                        disabled={agentHealth === "loading"}
                      >
                        {agentHealth === "loading" ? "Checking..." : "Check status"}
                      </button>
                    </div>
                  </div>
                  {agentHealthError ? (
                    <div className="mt-3 text-sm text-[#c23b32]">{agentHealthError}</div>
                  ) : null}
                  {agentHealthData ? (
                    <div className="mt-2 text-xs text-[color:var(--muted)]">
                      Service status: {agentHealthData.status || "unknown"}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {!agentFocusKey ? (
                <div className="panel p-6 md:p-8">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <div className="section-title">Agents library</div>
                      <p className="mt-2 text-sm text-[color:var(--muted)]">
                        Edit prompts, enable/disable agents, and manage routes and templates.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="status-pill">
                        <span className={`status-dot status-${agentsStatus}`} />
                        <span>{agentsStatusLabel}</span>
                      </div>
                      <button className="btn" onClick={fetchAgents}>
                        Refresh agents
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[color:var(--muted)]">
                    Showing {agents.length}. Status: {agentsStatus}.
                    {agentsError ? ` Error: ${agentsError}` : ""}
                  </div>
                </div>
              ) : null}

              {!agentFocusKey ? (
                <div className="grid gap-4">
                  {agents.length === 0 ? (
                    <div className="panel p-10 text-center text-[color:var(--muted)]">
                      No agents loaded yet. Use refresh to sync definitions.
                    </div>
                  ) : (
                    agents.map((agent) => {
                      const edit = agentEdits[agent.id] || agent;
                      const isOpen = openAgentId === agent.id;
                      const summaryTitle = (
                        edit.name || agent.name || agent.key || "Agent"
                      )
                        .toString()
                        .trim();
                      const summaryKey = (edit.key || agent.key || "")
                        .toString()
                        .trim();
                      const summaryDescription = (
                        edit.description || agent.description || ""
                      )
                        .toString()
                        .trim();
                      const summaryMeta = [summaryKey, agent.agent_type]
                        .filter(Boolean)
                        .join(" - ");

                      return (
                        <div key={agent.id} className="panel agent-row p-6">
                          <button
                            type="button"
                            className="agent-summary"
                            onClick={() => toggleAgentOpen(agent.id)}
                            aria-expanded={isOpen}
                          >
                            <div className="agent-summary-main">
                              <div className="agent-summary-title">
                                {summaryTitle || "Agent"}
                              </div>
                              <div className="agent-summary-sub">
                                {summaryMeta || "--"}
                              </div>
                              {summaryDescription ? (
                                <div className="agent-summary-desc">
                                  {summaryDescription}
                                </div>
                              ) : null}
                            </div>
                            <div className="agent-summary-meta">
                              <span className="badge">{agent.agent_type}</span>
                              {agent.is_system ? (
                                <span className="agent-flag">System</span>
                              ) : null}
                              <span
                                className={`agent-state ${
                                  agent.is_active ? "on" : "off"
                                }`}
                              >
                                {agent.is_active ? "Enabled" : "Paused"}
                              </span>
                              <span
                                className={`agent-chevron ${isOpen ? "open" : ""}`}
                              >
                                v
                              </span>
                            </div>
                          </button>

                          {isOpen ? renderAgentBody(agent) : null}
                        </div>
                      );
                    })
                  )}
                </div>
              ) : null}

              <div className="panel p-6 md:p-8">
                <div className="section-title">Latest output</div>
                <div className="mt-2 text-sm text-[color:var(--muted)]">
                  Route: {agentResultRoute || "--"} · Status: {agentStatusLabel}
                </div>
                <pre className="agent-output">
                  {agentOutput || "No output yet. Run an agent to see results."}
                </pre>
                {agentMeta ? (
                  <pre className="agent-meta">{JSON.stringify(agentMeta, null, 2)}</pre>
                ) : null}
              </div>
            </div>
          )}
        </main>
      </div>

      <div className="mt-10 text-center text-sm text-[color:var(--muted)]">
        Jour2 pipeline running. Build the next modules on top of this dashboard shell.
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
