"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchDashboard, DashboardData } from "@/lib/api";
import { useAuth } from "@/lib/supabase/AuthProvider";

export default function AdminDashboard() {
  const { session } = useAuth();

  const [data, setData] = useState<DashboardData | null>(null);
  // Connecté mais sans rôle admin (403 renvoyé par l'API) : ce n'est pas un problème
  // d'authentification, donc une page d'erreur distincte de la redirection vers /login.
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;

    fetchDashboard(session.access_token)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("403")) {
          setForbidden(true);
        } else {
          setError(err instanceof Error ? err.message : "Erreur inconnue");
        }
        setLoading(false);
      });
  }, [session]);

  if (forbidden) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-3 px-4 py-8 text-center">
        <h1 className="text-lg font-semibold">Accès réservé</h1>
        <p className="text-sm text-neutral-500">
          Cette page est réservée aux administrateurs.
        </p>
        <Link href="/app" className="text-sm font-medium text-emerald-800 hover:underline">
          Retour à l&apos;application
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="rounded-xl bg-emerald-900 px-6 py-5 text-white">
        <h1 className="text-xl font-semibold">Tableau de bord</h1>
        <p className="mt-1 text-sm text-emerald-100">Usage et coûts estimés, tous utilisateurs</p>
      </header>

      {loading && <p className="text-sm text-neutral-500">Chargement…</p>}
      {error && <p className="text-sm text-red-700">Erreur : {error}</p>}

      {data && (
        <>
          <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Questions" value={data.totals.total_questions.toLocaleString("fr-FR")} />
            <StatCard label="Tokens in" value={data.totals.total_tokens_in.toLocaleString("fr-FR")} />
            <StatCard label="Tokens out" value={data.totals.total_tokens_out.toLocaleString("fr-FR")} />
            <StatCard
              label="Coût estimé"
              value={`$${data.totals.estimated_cost_usd.toFixed(4)}`}
            />
          </section>

          <p className="text-xs text-neutral-400">{data.note}</p>

          <section className="rounded-xl border border-neutral-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
              30 derniers jours
            </h2>

            {data.by_day.length === 0 ? (
              <p className="text-sm text-neutral-500">Aucune activité sur cette période.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-xs uppercase text-neutral-400">
                    <th className="py-2 font-medium">Jour</th>
                    <th className="py-2 font-medium">Questions</th>
                    <th className="py-2 font-medium">Tokens in/out</th>
                    <th className="py-2 font-medium">Coût estimé</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {data.by_day.map((d) => (
                    <tr key={d.day}>
                      <td className="py-2">{new Date(d.day).toLocaleDateString("fr-FR")}</td>
                      <td className="py-2">{d.questions}</td>
                      <td className="py-2">
                        {d.tokens_in.toLocaleString("fr-FR")} / {d.tokens_out.toLocaleString("fr-FR")}
                      </td>
                      <td className="py-2">${d.estimated_cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">{label}</p>
      <p className="mt-1 text-xl font-semibold text-neutral-900">{value}</p>
    </div>
  );
}
