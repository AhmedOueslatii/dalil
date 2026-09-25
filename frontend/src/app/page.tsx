import Link from "next/link";

// Témoignages réels uniquement : la section s'affiche automatiquement dès qu'un
// témoignage est ajouté ici. Ne jamais y mettre d'avis inventés.
const TESTIMONIALS: { quote: string; author: string; role: string }[] = [];

const PAINS = [
  {
    title: "Des heures perdues dans les textes",
    text: "Lois de finances, codes, notes communes : retrouver le bon article et sa dernière version prend un temps que vous ne facturez pas.",
  },
  {
    title: "Des réponses d'IA impossibles à vérifier",
    text: "Les chatbots généralistes répondent avec assurance, sans source. Une erreur dans un dossier client engage votre responsabilité.",
  },
  {
    title: "Des données clients trop sensibles",
    text: "Coller le nom d'un client et sa situation fiscale dans un outil grand public, c'est exposer des informations confidentielles.",
  },
];

const BENEFITS = [
  {
    title: "Répondez à vos clients en minutes, pas en heures",
    text: "Posez votre question en langage courant : Dalil retrouve les passages pertinents et rédige une réponse claire.",
  },
  {
    title: "Justifiez chaque réponse",
    text: "Chaque affirmation renvoie à l'article exact qui la fonde. Pas de source, pas de réponse : Dalil dit « je ne sais pas ».",
  },
  {
    title: "Calculez sans erreur",
    text: "Les calculs sont faits par le code, jamais par l'IA, avec des taux validés et cités ligne par ligne.",
  },
  {
    title: "Protégez vos clients",
    text: "Les noms sont anonymisés avant tout traitement externe, et l'historique de chaque compte reste privé.",
  },
];

const FACTS = [
  { value: "100 %", label: "des réponses citées, ou « je ne sais pas »" },
  { value: "0", label: "nom de client transmis à un modèle externe" },
  { value: "LF 2026", label: "intégrée et consultable article par article" },
];

const FAQ = [
  {
    question: "Et si l'IA se trompe ou invente une réponse ?",
    answer:
      "Dalil ne répond qu'à partir des textes officiels qu'il a retrouvés, avec l'article cité pour chaque affirmation. Si aucun passage ne permet de répondre, il répond « je ne sais pas » au lieu d'improviser. Vous pouvez toujours vérifier la source en un clic.",
  },
  {
    question: "Mes données et celles de mes clients sont-elles en sécurité ?",
    answer:
      "Les noms de personnes et de sociétés sont remplacés par des pseudonymes avant tout appel à un modèle externe. Chaque compte ne voit que son propre historique. Les calculs fiscaux, eux, n'utilisent aucun modèle externe.",
  },
  {
    question: "Quels textes Dalil couvre-t-il aujourd'hui ?",
    answer:
      "La loi de finances 2026 est intégrée intégralement. Les codes fiscaux (IRPP/IS, TVA) et les notes communes sont en cours d'intégration. Dalil vous indique toujours sur quel texte repose sa réponse.",
  },
];

