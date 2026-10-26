#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crypto_benchmark.py
===================

Mesure et compare le coût des échanges de clés classiques et post-quantiques
utilisés dans l'article.

Pour chaque algorithme, le script répète l'opération complète d'établissement
de clé N fois (par défaut 1000) et enregistre, pour chaque répétition :
  - le temps écoulé en millisecondes ;
  - la taille des données échangées sur le réseau (octets).

Algorithmes mesurés :
  - ECDH P-256        : échange de clés sur courbe elliptique (référence du mémoire)
  - X25519            : échange de clés moderne, plus rapide
  - RSA-2048          : transport de clé RSA (chiffrement d'une clé de session)
  - ML-KEM-768        : encapsulation de clé post-quantique (NIST FIPS 203)
  - ECDH P-256 + ML-KEM-768 : échange HYBRIDE (classique + post-quantique)

ML-KEM et l'hybride nécessitent la bibliothèque `liboqs-python` (paquet `oqs`).
S'ils ne sont pas disponibles, le script mesure quand même ECDH, X25519 et RSA,
et prévient que la partie post-quantique a été ignorée.

Sortie : un fichier CSV horodaté dans le dossier choisi (option --out-dir).
Chaque ligne = une répétition. NE PAS supprimer ces fichiers : ce sont vos
données brutes.

Usage :
    python3 crypto_benchmark.py                 # 1000 répétitions, dossier ../data
    python3 crypto_benchmark.py -n 5000         # 5000 répétitions
    python3 crypto_benchmark.py --out-dir ./data

Analyse ensuite avec :
    python3 analyze_results.py ../data/crypto_benchmark_*.csv
"""

import argparse
import csv
import os
import platform
import time
from datetime import datetime, timezone

# --- Bibliothèque classique (toujours requise) ---------------------------------
from cryptography.hazmat.primitives.asymmetric import ec, x25519, rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# --- Bibliothèque post-quantique (optionnelle) ---------------------------------
try:
    import oqs  # liboqs-python
    OQS_AVAILABLE = True
except Exception:              # noqa: BLE001  (toute erreur d'import = pas de PQ)
    OQS_AVAILABLE = False

KEM_PQ = "ML-KEM-768"          # nom de l'algorithme dans liboqs


# ------------------------------------------------------------------------------
# Un "timer" précis. time.perf_counter() mesure le temps réellement écoulé,
# sans être perturbé par les changements d'heure du système.
# ------------------------------------------------------------------------------
def chrono_ms(fonction):
    """Exécute `fonction` et renvoie (résultat, durée_en_ms)."""
    debut = time.perf_counter()
    resultat = fonction()
    duree_ms = (time.perf_counter() - debut) * 1000.0
    return resultat, duree_ms


# ------------------------------------------------------------------------------
# Chaque fonction ci-dessous réalise UN échange de clé complet et renvoie :
#   (temps_ms, octets_sur_le_reseau)
# octets_sur_le_reseau = taille de ce qui transite entre les deux parties.
# ------------------------------------------------------------------------------

def mesure_ecdh_p256():
    """ECDH sur la courbe P-256 (secp256r1), puis dérivation HKDF."""
    def echange():
        # Alice et Bob génèrent chacun une paire de clés éphémère.
        cle_privee_a = ec.generate_private_key(ec.SECP256R1())
        cle_privee_b = ec.generate_private_key(ec.SECP256R1())
        # Chacun envoie sa clé publique à l'autre.
        pub_a = cle_privee_a.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        pub_b = cle_privee_b.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        # Chacun calcule le secret partagé.
        secret = cle_privee_a.exchange(ec.ECDH(), cle_privee_b.public_key())
        # Dérivation d'une clé de session AES-128 avec HKDF.
        HKDF(algorithm=hashes.SHA256(), length=16,
             salt=None, info=b"wifi-session").derive(secret)
        return len(pub_a) + len(pub_b)

    octets, duree = chrono_ms(echange)
    return duree, octets


def mesure_x25519():
    """X25519, échange de clés moderne (courbe de Montgomery)."""
    def echange():
        a = x25519.X25519PrivateKey.generate()
        b = x25519.X25519PrivateKey.generate()
        pub_a = a.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        pub_b = b.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        secret = a.exchange(b.public_key())
        HKDF(algorithm=hashes.SHA256(), length=16,
             salt=None, info=b"wifi-session").derive(secret)
        return len(pub_a) + len(pub_b)

    octets, duree = chrono_ms(echange)
    return duree, octets


def mesure_rsa2048(cle_privee, cle_publique):
    """
    Transport de clé RSA-2048 : une clé de session de 16 octets est chiffrée
    avec la clé publique du destinataire, puis déchiffrée.
    La paire de clés est générée UNE SEULE FOIS, hors de la mesure, car dans
    la pratique le certificat du serveur est déjà en place.
    """
    def echange():
        cle_session = os.urandom(16)                 # clé AES-128 à transporter
        chiffre = cle_publique.encrypt(
            cle_session,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None),
        )
        cle_privee.decrypt(
            chiffre,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None),
        )
        # Sur le réseau transite le chiffré (256 octets pour RSA-2048).
        return len(chiffre)

    octets, duree = chrono_ms(echange)
    return duree, octets


def mesure_mlkem():
    """
    ML-KEM-768 (post-quantique). Le client encapsule un secret avec la clé
    publique du serveur ; le serveur le décapsule. Sur le réseau transitent
    la clé publique et le ciphertext d'encapsulation.
    """
    def echange():
        with oqs.KeyEncapsulation(KEM_PQ) as serveur:
            cle_publique = serveur.generate_keypair()
            with oqs.KeyEncapsulation(KEM_PQ) as client:
                ciphertext, secret_client = client.encap_secret(cle_publique)
            secret_serveur = serveur.decap_secret(ciphertext)
            assert secret_client == secret_serveur      # vérification de cohérence
            return len(cle_publique) + len(ciphertext)

    octets, duree = chrono_ms(echange)
    return duree, octets


def mesure_hybride():
    """
    Échange HYBRIDE ECDH P-256 + ML-KEM-768.
    Les deux secrets (classique et post-quantique) sont concaténés puis passés
    dans HKDF. La sécurité tient tant qu'AU MOINS un des deux reste sûr : c'est
    l'approche recommandée pour la transition post-quantique.
    """
    def echange():
        # Partie classique (ECDH P-256)
        a = ec.generate_private_key(ec.SECP256R1())
        b = ec.generate_private_key(ec.SECP256R1())
        pub_a = a.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)
        pub_b = b.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)
        secret_ecdh = a.exchange(ec.ECDH(), b.public_key())
        # Partie post-quantique (ML-KEM-768)
        with oqs.KeyEncapsulation(KEM_PQ) as serveur:
            cle_pub_pq = serveur.generate_keypair()
            with oqs.KeyEncapsulation(KEM_PQ) as client:
                ciphertext, secret_pq_c = client.encap_secret(cle_pub_pq)
            secret_pq_s = serveur.decap_secret(ciphertext)
            assert secret_pq_c == secret_pq_s
        # Combinaison des deux secrets, puis HKDF
        HKDF(algorithm=hashes.SHA256(), length=16, salt=None,
             info=b"wifi-hybride").derive(secret_ecdh + secret_pq_s)
        octets = len(pub_a) + len(pub_b) + len(cle_pub_pq) + len(ciphertext)
        return octets

    octets, duree = chrono_ms(echange)
    return duree, octets


# ------------------------------------------------------------------------------
# Programme principal
# ------------------------------------------------------------------------------
def main():
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("-n", "--repetitions", type=int, default=1000,
                         help="nombre de répétitions par algorithme (défaut : 1000)")
    parseur.add_argument("--out-dir", default=os.path.join("..", "data"),
                         help="dossier de sortie des CSV (défaut : ../data)")
    parseur.add_argument("--chauffe", type=int, default=50,
                         help="répétitions de chauffe non mesurées (défaut : 50)")
    args = parseur.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(args.out_dir, f"crypto_benchmark_{horodatage}.csv")

    # Liste des algorithmes à mesurer.
    algos = [
        ("ECDH-P256", mesure_ecdh_p256),
        ("X25519",    mesure_x25519),
    ]
    # RSA : la paire de clés est générée une fois (hors mesure).
    print("Génération de la paire de clés RSA-2048 (une seule fois)...")
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pub = rsa_priv.public_key()
    algos.append(("RSA-2048", lambda: mesure_rsa2048(rsa_priv, rsa_pub)))

    if OQS_AVAILABLE and KEM_PQ in oqs.get_enabled_kem_mechanisms():
        algos.append(("ML-KEM-768", mesure_mlkem))
        algos.append(("ECDH-P256+ML-KEM-768", mesure_hybride))
        print(f"liboqs détecté : {KEM_PQ} inclus dans le benchmark.")
    else:
        print("ATTENTION : liboqs (oqs) indisponible ou ML-KEM-768 absent.")
        print("            La partie post-quantique est IGNORÉE.")
        print("            Installez-la avec :  pip install liboqs-python")

    infos = (f"python={platform.python_version()} "
             f"os={platform.system()}-{platform.release()} "
             f"machine={platform.machine()}")
    print(f"\nEnvironnement : {infos}")
    print(f"Répétitions mesurées : {args.repetitions} (+ {args.chauffe} de chauffe)\n")

    with open(chemin, "w", newline="", encoding="utf-8") as fichier:
        ecrivain = csv.writer(fichier)
        ecrivain.writerow(["timestamp", "algorithme", "iteration",
                           "temps_ms", "octets_reseau", "environnement"])

        for nom, fonction in algos:
            print(f"-> {nom} ...", end="", flush=True)
            # Phase de chauffe : les premières exécutions sont plus lentes
            # (allocation mémoire, cache). On les exécute mais on ne les garde pas.
            for _ in range(args.chauffe):
                fonction()
            # Phase mesurée
            for i in range(1, args.repetitions + 1):
                duree_ms, octets = fonction()
                ecrivain.writerow([
                    datetime.now(timezone.utc).isoformat(),
                    nom, i, f"{duree_ms:.6f}", octets, infos,
                ])
            print(" ok")

    print(f"\nTerminé. Données brutes : {chemin}")
    print(f"Analyse :  python3 analyze_results.py {chemin}")


if __name__ == "__main__":
    main()
