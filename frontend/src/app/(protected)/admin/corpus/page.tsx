"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CorpusState, deleteDocument, fetchCorpus, reindexCorpus, uploadDocument } from "@/lib/api";
import { useAuth } from "@/lib/supabase/AuthProvider";

const inputClass =
  "rounded-lg border border-neutral-300 bg-white p-2 text-sm text-neutral-900 focus:border-emerald-700 focus:outline-none";

export default function CorpusPage() {
  const { session } = useAuth();
  const token = session?.access_token;
  const [state, setState] = useState<CorpusState | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setState(await fetchCorpus(token));
    } catch (err) {
      if (err instanceof Error && err.message.includes("administrateurs")) setForbidden(true);
      else setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  // Pendant l'indexation (plusieurs minutes), on rafraîchit la progression toutes
  // les 4 secondes ; plus de requêtes une fois terminée.
  const indexing = state?.indexing.running ?? false;
  useEffect(() => {
    if (!indexing) return;
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
  }, [indexing, load]);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    const form = e.currentTarget;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(new FormData(form), token);
      form.reset();
      await load();
      // L'indexation démarre juste après la réponse du serveur : un second
      // rafraîchissement la voit en cours et déclenche le suivi de progression.
      setTimeout(load, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number, titre: string) {
    if (!token || !window.confirm(`Supprimer « ${titre} » et tous ses articles du corpus ?`)) return;
    try {
      await deleteDocument(id, token);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  async function handleReindex() {
    if (!token) return;
    await reindexCorpus(token);
    setTimeout(load, 1500);
  }

  if (forbidden) {
    return (
      <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center gap-3 px-4 py-8 text-center">
        <h1 className="text-lg font-semibold">Accès réservé</h1>
        <p className="text-sm text-neutral-500">Cette page est réservée aux administrateurs.</p>
        <Link href="/app" className="text-sm font-medium text-emerald-800 hover:underline">
          Retour à l&apos;application
        </Link>
      </div>
    );
  }

  const incomplete = state?.documents.some((d) => d.embedded < d.chunks) ?? false;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="rounded-xl bg-emerald-900 px-6 py-5 text-white">
        <h1 className="text-xl font-semibold">Corpus</h1>
        <p className="mt-1 text-sm text-emerald-100">Textes officiels sur lesquels Dalil fonde ses réponses</p>
      </header>

      <form onSubmit={handleUpload} className="flex flex-col gap-3 rounded-xl border border-neutral-200 bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Ajouter un texte</h2>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_160px]">
          <input name="file" type="file" accept="application/pdf,.pdf" required className="text-sm text-neutral-700" />
          <input name="titre" required minLength={3} placeholder="Titre (ex : Code de la TVA)" className={inputClass} />
          <input name="date_texte" type="date" className={inputClass} aria-label="Date du texte" />
        </div>
        <p className="text-xs text-neutral-400">
          PDF avec texte (pas un scan), articles marqués « Art. X » ou « Article premier ». 20 Mo maximum.
        </p>
        <button
          type="submit"
          disabled={uploading}
          className="self-start rounded-lg bg-emerald-900 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:bg-neutral-400"
        >
          {uploading ? "Découpage en cours…" : "Ajouter au corpus"}
        </button>
      </form>

      {error && <p className="text-sm text-red-700">Erreur : {error}</p>}

      <section className="rounded-xl border border-neutral-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Textes intégrés</h2>
          {indexing ? (
            <span className="text-sm text-amber-700">Indexation en cours…</span>
          ) : (
            incomplete && (
              <button onClick={handleReindex} className="text-sm font-medium text-emerald-800 hover:underline">
                Relancer l&apos;indexation
              </button>
            )
          )}
        </div>

        {state?.indexing.last_error && !indexing && (
          <p className="mb-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
            Dernière indexation interrompue (souvent le quota Gemini) : relancez-la dans une minute. Détail :{" "}
            {state.indexing.last_error}
          </p>
        )}

        {!state ? (
          <p className="text-sm text-neutral-500">Chargement…</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-xs uppercase text-neutral-400">
                <th className="py-2 font-medium">Texte</th>
                <th className="py-2 font-medium">Date</th>
                <th className="py-2 font-medium">Indexation</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {state.documents.map((d) => {
                const done = d.embedded === d.chunks;
                return (
                  <tr key={d.id}>
                    <td className="py-2 pr-3">
                      <p className="font-medium text-neutral-900">{d.titre}</p>
                      <p className="text-xs text-neutral-400">{d.source}</p>
                    </td>
                    <td className="py-2 pr-3 text-neutral-600">
                      {d.date_texte ? new Date(d.date_texte).toLocaleDateString("fr-FR") : "—"}
                    </td>
                    <td className="py-2 pr-3">
                      <span className={done ? "text-emerald-700" : "text-amber-700"}>
                        {d.embedded}/{d.chunks} passages {done ? "✓" : ""}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => handleDelete(d.id, d.titre)}
                        className="text-xs text-neutral-400 hover:text-red-700"
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
