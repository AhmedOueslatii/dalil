# Dalil — Assistant fiscal pour cabinets comptables tunisiens

## Contexte produit

Dalil est un assistant qui répond à des questions de fiscalité tunisienne en s'appuyant
sur un corpus de textes officiels (codes fiscaux, notes communes, circulaires). Il utilise
une architecture RAG (Retrieval-Augmented Generation) : on cherche d'abord les passages
pertinents dans le corpus, puis on rédige une réponse en se basant uniquement sur ces
passages, avec citation systématique de la source (article, document, date).

L'utilisateur cible est un comptable ou fiscaliste tunisien qui a besoin de réponses
fiables et traçables, pas d'un chatbot généraliste qui invente des réponses plausibles
mais fausses.

## Stack technique

- **Backend** : Python, FastAPI
- **Base de données** : PostgreSQL 16 + extension pgvector (recherche vectorielle) +
  recherche plein texte native PostgreSQL (`tsvector`) pour une recherche hybride
  (mot-clé + sémantique)
- **Driver DB** : psycopg 3 avec pool de connexions (`psycopg_pool`)
- **Configuration** : pydantic-settings (lecture depuis `.env`)
- **Conteneurisation** : Docker Compose pour la base de données

## Règles non négociables

1. **Citations obligatoires.** Toute réponse générée doit citer les passages sources
   (document, article) qui la justifient. Si aucun passage pertinent n'est trouvé, la
   réponse doit être « je ne sais pas » — jamais de réponse non sourcée. Ceci est la
   règle la plus importante du produit : elle garantit la confiance du client comptable.
2. **Anonymisation avant tout appel LLM.** Les noms de clients (personnes physiques ou
   morales) présents dans les questions doivent être anonymisés/pseudonymisés avant tout
   envoi à un LLM externe. Les données fiscales des clients des cabinets sont
   confidentielles.
3. **Coût en tokens journalisé.** Chaque appel LLM doit journaliser tokens en entrée,
   tokens en sortie et latence (voir table `questions`). Nécessaire pour maîtriser les
   coûts et diagnostiquer les lenteurs.
4. **Pas de secrets dans le code.** Toute information sensible (clés API, mots de passe,
   URL de connexion) vit dans `.env` (non versionné), jamais en dur dans le code source.

## Ordre de construction

1. **Fondations** (cette étape) : structure du projet, base de données, configuration,
   API minimale avec health check.
2. **Ingestion PDF** : extraction et découpage (chunking) des textes fiscaux en articles.
3. **Embeddings** : génération de vecteurs pour chaque chunk (recherche sémantique).
4. **Recherche hybride** : combinaison recherche plein texte (`tsvector`) + recherche
   vectorielle (pgvector) pour retrouver les passages pertinents.
5. **Génération citée** : appel LLM contraint à répondre uniquement à partir des
   passages retrouvés, avec citations.
6. **Évaluation** : mesure de la qualité des réponses (précision des citations, taux de
   « je ne sais pas » à bon escient, etc.).

Ne pas anticiper les étapes futures : à chaque étape, on construit uniquement ce qui est
nécessaire à cette étape.
