# Network Inventory - Homelab

## 1. Baseline executivo

- Baseline pos-padronizacao validado em 15/09/2026.
- Gateway/L3: RT-SN-003 (RB750Gr3, RouterOS 6.49.18 long-term).
- Core L2: SW-SN-03 (WS-C2960XR-24PS-I, IOS 15.2(7)E14).
- VLANs funcionais: 30, 60, 90, 130; VLAN 999 e native/blackhole no Cisco.
- Uplink RB-Cisco: ether3-switch para Gi1/0/1, 802.1Q 30/60/90/130, native 999 no Cisco e RB tagged-only.
- Trunks Proxmox: Gi1/0/3 host2, Gi1/0/5 host3, Gi1/0/6 host1, Gi1/0/15 host0; allowed 30,60 e native 999.
- STP: Cisco PVST root para VLANs 30/60/90/130; RouterOS bridge-core protocol-mode=none. O enlace Cisco-RB e uma fronteira STP.
- Portas conectadas no switch: 7
- Hosts Proxmox mapeados no switch: 4/4
- Workloads Proxmox preservados do inventario PVE: 13
- Findings abertos: 1 critical, 2 high, 3 medium, 1 review, 4 low.

Fontes primarias: `Base_line-SW.txt` (running-config Cisco), `base_line-RT.rsc` (RouterOS export) e `network-baseline-2026-09-15.md` como criterio tecnico. Segredos, hashes, PPPoE user, SNMP communities/trap-community e e-mail foram redigidos antes de gravar artefatos.

## 2. MikroTik RT-SN-003

| Campo | Valor |
| --- | --- |
| Nome | RT-SN-003 |
| IP de gerenciamento preferencial | 10.100.90.1 |
| Modelo | hEX / RB750Gr3 |
| Serial | HHK0A0BXD64 |
| RouterOS | 6.49.18 long-term |
| Firmware atual/disponivel | Nao determinado / Nao determinado |
| WAN | PPPoE em ether1-Link-WaveMax; credencial redigida |
| Bridge | bridge-core vlan-filtering=yes frame-types=admit-only-vlan-tagged pvid=999 protocol-mode=none |
| Timezone | America/Cuiaba |
| NTP client | disabled |
| SNMP | enabled; community redigida; revisar migracao para v3 |

### VLANs roteadas / DHCP

| VLAN | Interface | Rede | Gateway | DHCP | Pool | Range | DNS entregue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30 | vlan30-proxmox-hosts | 10.100.30.0/24 | 10.100.30.1/24 | dhcp_proxmox | dhcp_pool7 | 10.100.30.2-10.100.30.254 | 1.1.1.1,8.8.8.8 |
| 60 | vlan60-services | 10.100.60.0/24 | 10.100.60.1/24 | dhcp_services | dhcp_pool8 | 10.100.60.2-10.100.60.254 | 1.1.1.1,8.8.8.8 |
| 90 | vlan90-MGMT | 10.100.90.0/24 | 10.100.90.1/24 | dhcp_gerencia | dhcp_pool11 | 10.100.90.2-10.100.90.254 | 1.1.1.1,8.8.8.8 |
| 130 | vlan130-guest_wifi | 10.100.130.0/24 | 10.100.130.1/24 | dhcp_guest | dhcp_pool5 | 10.100.130.2-10.100.130.254 | 10.100.60.71,10.100.60.72 |

### Bridge e trunk

| Bridge | VLAN | Tagged | Untagged |
| --- | --- | --- | --- |
| bridge-core | 90 | bridge-core,ether3-switch | ether2-PC_DN-06 |
| bridge-core | 30 | bridge-core,ether3-switch | Nao determinado |
| bridge-core | 60 | bridge-core,ether3-switch | Nao determinado |
| bridge-core | 130 | bridge-core,ether3-switch | Nao determinado |

## 3. Cisco SW-SN-03

| Campo | Valor |
| --- | --- |
| Hostname | SW-SN-03 |
| IP de gerenciamento | 10.100.90.99 |
| Gateway | 10.100.90.1 |
| Modelo | WS-C2960XR-24PS-I |
| Serial | FDO2213B011 |
| IOS | 15.2(7)E14 |
| Uptime | Nao determinado |
| LLDP | habilitado |
| CDP | desabilitado |
| HTTP/HTTPS | off / off |
| VTP | transparent |
| STP | PVST; priority 24576 for VLANs 30,60,90,130 |
| SSH | v2; ACL SSH_MGMT_ONLY |
| SNMP | v3 authPriv read-only via SNMP_ZABBIX_ONLY |
| DNS | Pi-hole 10.100.60.71 / 10.100.60.72 |
| NTP | a.ntp.br prefer + b.ntp.br + c.ntp.br; sincronizado |

### Portas do switch

