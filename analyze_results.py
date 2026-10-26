#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_results.py
==================

Lit un ou plusieurs fichiers CSV produits par `crypto_benchmark.py` et calcule,
pour chaque algorithme, les statistiques à reporter dans l'article :

  - nombre de mesures ;
  - temps moyen (ms) et écart-type ;
  - temps médian et 95e centile (ms) ;
  - taille moyenne des données échangées (octets) ;
  - surcoût en temps par rapport à ECDH-P256 (référence).

Le résultat est affiché à l'écran ET enregistré dans deux fichiers à côté du
dernier CSV lu :
  - resume_crypto.csv      (tableau, pour Excel ou pour l'article)
  - resume_crypto.md       (tableau Markdown, prêt à coller dans un README)

Usage :
    python3 analyze_results.py ../data/crypto_benchmark_20261026_140000.csv
    python3 analyze_results.py ../data/crypto_benchmark_*.csv     # plusieurs fichiers
"""

import csv
import os
import statistics as stats
import sys
from collections import defaultdict

REFERENCE = "ECDH-P256"     # algorithme servant de base au calcul du surcoût


def centile(valeurs_triees, p):
    """Renvoie le p-ième centile (p entre 0 et 100), méthode du plus proche rang."""
    if not valeurs_triees:
        return 0.0
    import math
    rang = max(1, math.ceil(p / 100.0 * len(valeurs_triees)))
    return valeurs_triees[rang - 1]


def charger(fichiers):
    """Regroupe les lignes de tous les CSV par algorithme."""
    temps = defaultdict(list)       # algo -> [temps_ms, ...]
    octets = defaultdict(list)      # algo -> [octets, ...]
    for chemin in fichiers:
        with open(chemin, newline="", encoding="utf-8") as f:
            for ligne in csv.DictReader(f):
                algo = ligne["algorithme"]
                temps[algo].append(float(ligne["temps_ms"]))
                octets[algo].append(int(ligne["octets_reseau"]))
    return temps, octets


def main():
    if len(sys.argv) < 2:
        print("Usage : python3 analyze_results.py <fichier1.csv> [fichier2.csv ...]")
        sys.exit(1)

    fichiers = sys.argv[1:]
    temps, octets = charger(fichiers)
    if not temps:
        print("Aucune donnée trouvée.")
        sys.exit(1)

    # Temps moyen de la référence (pour le surcoût).
    moyenne_ref = stats.mean(temps[REFERENCE]) if REFERENCE in temps else None

    # On ordonne : la référence d'abord, puis les autres.
    ordre = ([REFERENCE] if REFERENCE in temps else []) + \
            sorted(a for a in temps if a != REFERENCE)

    lignes = []
    for algo in ordre:
        t = sorted(temps[algo])
        moy = stats.mean(t)
        ecart = stats.stdev(t) if len(t) > 1 else 0.0
        med = stats.median(t)
        p95 = centile(t, 95)
        taille = stats.mean(octets[algo])
        if moyenne_ref and moyenne_ref > 0:
            surcout = f"{(moy / moyenne_ref - 1) * 100:+.0f}%"
        else:
            surcout = "-"
        lignes.append({
            "Algorithme": algo,
            "Mesures": len(t),
            "Temps moyen (ms)": f"{moy:.4f}",
            "Ecart-type (ms)": f"{ecart:.4f}",
            "Mediane (ms)": f"{med:.4f}",
            "95e centile (ms)": f"{p95:.4f}",
            "Octets reseau": f"{taille:.0f}",
            "Surcout vs ECDH": surcout,
        })

    colonnes = list(lignes[0].keys())

    # --- Affichage à l'écran -------------------------------------------------
    largeurs = {c: max(len(c), max(len(str(l[c])) for l in lignes)) for c in colonnes}
    sep = "  "
    print()
    print(sep.join(c.ljust(largeurs[c]) for c in colonnes))
    print(sep.join("-" * largeurs[c] for c in colonnes))
    for l in lignes:
        print(sep.join(str(l[c]).ljust(largeurs[c]) for c in colonnes))
    print()

    # --- Enregistrement CSV --------------------------------------------------
    dossier = os.path.dirname(os.path.abspath(fichiers[-1]))
    chemin_csv = os.path.join(dossier, "resume_crypto.csv")
    with open(chemin_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        w.writerows(lignes)

    # --- Enregistrement Markdown ---------------------------------------------
    chemin_md = os.path.join(dossier, "resume_crypto.md")
    with open(chemin_md, "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(colonnes) + " |\n")
        f.write("| " + " | ".join("---" for _ in colonnes) + " |\n")
        for l in lignes:
            f.write("| " + " | ".join(str(l[c]) for c in colonnes) + " |\n")

    print(f"Tableau enregistré : {chemin_csv}")
    print(f"Tableau Markdown   : {chemin_md}")


if __name__ == "__main__":
    main()
