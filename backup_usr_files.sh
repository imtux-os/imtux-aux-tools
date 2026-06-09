#!/bin/bash
# =====================
# Backup User Files
# =====================
# 
# Este programa tem como função de monitorar os arquivos criados e modificados pelo usuário e
# os copiar para a unidade montada em TEMP_DEVICE_MOUNT, a qual foi escolhida pelo usuário em sto_dev_out_sel.py
#
# O programa é chamado no serviço onstart-autosave.servicee, o qual precisa ser salvo em ~/.config/systemd/user/onstart-autosave.service.
# Desta forma, o programa roda após login do usuário.

python3 /home/vboxuser/Desktop/PI/sto_dev_out_sel.py
export TEMP_DEVICE_MOUNT=$(cat /tmp/temp_device_mount)
echo $TEMP_DEVICE_MOUNT
# É necessário instalar o pacte inotify-tools
if [ -n "$TEMP_DEVICE_MOUNT" ]; then
    inotifywait -m -r -e close_write,moved_to \
        --exclude '(\.cache|\.local/state|/snap/|CachedData|workspaceStorage|\.tmp$|-journal$|-[0-9]+\.js$)' \
        --format "%w%f" "$HOME"  |
    while IFS= read -r filepath; do
        rsync -a --relative --ignore-missing-args $filepath "$TEMP_DEVICE_MOUNT"
    done
fi