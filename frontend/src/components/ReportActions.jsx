import { useState } from "react";
import { createShareLink, downloadCsvReport, downloadPdfReport, revokeShareLink } from "../api/client";

export default function ReportActions({ runId, filename }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  async function handleDownloadPdf() {
    setIsBusy(true);
    setError(null);
    try {
      await downloadPdfReport(runId, `${filename}-report.pdf`);
    } catch {
      setError("Couldn't download the PDF report.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDownloadCsv() {
    setIsBusy(true);
    setError(null);
    try {
      await downloadCsvReport(runId, `${filename}-findings.csv`);
    } catch {
      setError("Couldn't download the CSV export.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateShareLink() {
    setIsBusy(true);
    setError(null);
    try {
      const { share_path } = await createShareLink(runId);
      setShareUrl(`${window.location.origin}${share_path}`);
    } catch {
      setError("Couldn't create a share link.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRevoke() {
    setIsBusy(true);
    setError(null);
    try {
      await revokeShareLink(runId);
      setShareUrl(null);
      setCopied(false);
    } catch {
      setError("Couldn't revoke the share link.");
    } finally {
      setIsBusy(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
      >
        Export & share
      </button>

      {isOpen && (
        <div className="absolute right-0 z-10 mt-2 w-80 rounded-lg border border-border bg-white p-4 shadow-pop">
          <div className="space-y-2">
            <button
              onClick={handleDownloadPdf}
              disabled={isBusy}
              className="w-full rounded-lg border border-border px-3 py-2 text-left text-sm text-navy hover:border-cyan/50 disabled:opacity-50"
            >
              Download PDF report
            </button>
            <button
              onClick={handleDownloadCsv}
              disabled={isBusy}
              className="w-full rounded-lg border border-border px-3 py-2 text-left text-sm text-navy hover:border-cyan/50 disabled:opacity-50"
            >
              Download CSV (findings)
            </button>
          </div>

          <div className="mt-4 border-t border-border pt-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Public share link
            </div>
            {shareUrl ? (
              <div className="space-y-2">
                <div className="truncate rounded-lg bg-panel px-3 py-2 text-xs text-navy">{shareUrl}</div>
                <div className="flex gap-2">
                  <button
                    onClick={handleCopy}
                    className="flex-1 rounded-lg bg-navy px-3 py-2 text-xs font-semibold text-white hover:bg-navy-light"
                  >
                    {copied ? "Copied!" : "Copy link"}
                  </button>
                  <button
                    onClick={handleRevoke}
                    disabled={isBusy}
                    className="rounded-lg border border-border px-3 py-2 text-xs font-medium text-danger hover:border-danger/50"
                  >
                    Revoke
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={handleCreateShareLink}
                disabled={isBusy}
                className="w-full rounded-lg border border-dashed border-border px-3 py-2 text-xs font-medium text-muted hover:border-cyan/50 hover:text-navy disabled:opacity-50"
              >
                Anyone with the link can view this report, no account needed. Create link →
              </button>
            )}
          </div>

          {error && <div className="mt-3 text-xs text-danger">{error}</div>}
        </div>
      )}
    </div>
  );
}
