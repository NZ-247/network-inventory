# Homelab Standardization Roadmap

Documento de trabalho para padronizar rede, Proxmox VE e operacao do homelab. Nenhuma acao foi executada neste roadmap; ele parte dos fatos coletados em `network-inventory.md` e `proxmox-inventory/inventory.md`.

## 1. Baseline Atual

| Area | Estado observado |
| --- | --- |
| Gateway | MikroTik RT-SN-003, RB750Gr3, RouterOS 6.49.18 |
| Switch | Cisco SW-SN-03, WS-C2960XR-24PS-I, IOS 15.2(2)E7 |
| Uplink RB -> Switch | RB `ether3-switch` para Cisco `Gi1/0/1`, trunk VLANs 30/60/90/130 |
| VLAN 30 | Proxmox hosts, `10.100.30.0/24`, gateway `10.100.30.1` |
| VLAN 60 | Services/workloads, `10.100.60.0/24`, gateway `10.100.60.1` |
| VLAN 90 | Management, `10.100.90.0/24`, gateway `10.100.90.1`, switch em `10.100.90.99` |
| VLAN 130 | Guest Wi-Fi, `10.100.130.0/24`, DNS entregue para Pi-hole `10.100.60.71/72` |
| Proxmox hosts | `host0` Gi1/0/15, `host1` Gi1/0/6, `host2` Gi1/0/3, `host3` Gi1/0/5 |
| Storage hd1tb | Storage Proxmox local/global, `shared=0`; montado de fato no `host1` |

## 2. Itens de Revisao Prioritarios

| Prioridade | Item | Evidencia | Motivo |
| --- | --- | --- | --- |
| Alta | Link do `host0` negociando a 100 Mbps | Cisco `Gi1/0/15` conectado em `a-100` | Pode limitar migracao do Nextcloud, backup, restore e trafego de servicos |
| Alta | `running-config` diferente de `startup-config` no switch | Inventario Cisco encontrou diferenca, especialmente em `Gi1/0/15` | Um reboot pode desfazer parte da configuracao atual |
| Media | Trunks Proxmox sem padrao unico | Native VLANs `1` e `30`; allowed VLANs `30,60` e `30,60,90` | Aumenta risco de comportamento diferente entre hosts |
| Media | Bridges Proxmox inconsistentes | `vmbr1`/`vmbr2` representam VLANs diferentes entre hosts | Dificulta automacao, playbooks e troubleshooting |
| Media | VLANs legadas no switch | VLANs 10, 20 e 369 sem L3 correspondente na RB | Podem ser reserva/teste, mas devem ser nomeadas ou removidas futuramente |
| Media | Ceph parcial no Proxmox | Pacotes/configuracao presentes, cluster nao operacional | Evita conclusoes erradas sobre storage distribuido |
| Alta | SMART ruim no `host3` | Inventario Proxmox marcou falha em `/dev/nvme0n1` | Risco de indisponibilidade local |

## 3. Padrao-Alvo Sugerido

Este padrao e uma proposta para discussao, nao uma configuracao aplicada.

| Tema | Padrao sugerido |
| --- | --- |
| Nomes de VLAN | Manter numeracao atual e documentar funcao: 30=PVE, 60=SERVICES, 90=MGMT, 130=GUEST |
| Trunks Proxmox | Definir um unico perfil por tipo de host: VLANs permitidas, native VLAN e descricao de porta |
| Gerencia Proxmox | Usar sempre o mesmo modelo: IP de host em VLAN 30 tagged via subinterface ou untagged/native, mas nao misturado |
| Bridges Proxmox | Padronizar nomes: `vmbr0` como trunk fisico VLAN-aware; bridges/subinterfaces por VLAN com significado igual em todos os hosts |
| Rede guest | Manter VLAN 130 fora dos trunks Proxmox salvo necessidade comprovada |
| Management | Restringir administracao de RB/switch/Proxmox a VLAN 90 ou a hosts explicitamente autorizados |
| DHCP/DNS | Centralizar nomes de pools, reservas e DNS por VLAN; registrar Pi-hole primario/secundario |
| Storage Proxmox | Separar storage local, storage de VM e storage de dados do Nextcloud com nomes que indiquem host/escopo |
| Documentacao | Atualizar `network-inventory` e `proxmox-inventory` apos cada mudanca real |

## 4. Sequencia Segura de Trabalho

### Fase 0 - Preparacao

