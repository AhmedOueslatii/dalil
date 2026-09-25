"use client";

import { useState } from "react";
import { AssetCategory, computeWealthTax, WealthTaxResult } from "@/lib/api";
import { useAuth } from "@/lib/supabase/AuthProvider";

const CATEGORIES: { value: AssetCategory; label: string }[] = [
  { value: "autre", label: "Autre bien (immeuble, terrain, placement…)" },
  { value: "habitation_principale", label: "Habitation principale (exclue)" },
  { value: "actif_professionnel", label: "Bien professionnel exploité (exclu)" },
  { value: "vehicule_12cv_ou_moins", label: "Véhicule non utilitaire ≤ 12 CV (exclu)" },
  { value: "vehicule_plus_de_12cv", label: "Véhicule non utilitaire > 12 CV" },
  { value: "depot_bancaire_ou_postal", label: "Dépôt bancaire ou postal (exclu)" },
];

type AssetRow = { description: string; value: string; location: "tunisie" | "etranger"; category: AssetCategory };

const emptyAsset = (): AssetRow => ({ description: "", value: "", location: "tunisie", category: "autre" });

const inputClass =
  "rounded-lg border border-neutral-300 bg-white p-2 text-sm text-neutral-900 focus:border-emerald-700 focus:outline-none";

export default function CalculsPage() {
  const { session } = useAuth();
  const [resident, setResident] = useState<boolean | null>(null);
  const [assets, setAssets] = useState<AssetRow[]>([emptyAsset()]);
  const [debts, setDebts] = useState("");
  const [result, setResult] = useState<WealthTaxResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateAsset(index: number, patch: Partial<AssetRow>) {
    setAssets((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!session || resident === null) return;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await computeWealthTax(
        {
          resident_in_tunisia: resident,
          assets: assets.map((a) => ({
            description: a.description,
            value_tnd: Number(a.value),
            location: a.location,
            category: a.category,
          })),
          deductible_debts_tnd: Number(debts || 0),
        },
        session.access_token,
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="rounded-xl bg-emerald-900 px-6 py-5 text-white">
        <h1 className="text-xl font-semibold">Impôt sur la fortune</h1>
        <p className="mt-1 text-sm text-emerald-100">
          Calcul selon l&apos;Art. 88 de la loi de finances 2026 — chaque montant est cité
        </p>
      </header>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5 rounded-xl border border-neutral-200 bg-white p-5">
        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-neutral-700">Résidence fiscale</legend>
          <div className="flex gap-4 text-sm text-neutral-800">
            <label className="flex items-center gap-2">
              <input type="radio" name="resident" required checked={resident === true} onChange={() => setResident(true)} />
              Résident en Tunisie
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="resident" checked={resident === false} onChange={() => setResident(false)} />
              Non-résident
            </label>
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 text-sm font-semibold text-neutral-700">Biens</legend>
          {assets.map((asset, i) => (
            <div key={i} className="grid gap-2 sm:grid-cols-[1fr_140px_120px_1fr_auto]">
              <input
                className={inputClass}
                placeholder="Description (ex : appartement Tunis)"
                value={asset.description}
                onChange={(e) => updateAsset(i, { description: e.target.value })}
              />
              <input
                className={inputClass}
                type="number"
                min="0"
                step="0.001"
                required
                placeholder="Valeur (TND)"
                value={asset.value}
                onChange={(e) => updateAsset(i, { value: e.target.value })}
              />
              <select
                className={inputClass}
                value={asset.location}
                onChange={(e) => updateAsset(i, { location: e.target.value as AssetRow["location"] })}
              >
                <option value="tunisie">Tunisie</option>
                <option value="etranger">Étranger</option>
              </select>
              <select
                className={inputClass}
                value={asset.category}
                onChange={(e) => updateAsset(i, { category: e.target.value as AssetCategory })}
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={assets.length === 1}
                onClick={() => setAssets((rows) => rows.filter((_, j) => j !== i))}
                className="rounded-lg px-2 text-sm text-neutral-500 hover:text-red-700 disabled:invisible"
                aria-label="Retirer ce bien"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setAssets((rows) => [...rows, emptyAsset()])}
            className="self-start text-sm font-medium text-emerald-800 hover:underline"
          >
            + Ajouter un bien
          </button>
        </fieldset>

        <label className="flex flex-col gap-1 text-sm font-semibold text-neutral-700 sm:w-64">
          Dettes déductibles (TND)
          <input
            className={inputClass}
            type="number"
            min="0"
            step="0.001"
            placeholder="0"
            value={debts}
            onChange={(e) => setDebts(e.target.value)}
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="self-start rounded-lg bg-emerald-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
        >
          {loading ? "Calcul…" : "Calculer"}
        </button>
      </form>

      {error && <p className="text-sm text-red-700">Erreur : {error}</p>}

      {result && (
        <section className="rounded-xl border border-neutral-200 bg-white p-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Impôt estimé</p>
          <p className="mt-1 text-3xl font-bold text-neutral-900">{result.total}</p>

          <table className="mt-5 w-full text-left text-sm">
            <tbody className="divide-y divide-neutral-100">
              {result.steps.map((step, i) => (
                <tr key={i}>
                  <td className="py-2 pr-3 text-neutral-700">{step.label}</td>
                  <td className="whitespace-nowrap py-2 pr-3 text-right font-medium text-neutral-900">{step.amount}</td>
                  <td className="w-20 py-2 text-right">{step.article && <Citation article={step.article} />}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <ul className="mt-4 space-y-1 text-sm text-neutral-600">
            {result.notes.map((note, i) => (
              <li key={i}>
                {note.text} {note.article && <Citation article={note.article} />}
              </li>
            ))}
          </ul>

          <p className="mt-4 border-t border-neutral-200 pt-3 text-xs text-neutral-400">
            Source : {result.sources.map((s) => `${s.article} — ${s.document}`).join(" ; ")}
          </p>
        </section>
      )}
    </div>
  );
}

function Citation({ article }: { article: string }) {
  return (
    <span className="inline-block rounded bg-emerald-50 px-1.5 text-xs font-semibold text-emerald-800">{article}</span>
  );
}
