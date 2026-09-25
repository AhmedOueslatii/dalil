"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";
import { useAuth } from "@/lib/supabase/AuthProvider";
import { createClient } from "@/lib/supabase/client";

const LINKS = [
  { href: "/app", label: "Assistant" },
  { href: "/calculs", label: "Calculs" },
];

export function Navbar() {
  const { user, session } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (!session) return;
    fetchMe(session.access_token)
      .then((me) => setIsAdmin(me.is_admin))
      .catch(() => setIsAdmin(false));
  }, [session]);

  async function handleLogout() {
    await createClient().auth.signOut();
    router.push("/");
  }

  const links = isAdmin ? [...LINKS, { href: "/admin", label: "Tableau de bord" }] : LINKS;

  return (
    <nav className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/app" className="text-lg font-semibold text-emerald-900">
            Dalil
          </Link>
          <div className="flex gap-1">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                    active ? "bg-emerald-50 text-emerald-900" : "text-neutral-600 hover:bg-neutral-100"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="hidden text-neutral-500 sm:inline">{user?.email}</span>
          <button onClick={handleLogout} className="text-neutral-600 hover:text-neutral-900 hover:underline">
            Se déconnecter
          </button>
        </div>
      </div>
    </nav>
  );
}
