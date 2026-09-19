import Logo from "./Logo";

export default function DataScoreHeader() {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Logo size={20} variant="outline" />
      <span className="text-sm font-extrabold text-navy">DataScore</span>
      <span className="ml-auto text-xs text-muted">Data Quality &amp; Reliability</span>
    </div>
  );
}
