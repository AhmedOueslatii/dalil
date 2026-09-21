# Dalil

Assistant fiscal pour cabinets comptables tunisiens, basé sur un RAG (recherche de
passages pertinents puis rédaction d'une réponse citée). Voir [CLAUDE.md](CLAUDE.md)
pour le contexte produit, la stack et les règles non négociables.

Étape actuelle : **fondations** (base de données + API minimale avec health check).

## Démarrage

1. Copier le fichier d'environnement :

   ```bash
   cp .env.example .env
   ```

2. Démarrer la base de données PostgreSQL + pgvector :

   ```bash
   docker compose up -d
   ```

3. Créer un environnement virtuel et installer les dépendances :

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Lancer l'API :

   ```bash
   uvicorn app.main:app --reload
   ```

5. Vérifier que tout fonctionne :

   ```bash
   curl http://localhost:8000/health
   ```

## Tests

```bash
pytest
```
