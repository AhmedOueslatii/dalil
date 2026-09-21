// Transforme "[Art. 2]" ou "[Article premier]" (format imposé par le prompt système
// dans app/generate.py) en badges visuels, sans jamais injecter du HTML brut : la
// réponse vient d'un LLM, donc on ne lui fait pas confiance comme source de markup.
const CITATION_PATTERN = /\[(Article premier|Art\.\s*\d+)\]/g;

export function CitedAnswer({ text }: { text: string }) {
  const parts = text.split(CITATION_PATTERN);

  return (
    <p className="whitespace-pre-wrap leading-relaxed text-neutral-900">
      {parts.map((part, i) =>
        // Les indices impairs sont les groupes capturés par le split (les citations).
        i % 2 === 1 ? (
          <span
            key={i}
            className="inline-block rounded bg-emerald-50 px-1.5 text-sm font-semibold text-emerald-800"
          >
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}
