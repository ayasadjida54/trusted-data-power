import axios from "axios";

// Configurable so the built frontend can point at any backend without a
// rebuild — set VITE_API_BASE_URL in the environment; defaults to the
// local FastAPI dev server.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

/**
 * Set (or clear, with `null`) the bearer token attached to every
 * request made with this client. Called by AuthContext whenever the
 * token changes, so callers of uploadDataset/listDatasets/etc. never
 * need to think about auth headers themselves.
 */
export function setAuthToken(token) {
  if (token) {
    client.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete client.defaults.headers.common["Authorization"];
  }
}

/**
 * Upload a file for analysis. Returns the full AnalysisRunDetail.
 * If `datasetId` is given, the new run is appended to that existing
 * dataset slot instead of creating a new one (Phase 5); otherwise
 * `datasetName` is matched against existing slots by name, falling
 * back to creating a new slot if nothing matches.
 * Throws with a readable message on failure (400s/404s carry a
 * `detail` field from the backend; anything else falls back to a
 * generic one).
 */
export async function uploadDataset(file, datasetName, datasetId) {
  const formData = new FormData();
  formData.append("file", file);

  const params = {};
  if (datasetId) params.dataset_id = datasetId;
  else if (datasetName) params.dataset_name = datasetName;

  try {
    const response = await client.post("/api/datasets/upload", formData, {
      params,
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  } catch (error) {
    const detail = error?.response?.data?.detail;
    throw new Error(detail || "Something went wrong while analyzing this file.");
  }
}

export async function listDatasets() {
  const response = await client.get("/api/datasets");
  return response.data;
}

export async function getLatestRun(datasetId) {
  const response = await client.get(`/api/datasets/${datasetId}/latest`);
  return response.data;
}

export async function listRuns(datasetId) {
  const response = await client.get(`/api/datasets/${datasetId}/runs`);
  return response.data;
}

export async function compareRuns(datasetId, runA, runB) {
  const response = await client.get(`/api/datasets/${datasetId}/compare`, {
    params: { run_a: runA, run_b: runB },
  });
  return response.data;
}

export async function getRun(runId) {
  const response = await client.get(`/api/runs/${runId}`);
  return response.data;
}

export async function getMonitoringSettings(datasetId) {
  const response = await client.get(`/api/datasets/${datasetId}/monitoring`);
  return response.data;
}

export async function updateMonitoringSettings(datasetId, enabled, thresholdPoints) {
  const response = await client.patch(`/api/datasets/${datasetId}/monitoring`, {
    monitoring_enabled: enabled,
    alert_threshold_points: thresholdPoints,
  });
  return response.data;
}

export async function listAlerts(unreadOnly) {
  const response = await client.get("/api/alerts", {
    params: unreadOnly ? { unread_only: true } : undefined,
  });
  return response.data;
}

export async function markAlertRead(alertId) {
  const response = await client.post(`/api/alerts/${alertId}/read`);
  return response.data;
}

/**
 * Link a dataset to a Google Sheet and run an immediate sync. Throws
 * with a readable message on failure (bad URL, private sheet, etc. -
 * the backend's `detail` field is written to be shown directly).
 */
export async function connectSheet(sheetUrl, datasetName, datasetId, syncIntervalMinutes) {
  try {
    const response = await client.post("/api/datasets/connect-sheet", {
      sheet_url: sheetUrl,
      dataset_name: datasetId ? undefined : datasetName || undefined,
      dataset_id: datasetId || undefined,
      sync_interval_minutes: syncIntervalMinutes || undefined,
    });
    return response.data;
  } catch (error) {
    const detail = error?.response?.data?.detail;
    throw new Error(detail || "Something went wrong while connecting this sheet.");
  }
}

export async function getDatasource(datasetId) {
  const response = await client.get(`/api/datasets/${datasetId}/datasource`);
  return response.data; // null if not linked
}

export async function syncDatasetNow(datasetId) {
  try {
    const response = await client.post(`/api/datasets/${datasetId}/sync-now`);
    return response.data;
  } catch (error) {
    const detail = error?.response?.data?.detail;
    throw new Error(detail || "The sync failed.");
  }
}

export async function unlinkDatasource(datasetId) {
  await client.delete(`/api/datasets/${datasetId}/datasource`);
}

/**
 * Run the real DataScore cleaning pipeline on a run's source data.
 * Returns the new (cleaned) AnalysisRunDetail. Throws with a readable
 * message on failure (e.g. no stored source data for this run).
 */
export async function cleanRun(runId) {
  try {
    const response = await client.post(`/api/runs/${runId}/clean`);
    return response.data;
  } catch (error) {
    const detail = error?.response?.data?.detail;
    throw new Error(detail || "The cleaning pipeline failed.");
  }
}

/**
 * Downloads a run's PDF or CSV report as a blob and triggers a
 * browser download. Fetched via axios (not a plain <a href>) so the
 * auth header is attached - a bare link can't carry it.
 */
async function downloadBlob(path, filename) {
  const response = await client.get(path, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function downloadPdfReport(runId, filename) {
  return downloadBlob(`/api/runs/${runId}/report.pdf`, filename || `report-${runId}.pdf`);
}

export function downloadCsvReport(runId, filename) {
  return downloadBlob(`/api/runs/${runId}/report.csv`, filename || `findings-${runId}.csv`);
}

export async function createShareLink(runId) {
  const response = await client.post(`/api/runs/${runId}/share`);
  return response.data; // { share_token, share_path }
}

export async function revokeShareLink(runId) {
  await client.delete(`/api/runs/${runId}/share`);
}

/**
 * Public report fetch - deliberately uses a plain axios call with NO
 * auth header (the public endpoints require none), via a fresh client
 * instance so it's unaffected by whatever token is set on the shared
 * `client` above.
 */
const publicClient = axios.create({ baseURL: API_BASE_URL });

export async function getPublicReport(token) {
  const response = await publicClient.get(`/api/public/reports/${token}`);
  return response.data;
}

export function publicPdfReportUrl(token) {
  return `${API_BASE_URL}/api/public/reports/${token}/report.pdf`;
}

export default client;
