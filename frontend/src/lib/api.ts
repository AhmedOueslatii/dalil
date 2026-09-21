// URL de l'API FastAPI, configurable via .env.local pour ne pas coder en dur l'adresse
// (la régle "pas de secrets dans le code" du CLAUDE.md vaut aussi pour la config d'env).
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Source = {
  article: string;
  document: string;
  source: string;
};

export type QuestionResult = {
  reponse: string;
  sources: Source[];
  tokens_in: number;
  tokens_out: number;
  latence_ms: number;
};

export type HistoryItem = {
  id: number;
  texte: string;
  reponse: string;
  sources: Source[];
  tokens_in: number;
  tokens_out: number;
  latence_ms: number;
  created_at: string;
};

// L'API FastAPI exige désormais un token Supabase (Depends(get_current_user_id) dans
// app/main.py) : chaque appel doit porter le token de la session en cours.
export async function askQuestion(question: string, accessToken: string): Promise<QuestionResult> {
  const response = await fetch(`${API_BASE}/questions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`);
  }
  return response.json();
}

export async function fetchHistory(accessToken: string, limit = 10): Promise<HistoryItem[]> {
  const response = await fetch(`${API_BASE}/questions?limit=${limit}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`);
  }
  return response.json();
}
