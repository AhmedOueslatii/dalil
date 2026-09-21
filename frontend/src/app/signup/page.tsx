"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { data, error } = await supabase.auth.signUp({ email, password });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    // Confirmation email désactivée côté projet Supabase pour cette étape : une
    // session est immédiatement disponible après signUp, pas besoin d'un aller-retour
    // par email avant de pouvoir utiliser l'app.
    if (data.session) {
      router.push("/app");
      router.refresh();
    } else {
      setError("Compte créé. Vérifiez votre email pour confirmer votre inscription.");
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-4 py-8">
      <div className="rounded-xl border border-neutral-200 bg-white p-6">
        <h1 className="mb-1 text-lg font-semibold">Créer un compte</h1>
        <p className="mb-5 text-sm text-neutral-500">Accédez à Dalil pour votre cabinet</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="rounded-lg border border-neutral-300 bg-white p-2.5 text-sm text-neutral-900 focus:border-emerald-700 focus:outline-none"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Mot de passe (min. 6 caractères)"
            required
            minLength={6}
            className="rounded-lg border border-neutral-300 bg-white p-2.5 text-sm text-neutral-900 focus:border-emerald-700 focus:outline-none"
          />

          {error && <p className="text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 rounded-lg bg-emerald-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            {loading ? "Création…" : "Créer mon compte"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-neutral-500">
          Déjà un compte ?{" "}
          <Link href="/login" className="font-medium text-emerald-800 hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
