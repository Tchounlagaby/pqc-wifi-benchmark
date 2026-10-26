#!/usr/bin/env bash
# =============================================================================
# create_users.sh
# -----------------------------------------------------------------------------
# À lancer SUR LE SERVEUR FreeRADIUS. Crée 50 utilisateurs de test
# (user1..user50, avec les mots de passe pass1..pass50) dans le fichier
# d'autorisation de FreeRADIUS, puis rappelle comment redémarrer le service.
#
# Une sauvegarde du fichier d'origine est créée (.bak).
#
# Usage :  ./create_users.sh [nombre_utilisateurs]
# =============================================================================
set -e
N="${1:-50}"
FICHIER=/etc/freeradius/3.0/mods-config/files/authorize

[ -f "$FICHIER" ] || { echo "Fichier introuvable : $FICHIER (FreeRADIUS est-il installé ?)"; exit 1; }
sudo cp "$FICHIER" "$FICHIER.bak"

for i in $(seq 1 "$N"); do
  echo "user$i Cleartext-Password := \"pass$i\""
done | sudo tee -a "$FICHIER" > /dev/null

echo "$N utilisateurs ajoutés (sauvegarde : $FICHIER.bak)."
echo "Redémarrez FreeRADIUS :  sudo systemctl restart freeradius"
echo "Pour déboguer :          sudo systemctl stop freeradius && sudo freeradius -X"
