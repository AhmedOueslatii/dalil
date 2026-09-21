"""Jeu de questions/réponses de référence pour l'évaluation (étape 7).

Chaque cas donne une question et les articles attendus dans la réponse. Construit à
partir des vrais chunks ingérés de Loi2025_17-1.pdf (vérifiés en base), pas inventé.

expected_articles=[] signifie qu'on attend "Je ne sais pas." (question hors périmètre
ou dont la réponse n'est pas dans le corpus).
"""

GOLD_SET = [
    {
        "question": "Quel est le montant des recettes du budget de l'Etat pour 2026 ?",
        "expected_articles": ["Article premier"],
    },
    {
        "question": "Quel est l'effectif global du personnel autorisé pour l'année 2026 ?",
        "expected_articles": ["Art. 9"],
    },
    {
        "question": "Les équipements médicaux importés par les cliniques militaires bénéficient-ils d'une exonération ?",
        "expected_articles": ["Art. 17"],
    },
    {
        "question": "Une ligne de financement est-elle créée pour la restructuration des exploitations agricoles domaniales ?",
        "expected_articles": ["Art. 106"],
    },
    {
        "question": "Les personnes physiques résidentes tunisiennes peuvent-elles ouvrir des comptes en devises ?",
        "expected_articles": ["Art. 98"],
    },
    # Questions hors périmètre : la réponse correcte est "Je ne sais pas."
    {
        "question": "Quelle est la couleur du drapeau tunisien ?",
        "expected_articles": [],
    },
    {
        "question": "Quel est le taux de TVA applicable en France en 2026 ?",
        "expected_articles": [],
    },
    {
        "question": "Quelle est la capitale de la Tunisie ?",
        "expected_articles": [],
    },
]
