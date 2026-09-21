import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-6">
        <span className="text-lg font-semibold text-emerald-900">Dalil</span>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/login" className="text-neutral-600 hover:text-neutral-900">
            Se connecter
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-emerald-900 px-4 py-2 font-medium text-white hover:bg-emerald-800"
          >
            Créer un compte
          </Link>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl">
          L&apos;assistant fiscal de votre cabinet, sans invention.
        </h1>
        <p className="mt-5 max-w-xl text-lg text-neutral-600">
          Dalil recherche les passages pertinents dans les textes fiscaux officiels
          tunisiens et rédige une réponse citée à partir d&apos;eux uniquement. Aucune
          citation, aucune réponse.
        </p>

        <div className="mt-8 flex gap-3">
          <Link
            href="/signup"
            className="rounded-lg bg-emerald-900 px-6 py-3 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Créer un compte gratuit
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-neutral-300 px-6 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          >
            Se connecter
          </Link>
        </div>

        <div className="mt-16 grid w-full gap-6 text-left sm:grid-cols-3">
          <div className="rounded-xl border border-neutral-200 bg-white p-5">
            <h3 className="font-semibold text-neutral-900">Citations obligatoires</h3>
            <p className="mt-2 text-sm text-neutral-600">
              Chaque réponse renvoie à l&apos;article exact qui la justifie. Si aucun
              passage pertinent n&apos;est trouvé, Dalil répond « je ne sais pas ».
            </p>
          </div>
          <div className="rounded-xl border border-neutral-200 bg-white p-5">
            <h3 className="font-semibold text-neutral-900">Données clients protégées</h3>
            <p className="mt-2 text-sm text-neutral-600">
              Les noms de vos clients sont anonymisés avant tout envoi à un modèle
              externe.
            </p>
          </div>
          <div className="rounded-xl border border-neutral-200 bg-white p-5">
            <h3 className="font-semibold text-neutral-900">Historique par cabinet</h3>
            <p className="mt-2 text-sm text-neutral-600">
              Chaque compte dispose de son propre historique de questions, isolé des
              autres utilisateurs.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
