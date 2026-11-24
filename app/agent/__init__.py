"""Agent fiscal Dalil : boucle LLM + outils (recherche, calculateurs) au-dessus du RAG.

La réponse simple (`app.generate`) fait une seule recherche puis un seul appel LLM.
L'agent, lui, peut enchaîner plusieurs recherches, appeler un calculateur et demander
une précision au comptable, tout en gardant les règles non négociables du CLAUDE.md.
"""
