"use client";

import { useEffect, useState } from "react";
import { askQuestion, fetchHistory, HistoryItem, QuestionResult } from "@/lib/api";
import { CitedAnswer } from "@/components/CitedAnswer";
import { useAuth } from "@/lib/supabase/AuthProvider";

export default function Home() {
  const { session } = useAuth();

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QuestionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);

  async function loadHistory() {
    if (!session) return;
    try {
      const items = await fetchHistory(session.access_token, 10);
      setHistory(items);
      setHistoryError(null);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  useEffect(() => {
    if (session) loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || !session) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await askQuestion(trimmed, session.access_token);
      setResult(res);
      setQuestion("");
      loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="rounded-xl bg-emerald-900 px-6 py-5 text-white">
        <h1 className="text-xl font-semibold">Assistant fiscal</h1>
        <p className="mt-1 text-sm text-emerald-100">
          Réponses citées à partir des textes officiels tunisiens
        </p>
      </header>

      <form onSubmit={handleSubmit} className="rounded-xl border border-neutral-200 bg-white p-5">
        <div className="flex gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Posez une question fiscale (ex : quel est le montant des recettes du budget de l'État pour 2026 ?)"
            required
            className="min-h-[60px] flex-1 resize-y rounded-lg border border-neutral-300 bg-white p-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-emerald-700 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="shrink-0 rounded-lg bg-emerald-900 px-5 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            {loading ? "Recherche…" : "Demander"}
          </button>
        </div>
      </form>

      {(result || error || loading) && (
        <section className="rounded-xl border border-neutral-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Réponse
          </h2>

          {loading && (
            <p className="text-sm text-neutral-500">
              Recherche des passages et génération de la réponse…
            </p>
          )}

          {error && <p className="text-sm text-red-700">Erreur : {error}</p>}

          {result && (
            <>
              <CitedAnswer text={result.reponse} />

              {result.sources.length > 0 && (
                <div className="mt-4 border-t border-neutral-200 pt-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Sources consultées
                  </h3>
                  <ul className="space-y-1">
                    {result.sources.map((s, i) => (
                      <li key={i} className="text-sm text-neutral-500">
                        {s.article} — {s.document}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="mt-3 text-xs text-neutral-400">
                Tokens : {result.tokens_in} in / {result.tokens_out} out — Latence :{" "}
                {result.latence_ms}ms
              </p>
            </>
          )}
        </section>
      )}

      <section className="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Historique
        </h2>

        {historyError && <p className="text-sm text-red-700">Erreur : {historyError}</p>}

        {!historyError && history.length === 0 && (
          <p className="text-sm text-neutral-500">Aucune question posée pour l&apos;instant.</p>
        )}

        <ul className="divide-y divide-neutral-200">
          {history.map((item) => (
            <li key={item.id} className="py-3">
              <p className="text-sm font-semibold">{item.texte}</p>
              <div className="mt-1 text-sm text-neutral-500">
                <CitedAnswer text={item.reponse} />
              </div>
              <p className="mt-1 text-xs text-neutral-400">
                {new Date(item.created_at).toLocaleString("fr-FR")}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
