"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { useAuth } from "@/lib/supabase/AuthProvider";

// Groupe de routes (protected) : le dossier entre parenthèses n'apparaît pas dans
// l'URL (/app, /calculs, /admin restent inchangées). La vérification de session et
// la navbar sont faites une fois ici au lieu d'être dupliquées dans chaque page.
export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) {
      router.push("/login");
    }
  }, [loading, session, router]);

  if (loading || !session) {
    return <div className="flex flex-1 items-center justify-center text-sm text-neutral-500">Chargement…</div>;
  }

  return (
    <>
      <Navbar />
      {children}
    </>
  );
}
