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

export type DashboardTotals = {
  total_questions: number;
  total_tokens_in: number;
  total_tokens_out: number;
  avg_latence_ms: number;
  estimated_cost_usd: number;
};

export type DashboardDay = {
  day: string;
  questions: number;
  tokens_in: number;
  tokens_out: number;
  estimated_cost_usd: number;
};

export type DashboardData = {
  totals: DashboardTotals;
  by_day: DashboardDay[];
  note: string;
};

export async function fetchMe(accessToken: string): Promise<{ is_admin: boolean }> {
  const response = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`);
  }
  return response.json();
}

export type AssetCategory =
  | "habitation_principale"
  | "actif_professionnel"
  | "vehicule_12cv_ou_moins"
  | "vehicule_plus_de_12cv"
  | "depot_bancaire_ou_postal"
  | "autre";

export type WealthTaxInput = {
  resident_in_tunisia: boolean;
  assets: { description: string; value_tnd: number; location: "tunisie" | "etranger"; category: AssetCategory }[];
  deductible_debts_tnd: number;
};

export type CitedLine = { label: string; amount: string; article: string | null };

export type WealthTaxResult = {
  total: string;
  steps: CitedLine[];
  notes: { text: string; article: string | null }[];
  sources: Source[];
};

export async function computeWealthTax(input: WealthTaxInput, accessToken: string): Promise<WealthTaxResult> {
  const response = await fetch(`${API_BASE}/calculs/impot-fortune`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`);
  }
  return response.json();
}

// 403 si le compte connecté n'a pas le rôle admin (voir app/auth.py get_current_admin_id).
export async function fetchDashboard(accessToken: string): Promise<DashboardData> {
  const response = await fetch(`${API_BASE}/admin/dashboard`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`Erreur serveur (${response.status})`);
  }
  return response.json();
}
