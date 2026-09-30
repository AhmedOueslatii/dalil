"use client";

import { useState } from "react";
import { sendFeedback } from "@/lib/api";

type Props = { questionId: number; accessToken: string };

export function AnswerFeedback({ questionId, accessToken }: Props) {
  const [rating, setRating] = useState<1 | -1 | null>(null);
  const [wrongCitation, setWrongCitation] = useState(false);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(value: 1 | -1, details: { wrong_citation?: boolean; comment?: string } = {}) {
    setError(null);
    try {
      await sendFeedback(questionId, { rating: value, ...details }, accessToken);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  function vote(value: 1 | -1) {
    setRating(value);
    setSent(false);
    // Un 👍 s'enregistre directement ; un 👎 ouvre d'abord le détail, pour qu'on sache
    // ce qui ne va pas (citation fausse ou autre) au lieu d'un simple signal négatif.
    if (value === 1) submit(1);
  }

  const buttonClass = (active: boolean) =>
    `rounded-lg border px-2.5 py-1 text-sm ${
      active ? "border-emerald-700 bg-emerald-50" : "border-neutral-200 hover:bg-neutral-50"
    }`;

  return (
    <div className="mt-4 border-t border-neutral-200 pt-3 text-sm">
      <div className="flex items-center gap-2 text-neutral-500">
        <span>Cette réponse vous a-t-elle aidé ?</span>
        <button type="button" onClick={() => vote(1)} className={buttonClass(rating === 1)} aria-label="Réponse utile">
          👍
        </button>
        <button type="button" onClick={() => vote(-1)} className={buttonClass(rating === -1)} aria-label="Réponse pas utile">
          👎
        </button>
        {sent && <span className="text-emerald-700">Merci pour votre retour.</span>}
      </div>

      {rating === -1 && !sent && (
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit(-1, { wrong_citation: wrongCitation, comment: comment.trim() || undefined });
          }}
        >
          <label className="flex items-center gap-2 text-neutral-700">
            <input type="checkbox" checked={wrongCitation} onChange={(e) => setWrongCitation(e.target.checked)} />
            Une citation est erronée (mauvais article ou texte qui ne dit pas cela)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={2000}
            placeholder="Qu'est-ce qui ne va pas ? (facultatif)"
            className="min-h-[60px] rounded-lg border border-neutral-300 bg-white p-2 text-sm text-neutral-900 focus:border-emerald-700 focus:outline-none"
          />
          <button
            type="submit"
            className="self-start rounded-lg bg-emerald-900 px-4 py-1.5 font-medium text-white hover:bg-emerald-800"
          >
            Envoyer
          </button>
        </form>
      )}
      {error && <p className="mt-2 text-red-700">Erreur : {error}</p>}
    </div>
  );
}
