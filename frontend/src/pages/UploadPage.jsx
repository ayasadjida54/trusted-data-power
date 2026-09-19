import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadDropzone from "../components/UploadDropzone";
import { uploadDataset, connectSheet, listDatasets } from "../api/client";

const MODES = { FILE: "file", SHEET: "sheet" };

export default function UploadPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState(MODES.FILE);

  const [file, setFile] = useState(null);
  const [sheetUrl, setSheetUrl] = useState("");
  const [syncInterval, setSyncInterval] = useState("");

  const [datasets, setDatasets] = useState([]);
  const [targetDatasetId, setTargetDatasetId] = useState(""); // "" = create new
  const [datasetName, setDatasetName] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    listDatasets()
      .then(setDatasets)
      .catch(() => {
        /* non-fatal - upload still works as "always create new" */
      });
  }, []);

  function handleFileSelected(selectedFile, selectionError) {
    setError(selectionError);
    setFile(selectedFile);
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError(null);
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    setError(null);
    try {
      let run;
      if (mode === MODES.FILE) {
        if (!file) return;
        run = await uploadDataset(
          file,
          targetDatasetId ? undefined : datasetName || undefined,
          targetDatasetId || undefined
        );
      } else {
        if (!sheetUrl.trim()) return;
        run = await connectSheet(
          sheetUrl.trim(),
          targetDatasetId ? undefined : datasetName || undefined,
          targetDatasetId || undefined,
          syncInterval ? parseInt(syncInterval, 10) : undefined
        );
      }
      navigate(`/datasets/${run.dataset_id}`);
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  }

  const canSubmit = mode === MODES.FILE ? Boolean(file) : Boolean(sheetUrl.trim());

  return (
    <div className="mx-auto max-w-2xl px-8 py-12">
      <h1 className="text-2xl font-semibold text-navy">Add a dataset</h1>
      <p className="mt-1 text-sm text-muted">
        We'll check completeness, duplicates, formatting, and structure, and give you a
        reliability score with exactly why it is what it is.
      </p>

      <div className="mt-6 inline-flex rounded-lg border border-border bg-white p-1">
        <button
          onClick={() => switchMode(MODES.FILE)}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
            mode === MODES.FILE ? "bg-navy text-white" : "text-muted hover:text-navy"
          }`}
        >
          Upload file
        </button>
        <button
          onClick={() => switchMode(MODES.SHEET)}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
            mode === MODES.SHEET ? "bg-navy text-white" : "text-muted hover:text-navy"
          }`}
        >
          Connect Google Sheet
        </button>
      </div>

      {mode === MODES.FILE ? (
        <div className="mt-6">
          <UploadDropzone onFileSelected={handleFileSelected} disabled={isSubmitting} />
          {file && (
            <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-white px-4 py-3">
              <span className="text-sm text-navy">{file.name}</span>
              <button
                className="text-xs font-medium text-muted hover:text-danger"
                onClick={() => setFile(null)}
                disabled={isSubmitting}
              >
                Remove
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
              Google Sheets link
            </label>
            <input
              type="text"
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/.../edit"
              disabled={isSubmitting}
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
            />
            <p className="mt-1 text-xs text-muted">
              The sheet must be shared as "Anyone with the link can view" — we don't use your
              Google account, we just read the public link.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
              Auto-sync every (optional)
            </label>
            <select
              value={syncInterval}
              onChange={(e) => setSyncInterval(e.target.value)}
              disabled={isSubmitting}
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
            >
              <option value="">Manual sync only</option>
              <option value="60">Hourly</option>
              <option value="1440">Daily</option>
              <option value="10080">Weekly</option>
            </select>
            <p className="mt-1 text-xs text-muted">
              You can always trigger a sync manually from the dataset's dashboard too.
            </p>
          </div>
        </div>
      )}

      <div className="mt-6">
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
          Dataset
        </label>
        <select
          value={targetDatasetId}
          onChange={(e) => setTargetDatasetId(e.target.value)}
          disabled={isSubmitting}
          className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
        >
          <option value="">+ New dataset</option>
          {datasets.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>
              {dataset.name} — add a new version
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted">
          {targetDatasetId
            ? "This will be added as a new version of the selected dataset."
            : "Using the same name again later will add to this dataset's history."}
        </p>
      </div>

      {!targetDatasetId && (
        <div className="mt-4">
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
            Dataset name (optional)
          </label>
          <input
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="e.g. Monthly Sales Export"
            disabled={isSubmitting}
            className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
          />
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!canSubmit || isSubmitting}
        className="mt-6 w-full rounded-lg bg-navy px-4 py-3 text-sm font-semibold text-white transition hover:bg-navy-light disabled:cursor-not-allowed disabled:opacity-40"
      >
        {isSubmitting
          ? mode === MODES.FILE
            ? "Analyzing…"
            : "Connecting…"
          : mode === MODES.FILE
            ? "Analyze dataset"
            : "Connect & analyze"}
      </button>
    </div>
  );
}
