# Network Findings

## [WARNING] Running-config do switch difere do startup-config

- Evidencia: O running-config tem alteracao posterior ao NVRAM update; Gi1/0/15 aparece com allowed VLANs diferente entre running e startup.
- Impacto: Apos reboot do switch, parte da configuracao atual pode voltar ao estado anterior.
- Recomendacao: Revisar a diferenca e decidir, fora desta coleta read-only, se deve salvar ou ajustar a configuracao.

## [WARNING] Porta Gi1/0/10 conectada a 100 Mbps

- Evidencia: Gi1/0/10 (AP_GUEST) esta connected com speed a-100.
- Impacto: Pode limitar a capacidade de clientes ligados a esse AP ou enlace guest.
- Recomendacao: Validar cabo, porta, autonegociacao e NIC quando for fazer janela de manutencao.

## [WARNING] Porta Gi1/0/15 conectada a 100 Mbps

- Evidencia: Gi1/0/15 (PROXMOX_HOST-0) esta connected com speed a-100.
- Impacto: Pode limitar trafego do host0; isso importa especialmente em migracoes e servicos com disco/rede mais intensivos.
- Recomendacao: Validar cabo, porta, autonegociacao e NIC quando for fazer janela de manutencao.

## [REVIEW] VLANs existem no switch sem interface L3 correspondente no RouterOS

- Evidencia: VLANs no switch nao roteadas/coletadas na RB: 10, 20, 369.
- Impacto: Pode ser legado/teste, mas aumenta ambiguidade durante padronizacao.
- Recomendacao: Confirmar se devem permanecer, ser documentadas como reserva ou removidas em mudanca planejada.

## [REVIEW] Trunks Proxmox com native/allowed VLANs diferentes

- Evidencia: Native VLANs vistas: 1, 30; allowed VLANs vistas: 30,60, 30,60,90.
- Impacto: Nao e necessariamente erro no homelab, mas pode causar comportamento diferente entre hosts.
- Recomendacao: Padronizar trunk por perfil de host ou registrar explicitamente excecoes.

## [REVIEW] Ranges dos pools DHCP nao foram comprovados

- Evidencia: A consulta /ip pool print detail marcou timeout nesta coleta.
- Impacto: DHCP server, redes, gateway e DNS foram coletados, mas ranges exatos dos pools ficam pendentes.
- Recomendacao: Coletar novamente em janela separada se os ranges forem decisivos para o playbook.

## [REVIEW] HTTP/HTTPS habilitados no switch

- Evidencia: running-config contem ip http server e ip http secure-server.
- Impacto: Pode ser aceitavel em homelab, mas e superficie administrativa adicional.
- Recomendacao: Revisar politica de gerenciamento na VLAN 90 durante a padronizacao.

## [REVIEW] Switch com no service password-encryption

- Evidencia: running-config contem no service password-encryption; secrets foram redigidos no inventario.
- Impacto: Pode expor senhas tipo 0/7 se forem adicionadas futuramente.
- Recomendacao: Revisar hardening de configuracao em etapa propria.

## [REVIEW] Acesso SSH ao switch dependeu de algoritmos legados

- Evidencia: Coleta do switch exigiu diffie-hellman-group14-sha1/ssh-rsa e o ssh-keyscan retornou apenas banner, sem chave RSA utilizavel.
- Impacto: Nao muda a topologia, mas e ponto de seguranca/operabilidade para automacao futura.
- Recomendacao: Planejar revisao de firmware/ciphers/SSH do switch quando houver janela, sem misturar com inventario read-only.

## [INFO] LLDP desabilitado no switch

- Evidencia: show lldp neighbors retornou que LLDP nao esta habilitado; CDP esta ativo e viu a RB.
- Impacto: Topologia multi-vendor depende mais de CDP/MAC table/ARP do que de LLDP.
- Recomendacao: Opcionalmente avaliar LLDP em momento separado, se fizer sentido para descoberta automatica.

## [INFO] Firmware RouterBOARD diferente da versao disponivel

- Evidencia: current-firmware=6.49.17 upgrade-firmware=6.49.18.
- Impacto: Nao afeta diretamente a topologia atual; e um ponto de manutencao.
- Recomendacao: Avaliar upgrade de firmware em manutencao planejada, nunca dentro de inventario read-only.

## [INFO] hd1tb e um storage local definido globalmente no Proxmox, nao um compartilhamento de rede

- Evidencia: Inventario Proxmox mostra hd1tb como dir em /mnt/pve/hd1tb, shared=0, montado de fato no host1.
- Impacto: A aparencia de 'disco em todos os hosts' vem da configuracao clusterizada do Proxmox, nao do switch/RB.
- Recomendacao: Para espelhamento/migracao do Nextcloud, tratar isso no desenho de storage Proxmox/ZFS/LVM, separado da rede.
