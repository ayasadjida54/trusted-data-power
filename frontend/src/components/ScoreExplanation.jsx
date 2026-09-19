export default function ScoreExplanation({ sentences }) {
  return (
    <ul className="space-y-2">
      {sentences.map((sentence, idx) => (
        <li key={idx} className="flex gap-2 text-sm text-navy">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
          <span>{sentence}</span>
        </li>
      ))}
    </ul>
  );
}