function PrimaryCta({ children }: { children: React.ReactNode }) {
  return (
    <Link
      href="/signup"
      className="inline-block rounded-lg bg-amber-400 px-6 py-3 text-sm font-semibold text-emerald-950 shadow-sm hover:bg-amber-300"
    >
      {children}
    </Link>
  );
}

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
          <span className="text-lg font-semibold text-emerald-900">Dalil</span>
          <nav className="flex items-center gap-5 text-sm">
            <a href="#probleme" className="hidden text-neutral-600 hover:text-neutral-900 sm:inline">Le problème</a>
            <a href="#solution" className="hidden text-neutral-600 hover:text-neutral-900 sm:inline">La solution</a>
            <a href="#faq" className="hidden text-neutral-600 hover:text-neutral-900 sm:inline">FAQ</a>
            <Link href="/login" className="text-neutral-600 hover:text-neutral-900">Se connecter</Link>
            <Link href="/signup" className="rounded-lg bg-emerald-900 px-4 py-2 font-medium text-white hover:bg-emerald-800">
              Essayer
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-emerald-950 text-white">
        <div className="mx-auto grid w-full max-w-5xl items-center gap-10 px-4 py-16 md:grid-cols-2 md:py-24">
          <div>
            <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Des réponses fiscales sourcées, en quelques secondes.
            </h1>
            <p className="mt-5 text-lg text-emerald-100">
              Dalil est l&apos;assistant des cabinets comptables tunisiens : il cherche dans les textes officiels et
              vous répond avec l&apos;article exact. Aucune citation, aucune réponse.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <PrimaryCta>Essayer gratuitement</PrimaryCta>
              <a href="#solution" className="text-sm font-medium text-emerald-100 underline-offset-4 hover:underline">
                Voir comment ça marche
              </a>
            </div>
          </div>

          <div className="rounded-xl bg-white p-5 text-neutral-900 shadow-xl">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Exemple de réponse</p>
            <p className="mt-3 text-sm font-medium">Quel est le montant des recettes du budget de l&apos;État pour 2026 ?</p>
            <p className="mt-3 text-sm leading-relaxed text-neutral-700">
              Les recettes du budget de l&apos;État pour 2026 sont estimées à 52 560 000 000 dinars{" "}
              <span className="rounded bg-emerald-50 px-1.5 text-xs font-semibold text-emerald-800">Article premier</span>
            </p>
            <p className="mt-4 border-t border-neutral-100 pt-3 text-xs text-neutral-400">
              Source : Loi n° 2025-17 portant loi de finances pour l&apos;année 2026
            </p>
          </div>
        </div>
      </section>

      {/* Problème */}
      <section id="probleme" className="scroll-mt-20 px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-bold tracking-tight text-neutral-900">
            La veille fiscale vous coûte plus qu&apos;elle ne vous rapporte
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {PAINS.map((pain) => (
              <div key={pain.title} className="rounded-xl border border-neutral-200 bg-white p-6">
                <h3 className="font-semibold text-neutral-900">{pain.title}</h3>
                <p className="mt-2 text-sm text-neutral-600">{pain.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution & bénéfices */}
      <section id="solution" className="scroll-mt-20 bg-white px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-bold tracking-tight text-neutral-900">
            Dalil vous rend ce temps, sans sacrifier la rigueur
          </h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2">
            {BENEFITS.map((benefit) => (
              <div key={benefit.title} className="flex gap-4">
                <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-900">
                  ✓
                </span>
                <div>
                  <h3 className="font-semibold text-neutral-900">{benefit.title}</h3>
                  <p className="mt-1 text-sm text-neutral-600">{benefit.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Preuve sociale */}
      <section className="px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-bold tracking-tight text-neutral-900">Conçu pour inspirer confiance</h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-3">
            {FACTS.map((fact) => (
              <div key={fact.label} className="rounded-xl border border-neutral-200 bg-white p-6 text-center">
                <p className="text-3xl font-bold text-emerald-900">{fact.value}</p>
                <p className="mt-2 text-sm text-neutral-600">{fact.label}</p>
              </div>
            ))}
          </div>

          {TESTIMONIALS.length > 0 && (
            <div className="mt-10 grid gap-6 md:grid-cols-2">
              {TESTIMONIALS.map((t) => (
                <figure key={t.author} className="rounded-xl bg-white p-6 shadow-sm">
                  <blockquote className="text-neutral-700">« {t.quote} »</blockquote>
                  <figcaption className="mt-4 text-sm">
                    <span className="font-semibold text-neutral-900">{t.author}</span>
                    <span className="text-neutral-500"> — {t.role}</span>
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="scroll-mt-20 bg-white px-4 py-16">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-3xl font-bold tracking-tight text-neutral-900">Vos questions</h2>
          <div className="mt-10 divide-y divide-neutral-200 rounded-xl border border-neutral-200">
            {FAQ.map((item) => (
              <details key={item.question} className="group p-5">
                <summary className="flex cursor-pointer list-none items-center justify-between font-semibold text-neutral-900">
                  {item.question}
                  <span className="ml-4 text-emerald-800 transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-neutral-600">{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="bg-emerald-950 px-4 py-16 text-center text-white">
        <h2 className="text-3xl font-bold tracking-tight">Votre prochaine question fiscale mérite une source.</h2>
        <p className="mx-auto mt-4 max-w-xl text-emerald-100">
          Créez votre compte en une minute et posez-la à Dalil.
        </p>
        <div className="mt-8">
          <PrimaryCta>Créer mon compte gratuit</PrimaryCta>
        </div>
      </section>

      <footer className="px-4 py-6 text-center text-xs text-neutral-400">
        Dalil — assistant fiscal pour les cabinets comptables tunisiens
      </footer>
    </div>
  );
}
