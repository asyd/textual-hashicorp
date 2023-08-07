#!/bin/sh

VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root

export VAULT_ADDR 
export VAULT_TOKEN

apk add -U pwgen

sleep 1

for env in devel staging production ; do
  vault kv put secret/${env}/db/access login=${env} secret=$(pwgen 16 1)
  vault kv put secret/${env}/broker/access login=${env} secret=$(pwgen 16 1)
  vault kv put secret/${env}/mail/access login=${env} secret=$(pwgen 16 1) port=587
done
