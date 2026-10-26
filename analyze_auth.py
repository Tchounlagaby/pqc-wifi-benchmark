#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_auth.py
===============

Analyse les fichiers CSV d'authentification produits par le banc de test
802.1X (voir le script `run_clients.sh`). Pour chaque scénario, calcule :

  - la période réelle de l'expérience (première et dernière mesure) ;
  - le nombre de tentatives et de réussites ;
  - le taux de réussite ;
  - la latence moyenne, l'écart-type, la médiane et le 95e centile (ms).

Le format attendu du CSV est :
    timestamp,client,user,scenario,result,latency_ms

Usage :
    python3 analyze_auth.py ../data/8021x_auth_*.csv
    python3 analyze_auth.py ../data/8021x_auth_*.csv ../data/bruteforce_auth_*.csv
"""

import csv
import math
import statistics as stats
import sys
from collections import defaultdict


def centile(valeurs_triees, p):
    if not valeurs_triees:
        return 0
    rang = max(1, math.ceil(p / 100.0 * len(valeurs_triees)))
    return valeurs_triees[rang - 1]


def main():
    if len(sys.argv) < 2:
        print("Usage : python3 analyze_auth.py <fichier1.csv> [fichier2.csv ...]")
        sys.exit(1)

    lignes = defaultdict(list)
    for chemin in sys.argv[1:]:
        with open(chemin, newline="", encoding="utf-8") as f:
            for ligne in csv.DictReader(f):
                lignes[ligne["scenario"]].append(ligne)

    if not lignes:
        print("Aucune donnée trouvée.")
        sys.exit(1)

    for scenario, rows in lignes.items():
        latences = sorted(int(r["latency_ms"]) for r in rows)
        reussites = sum(1 for r in rows if r["result"] == "SUCCESS")
        horodatages = sorted(r["timestamp"] for r in rows)
        print(f"\n=== Scénario : {scenario} ===")
        print(f"Période             : {horodatages[0]}  ->  {horodatages[-1]}")
        print(f"Tentatives          : {len(rows)}")
        print(f"Réussites           : {reussites}")
        print(f"Taux de réussite    : {reussites / len(rows):.2%}")
        print(f"Latence moyenne     : {stats.mean(latences):.1f} ms")
        print(f"Écart-type latence  : {stats.stdev(latences) if len(latences) > 1 else 0:.1f} ms")
        print(f"Latence médiane     : {stats.median(latences):.1f} ms")
        print(f"Latence 95e centile : {centile(latences, 95)} ms")


if __name__ == "__main__":
    main()