| Porta | Descricao | Admin | Status | Modo | Access | Allowed | Native | Speed | PoE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gi1/0/1 | UPLINK_RT-SN-003 | enabled | connected | trunk | Nao determinado | 30,60,90,130 | 999 | 1G | auto |
| Gi1/0/2 | RESERVED_MGMT_EMERGENCY | shutdown | disabled | access | 90 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/3 | PROXMOX_HOST2 | enabled | connected | trunk | 999 | 30,60 | 999 | 1G | auto |
| Gi1/0/4 | RESERVED_PROXMOX | shutdown | disabled | trunk | 999 | 30,60 | 999 | auto | auto |
| Gi1/0/5 | PROXMOX_HOST3 | enabled | connected | trunk | 999 | 30,60 | 999 | 1G | auto |
| Gi1/0/6 | PROXMOX_HOST1 | enabled | connected | trunk | 999 | 30,60 | 999 | 1G | auto |
| Gi1/0/7 | AP_GUEST_01_HUAWEI-BE3 | enabled | connected | access | 130 | Nao determinado | Nao determinado | 1G | auto |
| Gi1/0/8 | RESERVED_AP_GUEST | shutdown | disabled | access | 130 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/9 | RESERVED_AP_GUEST | shutdown | disabled | access | 130 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/10 | AP_GUEST_02_TPLink | enabled | connected | access | 130 | Nao determinado | Nao determinado | 100M | auto |
| Gi1/0/11 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/12 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/13 | RESERVED_PROXMOX | shutdown | disabled | trunk | 999 | 30,60 | 999 | auto | auto |
| Gi1/0/14 | RESERVED_PROXMOX | shutdown | disabled | trunk | 999 | 30,60 | 999 | auto | auto |
| Gi1/0/15 | PROXMOX_HOST0 | enabled | connected | trunk | 999 | 30,60 | 999 | 1G | auto |
| Gi1/0/16 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/17 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/18 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/19 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/20 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/21 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/22 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/23 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/24 | UNUSED_BLACKHOLE | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | off |
| Gi1/0/25 | UNUSED_SFP | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/26 | UNUSED_SFP | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/27 | UNUSED_SFP | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | auto |
| Gi1/0/28 | UNUSED_SFP | shutdown | disabled | access | 999 | Nao determinado | Nao determinado | auto | auto |
| Fa0 | Nao determinado | shutdown | disabled | routed | Nao determinado | Nao determinado | Nao determinado | auto | auto |

## 4. VLANs e Subnets

| VLAN | Nome RouterOS | Nome Switch | Rede | Gateway |
| --- | --- | --- | --- | --- |
| 30 | vlan30-proxmox-hosts | PROXMOX | 10.100.30.0/24 | 10.100.30.1/24 |
| 60 | vlan60-services | SERVICES | 10.100.60.0/24 | 10.100.60.1/24 |
| 90 | vlan90-MGMT | MGMT | 10.100.90.0/24 | 10.100.90.1/24 |
| 130 | vlan130-guest_wifi | GUESTs | 10.100.130.0/24 | 10.100.130.1/24 |

### VLAN 999 / blackhole

A VLAN 999 existe no Cisco como native/blackhole para trunks e portas inutilizadas. Ela nao possui SVI/L3 funcional na RB no baseline atual.

## 5. Proxmox na rede

| Host | IP gerencia | MAC observado | Porta switch | VLAN observada |
| --- | --- | --- | --- | --- |
| host0 | 10.100.30.2 | Nao determinado | Gi1/0/15 | 30 |
| host1 | 10.100.30.3 | Nao determinado | Gi1/0/6 | 30 |
| host2 | 10.100.30.6 | Nao determinado | Gi1/0/3 | 30 |
| host3 | 10.100.30.9 | Nao determinado | Gi1/0/5 | 30 |

## 6. Workloads Proxmox - Rede

| ID | Nome | Tipo | Host | Status | IP | Bridge | VLAN config | VLAN efetiva | Porta observada | Porta do host | VLAN observada |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | Ubuntu-Server | VM | host1 | stopped | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 101 | Mine-Server | CT | host1 | stopped | 10.100.20.10/24 | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 102 | Nextcloud | VM | host1 | running | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 102 | Nextcloud | VM | host1 | running | Nao determinado | vmbr2 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/6 | Nao determinado |
| 103 | tailscale-vpn | VM | host1 | running | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 103 | tailscale-vpn | VM | host1 | running | Nao determinado | vmbr2 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/6 | Nao determinado |
| 104 | Page-ServicesNET | CT | host1 | running | 10.100.30.12/24 | vmbr0 | Nao determinado | 30 (inferido pelo IP) | Nao determinado | Gi1/0/6 | 30 |
| 106 | Interface-Web | CT | host1 | running | 10.100.60.16/24 | vmbr2 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/6 | 60 |
| 107 | CT107 | CT | host1 | running | 10.100.60.71/24 | vmbr2 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/6 | 60 |
| 109 | Zabbix-server | CT | host1 | running | 10.100.30.60/24 | vmbr0 | Nao determinado | 30 (inferido pelo IP) | Nao determinado | Gi1/0/6 | 30 |
| 105 | LAB-REDES | VM | host2 | stopped | Nao determinado | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | Nao determinado |
| 108 | PiHole-2 | CT | host2 | running | 10.100.60.72/24 | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | 60 |
| 110 | bot-server | CT | host2 | stopped | 10.100.60.20/24 | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | 60 |
| 111 | Pag-darling | CT | host2 | running | 10.100.60.80/24 | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | 60 |
| 112 | streaming | VM | host3 | stopped | Nao determinado | vmbr0 | 60 | 60 | Nao determinado | Gi1/0/5 | Nao determinado |

