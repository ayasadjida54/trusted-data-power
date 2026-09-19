import { useCallback, useRef, useState } from "react";

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];

function isAcceptedFile(file) {
  return ACCEPTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
}

export default function UploadDropzone({ onFileSelected, disabled }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (fileList) => {
      const file = fileList?.[0];
      if (!file) return;
      if (!isAcceptedFile(file)) {
        onFileSelected(null, "Please choose a .csv or .xlsx file.");
        return;
      }
      onFileSelected(file, null);
    },
    [onFileSelected]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragActive(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-8 py-16 text-center transition ${
        isDragActive ? "border-cyan bg-cyan-pale" : "border-border bg-white"
      } ${disabled ? "cursor-not-allowed opacity-60" : "hover:border-cyan/60"}`}
    >
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-cyan-pale">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
            stroke="#17B6E0"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-navy">
        Drop a CSV or Excel file here, or click to browse
      </p>
      <p className="mt-1 text-xs text-muted">.csv or .xlsx, up to a few hundred MB</p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx"
        className="hidden"
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
