import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Un package-lock.json existe dans le dossier utilisateur parent (hors du projet) ;
  // Turbopack déduit sinon une racine trop large. On la fixe explicitement au dossier
  // frontend pour éviter le warning et garantir un comportement stable.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