## 7. Findings abertos

| Severidade | ID | Finding | Evidencia | Recomendacao |
| --- | --- | --- | --- | --- |
| CRITICAL | RB-FW-001 | RB input firewall: DROP GERAL disabled | RouterOS export mostra chain=input action=drop comment="DROP GERAL" disabled=yes. | Auditar /ip service print detail, restringir servicos administrativos e aplicar default-deny seguro em Safe Mode. |
| HIGH | RB-DHCP-001 | DHCP pools sobrepoem IPs estaticos | dhcp_pool7 10.100.30.2-10.100.30.254: 10.100.30.12, 10.100.30.2, 10.100.30.26, 10.100.30.3, 10.100.30.4, 10.100.30.6, 10.100.30.60, 10.100.30.9; dhcp_pool8 10.100.60.2-10.100.60.254: 10.100.60.16, 10.100.60.20, 10.100.60.4, 10.100.60.71, 10.100.60.72, 10.100.60.80; dhcp_pool11 10.100.90.2-10.100.90.254: 10.100.90.99 | Separar faixas dinamicas das reservas/estaticos e revisar leases antes da mudanca. |
| HIGH | RB-FW-002 | RB forward policy sem default-deny explicito | Export contem accepts/fasttrack na chain forward, mas nao contem regra final drop/reject ativa. | Definir matriz de fluxos inter-VLAN e implantar default-deny gradual, preservando fluxos necessarios. |
| MEDIUM | RB-DNS-001 | DNS DHCP inconsistente entre VLANs | VLAN 30: 1.1.1.1,8.8.8.8, VLAN 60: 1.1.1.1,8.8.8.8, VLAN 90: 1.1.1.1,8.8.8.8, VLAN 130: 10.100.60.71,10.100.60.72 | Definir politica DNS por VLAN; se Pi-hole for padrao, alinhar DHCP e NAT anti-bypass para as VLANs aplicaveis. |
| MEDIUM | RB-NTP-001 | RB NTP client disabled | O export nao contem cliente NTP/SNTP ativo; o resumo tecnico valida NTP client desabilitado. | Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba. |
| MEDIUM | RB-SNMP-001 | RB SNMP community difere da origem liberada no firewall | Community addresses=10.100.0.6/32; firewall UDP/161 src-address=10.100.30.60. | Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv. |
| REVIEW | RB-DISC-001 | Neighbor discovery usa lista invertida | Export contem discover-interface-list=!interfaces-secure. | Validar intencao no RouterOS antes de alterar; limitar descoberta somente onde for necessario. |
| LOW | RB-KNOCK-001 | Port-knocking popula rede-suporte sem accept correspondente | Regras adicionam pre-rede-suporte/rede-suporte, mas o export nao mostra regra action=accept usando rede-suporte. | Revisar a intencao; concluir o fluxo de accept ou remover as regras orfas. |
| LOW | RB-POOL-001 | Pools DHCP legados aparentemente nao usados | Pools nao referenciados por DHCP servers ativos: dhcp_pool1, dhcp_pool4, dhcp_pool6, pool-wifi. | Confirmar ausencia de dependencias e remover em mudanca separada. |
| LOW | SW-BANNER-001 | Cisco banner MOTD truncado/malformado | running-config mostra banner motd com delimitador/texto truncado; banner login esta integro. | Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado. |
| LOW | SW-CLEAN-001 | Cisco ACL 10 orfa apos remocao do SNMPv2c | running-config ainda contem access-list 10 permit 10.100.30.60, enquanto SNMP usa SNMP_ZABBIX_ONLY. | Remover ACL 10 apos confirmar que nao ha referencia remanescente. |

## 8. Observacoes de relacionamento

- A RB RT-SN-003 chega ao switch pela porta Gi1/0/1, associada ao ether3-switch/bridge-core.
- VLANs 30, 60, 90 e 130 passam no trunk RB-Cisco; VLAN 999 e somente native/blackhole no Cisco.
- VLAN 130 aparece segmentada para AP/guest e nao aparece permitida nos trunks Proxmox.
- O export atual da RB nao traz ARP/MAC operacional; por isso os hosts PVE sao ligados as portas pelo baseline Cisco e os fatos PVE ja existentes.
- O comportamento do storage hd1tb visto no cluster Proxmox continua fora do escopo deste baseline de rede.

## 9. Arquivos de origem

- Fontes sanitizadas: `Base_line-SW.txt`, `base_line-RT.rsc`, `network-baseline-2026-09-15.md`
- Raw RouterOS sanitizado: `raw/routeros.stream` e `raw/routeros/*.txt`
- Raw switch sanitizado/derivado: `raw/switch.stream` e `raw/switch/*.txt`
- Dados tratados: `data/*.json`
- Topologia: `topology-current.md`
- Findings: `findings.md`
