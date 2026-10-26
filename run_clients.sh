#!/usr/bin/env bash
# =============================================================================
# run_clients.sh
# -----------------------------------------------------------------------------
# Simule des clients Wi-Fi d'entreprise (802.1X / EAP-PEAP) qui s'authentifient
# en boucle auprès d'un serveur FreeRADIUS, à l'aide de l'outil `eapol_test`
# (fourni par wpa_supplicant / paquet `eapoltest`).
#
# Deux scénarios, pour vos PROPRES expériences sur votre PROPRE banc de test :
#   normal     -> bons identifiants  (fonctionnement normal, mesure du taux de
#                 réussite et de la latence)
#   bruteforce -> mauvais mots de passe (le serveur doit les REFUSER ; sert à
#                 vérifier que les échecs d'authentification sont bien détectés)
#
# Chaque exécution écrit un fichier CSV horodaté dans ../data.
# NE SUPPRIMEZ PAS ces fichiers : ce sont vos données brutes.
#
# Analyse ensuite avec :
#   python3 analyze_auth.py ../data/normal_auth_*.csv ../data/bruteforce_auth_*.csv
#
# Usage :
#   ./run_clients.sh <scenario> <nb_tentatives> [nb_clients_simultanes]
# Exemples :
#   RADIUS_IP=127.0.0.1    ./run_clients.sh normal 10 1       # petit test
#   RADIUS_IP=192.168.56.10 ./run_clients.sh normal 5000 5    # campagne
#   RADIUS_IP=192.168.56.10 ./run_clients.sh bruteforce 500 5
# =============================================================================
set -u

RADIUS_IP="${RADIUS_IP:-127.0.0.1}"     # IP du serveur FreeRADIUS
SECRET="${SECRET:-testing123}"          # secret partagé (clients.conf du serveur)
NB_USERS="${NB_USERS:-50}"              # nombre d'utilisateurs user1..userN
SCENARIO="${1:-normal}"
N="${2:-1000}"
WORKERS="${3:-5}"

DIR="$(cd "$(dirname "$0")" && pwd)"
OUTDIR="$DIR/../data"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/${SCENARIO}_auth_$(date +%Y%m%d_%H%M%S).csv"
TMP="$(mktemp -d)"
TEMPLATE="$DIR/peap_template.conf"

command -v eapol_test >/dev/null || { echo "eapol_test introuvable : sudo apt install eapoltest"; exit 1; }
[ -f "$TEMPLATE" ] || { echo "Modèle introuvable : $TEMPLATE"; exit 1; }

echo "timestamp,client,user,scenario,result,latency_ms" > "$OUT"

une_tentative() {
  local w=$1 u pass conf t0 t1 res
  u=$(( (RANDOM % NB_USERS) + 1 ))
  pass="pass$u"
  [ "$SCENARIO" = "bruteforce" ] && pass="wrong$RANDOM"     # mot de passe erroné
  conf="$TMP/client$w.conf"
  sed -e "s/__USER__/user$u/" -e "s/__PASS__/$pass/" "$TEMPLATE" > "$conf"
  t0=$(date +%s%N)
  if eapol_test -c "$conf" -a "$RADIUS_IP" -s "$SECRET" -r0 -t 10 >/dev/null 2>&1; then
    res=SUCCESS
  else
    res=FAILURE
  fi
  t1=$(date +%s%N)
  echo "$(date -Iseconds),$w,user$u,$SCENARIO,$res,$(( (t1 - t0) / 1000000 ))"
}

client() {
  local w=$1 k=$2 i
  for ((i = 0; i < k; i++)); do une_tentative "$w"; done > "$TMP/out$w.csv"
}

PAR_CLIENT=$(( (N + WORKERS - 1) / WORKERS ))
echo "Scénario : $SCENARIO | serveur : $RADIUS_IP | $((PAR_CLIENT * WORKERS)) tentatives | $WORKERS clients -> $OUT"
for ((w = 1; w <= WORKERS; w++)); do client "$w" "$PAR_CLIENT" & done
wait
cat "$TMP"/out*.csv >> "$OUT"
rm -rf "$TMP"
echo "Terminé. Analyse :  python3 analyze_auth.py $OUT"
