# UTILISATION DE LA CRYPTOGRAPHIE HYBRIDE POUR LA SÉCURITÉ DES DONNÉES EN TRANSIT DANS LES RÉSEAUX SANS FIL D’ENTREPRISE AU CAMEROUN 

Code et scripts pour reproduire les expériences de l'article :
**« A Lightweight Hybrid ECC–AES Security Architecture for Enterprise Wi-Fi in
Resource-Constrained Environments »** et son extension post-quantique.

Ce dépôt permet de :

1. **mesurer et comparer** les échanges de clés classiques (ECDH P-256, X25519,
   RSA-2048) et post-quantiques (ML-KEM-768, et l'hybride ECDH + ML-KEM) ;
2. **simuler des clients Wi-Fi d'entreprise** (802.1X / EAP-PEAP) contre un
   serveur FreeRADIUS, et mesurer le taux de réussite et la latence
   d'authentification ;
3. **analyser** les données brutes et **générer les figures** de l'article.

> Auteure : Gaby Béatrice Tchounla Nguenle — ENSPD, Université de Douala, Cameroun.

---

## 1. Contenu du dépôt

```
pqc-wifi-benchmark/
├── README.md                 ← ce fichier
├── LICENSE                   ← licence MIT
├── requirements.txt          ← dépendances Python
├── .gitignore
├── src/
│   ├── crypto_benchmark.py   ← mesure ECDH / X25519 / RSA / ML-KEM / hybride
│   ├── analyze_results.py    ← statistiques du benchmark (moyenne, écart-type…)
│   ├── make_figures.py       ← figures PNG pour l'article
│   ├── run_clients.sh        ← simule 50 clients 802.1X (eapol_test)
│   ├── create_users.sh       ← crée 50 utilisateurs de test sur FreeRADIUS
│   ├── peap_template.conf    ← modèle de config client EAP-PEAP
│   └── analyze_auth.py       ← statistiques d'authentification (taux, latence)
├── data/                     ← vos CSV de mesures (non versionnés)
└── figures/                  ← figures générées (non versionnées)
```

Les scripts **Python** portent la contribution scientifique (cryptographie,
analyse, figures). Les scripts **Bash** pilotent le banc de test réseau.

---

## 2. Installation

Nécessite **Python 3.9 ou plus**.

```bash
git clone https://github.com/<votre-compte>/pqc-wifi-benchmark.git
cd pqc-wifi-benchmark
python3 -m venv .venv && source .venv/bin/activate   # environnement isolé (conseillé)
pip install -r requirements.txt
```

> **Note sur liboqs (post-quantique).** Au tout premier `import oqs`, la
> bibliothèque `liboqs-python` compile la bibliothèque C `liboqs`, ce qui peut
> prendre quelques minutes et nécessite `cmake` et un compilateur C
> (`sudo apt install cmake gcc` sous Debian/Ubuntu/Kali). Si liboqs n'est pas
> disponible, `crypto_benchmark.py` fonctionne quand même et mesure uniquement
> les algorithmes classiques, en vous le signalant.

---

## 3. Utilisation rapide

### 3.1 Benchmark cryptographique (le cœur de l'article)

```bash
cd src
python3 crypto_benchmark.py -n 1000          # 1000 répétitions par algorithme
python3 analyze_results.py ../data/crypto_benchmark_*.csv
python3 make_figures.py ../data/resume_crypto.csv
```

- `crypto_benchmark.py` écrit un CSV horodaté dans `../data/` : une ligne par
  répétition (temps en ms, octets échangés).
- `analyze_results.py` calcule moyenne, écart-type, médiane, 95e centile, taille
  des messages et **surcoût par rapport à ECDH**, et enregistre un tableau
  (`resume_crypto.csv` et `resume_crypto.md`).
- `make_figures.py` produit deux figures en niveaux de gris dans `../figures/`.

### 3.2 Banc de test 802.1X (authentification)

Deux machines virtuelles conseillées : un **serveur** (Ubuntu + FreeRADIUS) et
un **client** (eapol_test). Tout peut aussi tourner sur une seule machine avec
`RADIUS_IP=127.0.0.1`.

**Sur le serveur :**

```bash
sudo apt install freeradius
./create_users.sh 50
# Ajouter le client dans /etc/freeradius/3.0/clients.conf :
#   client testbed { ipaddr = 192.168.56.0/24   secret = testing123 }
sudo systemctl restart freeradius        # ou, pour déboguer : sudo freeradius -X
```

**Sur le client :**

```bash
sudo apt install eapoltest
cd src
RADIUS_IP=192.168.56.10 ./run_clients.sh normal 5000 5       # fonctionnement normal
RADIUS_IP=192.168.56.10 ./run_clients.sh bruteforce 500 5    # mauvais mots de passe
python3 analyze_auth.py ../data/normal_auth_*.csv ../data/bruteforce_auth_*.csv
```

Le scénario `bruteforce` envoie de **mauvais mots de passe** : le serveur doit
les refuser. Il sert à vérifier que les **échecs d'authentification** sont bien
enregistrés et détectables. Toutes ces opérations se font sur **votre propre
banc de test**, isolé, à des fins de mesure.

> Mesure de charge additionnelle : l'outil standard `radclient`, fourni avec
> FreeRADIUS, permet d'envoyer un volume contrôlé de requêtes vers **votre**
> serveur pour observer son comportement sous charge. Voir `man radclient`.

---

## 4. Des données brutes aux résultats de l'article

| Étape | Commande | Produit |
| --- | --- | --- |
| Mesure crypto | `crypto_benchmark.py` | `data/crypto_benchmark_*.csv` |
| Statistiques | `analyze_results.py` | `data/resume_crypto.csv` et `.md` |
| Figures | `make_figures.py` | `figures/fig_temps.png`, `fig_octets.png` |
| Mesure auth | `run_clients.sh` | `data/*_auth_*.csv` |
| Statistiques auth | `analyze_auth.py` | affichage à l'écran |

**Conservez tous les fichiers de `data/`** : ce sont vos données brutes. Un
relecteur peut les demander. Reportez les valeurs de `resume_crypto.csv` et la
sortie de `analyze_auth.py` dans les tableaux de l'article.

---

## 5. Environnement de test (à adapter dans l'article)

- Serveur : FreeRADIUS 3.x sous Ubuntu 24.04 LTS (machine virtuelle).
- Client : eapol_test (wpa_supplicant) sous Kali Linux (machine virtuelle).
- Hyperviseur : VirtualBox, réseau privé hôte (host-only).
- Python 3.x, cryptography, liboqs-python.

Indiquez dans l'article le matériel réel (processeur, RAM) et le système, car
les temps mesurés en dépendent.

---

## 6. Licence

Code publié sous licence **MIT** (voir le fichier `LICENSE`). Vous pouvez le
réutiliser et le citer librement. Merci de citer l'article associé.