- Fazer backup/export das configuracoes antes de qualquer mudanca real.
- Definir janela de manutencao para rede e Proxmox.
- Congelar nomes desejados de VLAN, bridges, storages e hosts.
- Confirmar se VLANs 10, 20 e 369 sao legado, reserva ou descarte.

### Fase 1 - Camada Fisica

- Resolver `Gi1/0/15` do `host0` negociando a 100 Mbps.
- Resolver ou justificar `Gi1/0/10` em 100 Mbps.
- Etiquetar cabos/portas conforme mapa:

| Porta | Uso atual | Observacao |
| --- | --- | --- |
| Gi1/0/1 | UPLINK_RT | Trunk para RB, VLANs 30/60/90/130 |
| Gi1/0/3 | host2 | Trunk Proxmox, VLANs 30/60/90, native 30 |
| Gi1/0/5 | host3 | Trunk Proxmox, VLANs 30/60/90, native 1 |
| Gi1/0/6 | host1 | Trunk Proxmox, VLANs 30/60/90, native 30 |
| Gi1/0/15 | host0 | Trunk Proxmox, VLANs 30/60, speed 100 Mbps observado |
| Gi1/0/7 | AP_GUEST | Access VLAN 130 |
| Gi1/0/10 | AP_GUEST | Access VLAN 130, speed 100 Mbps observado |

### Fase 2 - Padrao de VLAN/Trunk

- Escolher um dos modelos:
  - Gerencia Proxmox tagged: `vmbr0` trunk VLAN-aware e IP de host em `vmbr0.30`.
  - Gerencia Proxmox untagged: native VLAN 30 em todos os trunks Proxmox e IP direto na bridge.
- Evitar modelo misto, pois hoje ha native VLAN 1 e 30 em portas Proxmox.
- Decidir se VLAN 90 deve chegar aos hosts Proxmox para administracao, backup ou monitoramento.

### Fase 3 - Padrao de Bridges PVE

- Padronizar o significado de `vmbr1` e `vmbr2`.
- Sugestao de nomenclatura legivel:
  - `vmbr0`: bridge fisica trunk VLAN-aware.
  - `vmbr30`: rede de hosts/gerencia Proxmox, se bridge separada for usada.
  - `vmbr60`: rede de servicos.
  - `vmbr90`: rede de management, se necessaria nos hosts.
- Atualizar playbooks para nunca assumir que `vmbr1` significa a mesma VLAN em todos os hosts ate a padronizacao acontecer.

### Fase 4 - Storage e Nextcloud

- Tratar `hd1tb` como storage local do `host1`, nao como storage compartilhado.
- Renomear/segmentar storages futuramente para expressar escopo, por exemplo `host1-hd1tb-local` ou `host0-nc-mirror`.
- Antes da migracao do Nextcloud para `host0`, resolver o link de 100 Mbps e validar backup/restore.
- Para espelhamento temporario com dois discos, planejar pool/volume redundante fora deste inventario read-only.
- Para os 4 SAS no `host1` via HBA, documentar previamente se o alvo e capacidade, IOPS ou resiliencia.

### Fase 5 - Servicos, Backup e Operacao

- Definir onde ficam DNS/Pi-hole, Nextcloud, VPN/Tailscale, Zabbix e paginas.
- Criar politica simples de backup por workload critico.
- Documentar ordem de restauracao: DNS, gateway/gerencia, storage, Nextcloud, monitoramento.
- Usar Zabbix para alertar link a 100 Mbps, storage cheio, SMART ruim e hosts offline.

## 5. Decisoes Pendentes

| Decisao | Opcoes | Impacto |
| --- | --- | --- |
| Gerencia Proxmox tagged ou untagged | `vmbr0.30` em todos os hosts ou native VLAN 30 em todos os trunks | Define o padrao de switch e `/etc/network/interfaces` |
| VLAN 90 nos hosts Proxmox | Permitida nos trunks ou restrita ao switch/RB | Afeta administracao e isolamento |
| Nomes de bridges | `vmbr1/vmbr2` atuais ou nomes por VLAN | Afeta clareza, playbooks e migracoes |
| Storage Nextcloud temporario | Mirror no `host0` ou manter no `host1` ate HBA/SAS | Afeta janela de migracao e risco |
| Layout dos 4 SAS | Mirror pairs ou RAIDZ1/alternativa | Define capacidade util, resiliencia e performance |
| VLANs 10/20/369 | Manter, reservar, renomear ou remover futuramente | Reduz ambiguidade do switch |

## 6. Regra de Ouro

Nao usar este roadmap como script de execucao. Cada item deve virar uma mudanca pequena, com backup, janela e rollback definidos.
