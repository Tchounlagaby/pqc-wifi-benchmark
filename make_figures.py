#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_figures.py
===============

Produit les figures de l'article à partir du résumé du benchmark
cryptographique (`resume_crypto.csv`, créé par analyze_results.py).

Génère deux images PNG dans le dossier ../figures :
  - fig_temps.png   : temps moyen par algorithme (barres + écart-type)
  - fig_octets.png  : taille des données échangées par algorithme

Ces figures sont en nuances de gris et lisibles en noir et blanc, comme
l'exigent beaucoup de conférences.

Usage :
    python3 make_figures.py ../data/resume_crypto.csv
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")                 # pas d'affichage interactif, on enregistre
import matplotlib.pyplot as plt       # noqa: E402


def lire(chemin):
    noms, temps, ecarts, octets = [], [], [], []
    with open(chemin, newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            noms.append(l["Algorithme"])
            temps.append(float(l["Temps moyen (ms)"]))
            ecarts.append(float(l["Ecart-type (ms)"]))
            octets.append(float(l["Octets reseau"]))
    return noms, temps, ecarts, octets


def barres(noms, valeurs, titre, ylabel, chemin_sortie, erreurs=None):
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(noms))
    ax.bar(x, valeurs, yerr=erreurs, capsize=4,
           color="0.6", edgecolor="black", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(noms, rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(titre)
    ax.grid(axis="y", linestyle=":", color="0.8")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(chemin_sortie, dpi=200)
    plt.close(fig)
    print(f"Figure enregistrée : {chemin_sortie}")


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else os.path.join("..", "data", "resume_crypto.csv")
    if not os.path.exists(chemin):
        print(f"Fichier introuvable : {chemin}")
        print("Lancez d'abord :  python3 analyze_results.py ../data/crypto_benchmark_*.csv")
        sys.exit(1)

    dossier = os.path.join(os.path.dirname(os.path.abspath(chemin)), "..", "figures")
    dossier = os.path.normpath(dossier)
    os.makedirs(dossier, exist_ok=True)

    noms, temps, ecarts, octets = lire(chemin)
    barres(noms, temps,
           "Temps moyen d'établissement de clé", "Temps (ms)",
           os.path.join(dossier, "fig_temps.png"), erreurs=ecarts)
    barres(noms, octets,
           "Données échangées sur le réseau", "Octets",
           os.path.join(dossier, "fig_octets.png"))


if __name__ == "__main__":
    main()
