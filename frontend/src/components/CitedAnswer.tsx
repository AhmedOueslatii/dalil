"use client";

import { useEffect, useState } from "react";
import type { Source } from "@/lib/api";

// Transforme "[Art. 2]" ou "[Article premier]" (format imposé par le prompt système
// dans app/generate.py) en badges visuels, sans jamais injecter du HTML brut : la
// réponse vient d'un LLM, donc on ne lui fait pas confiance comme source de markup.
const CITATION_PATTERN = /\[(Article premier|Art\.\s*\d+)\]/g;

// Le PDF source contient parfois des doubles espaces (« Art.  4 ») : même
// normalisation que le garde-fou côté backend (app/guardrails.py).
const normalize = (article: string) => article.replace(/\s+/g, " ").trim().toLowerCase();

export function CitedAnswer({ text, sources = [] }: { text: string; sources?: Source[] }) {
  const [openArticle, setOpenArticle] = useState<string | null>(null);
  const parts = text.split(CITATION_PATTERN);

  // Un article peut correspondre à plusieurs passages (article long sous-découpé).
  const passagesFor = (article: string) =>
    sources.filter((s) => s.texte && normalize(s.article) === normalize(article));

  return (
    <>
      <p className="whitespace-pre-wrap leading-relaxed text-neutral-900">
        {parts.map((part, i) => {
          // Les indices impairs sont les groupes capturés par le split (les citations).
          if (i % 2 === 0) return <span key={i}>{part}</span>;
          const clickable = passagesFor(part).length > 0;
          return clickable ? (
            <button
              key={i}
              type="button"
              onClick={() => setOpenArticle(part)}
              title="Voir le texte de l'article"
              className="inline-block cursor-pointer rounded bg-emerald-50 px-1.5 text-sm font-semibold text-emerald-800 underline decoration-dotted underline-offset-2 hover:bg-emerald-100"
            >
              {part}
            </button>
          ) : (
            <span key={i} className="inline-block rounded bg-emerald-50 px-1.5 text-sm font-semibold text-emerald-800">
              {part}
            </span>
          );
        })}
      </p>
      {openArticle && (
        <PassageDialog article={openArticle} passages={passagesFor(openArticle)} onClose={() => setOpenArticle(null)} />
      )}
    </>
  );
}

function PassageDialog({ article, passages, onClose }: { article: string; passages: Source[]; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Texte de ${article}`}
        className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900">{article}</h3>
            <p className="mt-0.5 text-xs text-neutral-500">{passages[0]?.document}</p>
          </div>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-700" aria-label="Fermer">
            ✕
          </button>
        </div>
        <div className="mt-4 space-y-3">
          {passages.map((p, i) => (
            <p key={i} className="whitespace-pre-wrap rounded-lg bg-neutral-50 p-3 text-sm leading-relaxed text-neutral-800">
              {p.texte}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
