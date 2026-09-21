import { createBrowserClient } from "@supabase/ssr";

// Client Supabase côté navigateur : utilisé dans les composants "use client" pour
// signup/login/logout et pour récupérer la session (donc le token à envoyer à l'API).
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
