# Network Inventory - Homelab

## 1. Executive Summary

- Router principal: RT-SN-003 (RB750Gr3, RouterOS 6.49.18 (long-term))
- Switch principal: SW-SN-03 (WS-C2960XR-24PS-I, IOS 15.2(2)E7)
- VLANs roteadas na RB: 30, 60, 90, 130
- Portas conectadas no switch: 7
- Hosts Proxmox mapeados no switch: 4/4
- Workloads Proxmox no inventario cruzado: 13
- Findings: 0 critical, 3 warnings, 12 total

Coleta feita em modo somente leitura. Credenciais, hashes e communities foram redigidos quando apareceram em saida de configuracao.

## 2. RouterBOARD / Gateway

| Campo | Valor |
| --- | --- |
| Nome | RT-SN-003 |
| IP de gerenciamento | 10.100.30.1 |
| Modelo | hEX / RB750Gr3 |
| Serial | HHK0A0BXD64 |
| RouterOS | 6.49.18 (long-term) |
| Firmware atual/disponivel | 6.49.17 / 6.49.18 |
| Uptime | 1w4d34m40s |
| CPU/RAM | MIPS 1004Kc V2.15 / 256.0MiB |

### VLANs roteadas pela RB

| VLAN | Interface | Rede | Gateway | DHCP | DNS entregue |
| --- | --- | --- | --- | --- | --- |
| 30 | vlan30-proxmox-hosts | 10.100.30.0/24 | 10.100.30.1/24 | dhcp_proxmox | 1.1.1.1,8.8.8.8 |
| 60 | vlan60-services | 10.100.60.0/24 | 10.100.60.1/24 | dhcp_services | 1.1.1.1,8.8.8.8 |
| 90 | vlan90-MGMT | 10.100.90.0/24 | 10.100.90.1/24 | dhcp_gerencia | 1.1.1.1,8.8.8.8 |
| 130 | vlan130-guest_wifi | 10.100.130.0/24 | 10.100.130.1/24 | dhcp_guest | 10.100.60.71,10.100.60.72 |

### Bridge e trunk

| Bridge | VLAN | Tagged | Untagged |
| --- | --- | --- | --- |
| bridge-core | 90 | bridge-core,ether3-switch | ether2-PC_DN-06 |
| bridge-core | 30 | bridge-core,ether3-switch | Nao determinado |
| bridge-core | 60 | bridge-core,ether3-switch | Nao determinado |
| bridge-core | 130 | bridge-core,ether3-switch | Nao determinado |

## 3. Cisco Switch

| Campo | Valor |
| --- | --- |
| Hostname | SW-SN-03 |
| IP de gerenciamento | 10.100.90.99 |
| Gateway | 10.100.90.1 |
| Modelo | WS-C2960XR-24PS-I |
| Serial | FDO2213B011 |
| IOS | 15.2(2)E7 |
| Uptime | 1 week, 4 days, 59 minutes |
| LLDP | desabilitado |

### Portas do switch

| Porta | Descricao | Status | Modo | VLAN operacional | Allowed VLANs | Native | Speed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gi1/0/1 | UPLINK_RT | connected | trunk | trunk | 30,60,90,130 | 1 | a-1000 |
| Gi1/0/2 | MGMT_ACCESS | notconnect | access | 90 | Nao determinado | Nao determinado | auto |
| Gi1/0/3 | PROXMOX_HOSTS | connected | trunk | trunk | 30,60,90 | 30 | a-1000 |
| Gi1/0/4 | PROXMOX_HOSTS | notconnect | trunk | 30 | 30,60,90 | 1 | auto |
| Gi1/0/5 | PROXMOX_HOSTS | connected | trunk | trunk | 30,60,90 | 1 | a-1000 |
| Gi1/0/6 | PROXMOX_HOSTS | connected | trunk | trunk | 30,60,90 | 30 | a-1000 |
| Gi1/0/7 | AP_GUEST | connected | access | 130 | Nao determinado | Nao determinado | a-1000 |
| Gi1/0/8 | AP_GUEST | notconnect | access | 130 | Nao determinado | Nao determinado | auto |
| Gi1/0/9 | AP_GUEST | notconnect | access | 130 | Nao determinado | Nao determinado | auto |
| Gi1/0/10 | AP_GUEST | connected | access | 130 | Nao determinado | Nao determinado | a-100 |
| Gi1/0/11 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/12 | teste-vlan60 | notconnect | access | 60 | Nao determinado | Nao determinado | auto |
| Gi1/0/13 | PROXMOX_HOSTS | notconnect | trunk | 1 | 30,60,90 | 1 | auto |
| Gi1/0/14 | PROXMOX_HOSTS | notconnect | trunk | 1 | 30,60,90 | 1 | auto |
| Gi1/0/15 | PROXMOX_HOST-0 | connected | trunk | trunk | 30,60 | 1 | a-100 |
| Gi1/0/16 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/17 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/18 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/19 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/20 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/21 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/22 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/23 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/24 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/25 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/26 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/27 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Gi1/0/28 | Nao determinado | notconnect | Nao determinado | 1 | Nao determinado | Nao determinado | auto |
| Fa0 | Nao determinado | disabled | Nao determinado | routed | Nao determinado | Nao determinado | auto |

## 4. VLANs e Subnets

| VLAN | Nome RouterOS | Nome Switch | Rede | Gateway |
| --- | --- | --- | --- | --- |
| 30 | vlan30-proxmox-hosts | PROXMOX | 10.100.30.0/24 | 10.100.30.1/24 |
| 60 | vlan60-services | SERVICES | 10.100.60.0/24 | 10.100.60.1/24 |
| 90 | vlan90-MGMT | MGMT | 10.100.90.0/24 | 10.100.90.1/24 |
| 130 | vlan130-guest_wifi | GUESTs | 10.100.130.0/24 | 10.100.130.1/24 |

## 5. Proxmox na rede

| Host | IP gerencia | MAC observado | Porta switch | VLAN observada |
| --- | --- | --- | --- | --- |
| host0 | 10.100.30.2 | 84:69:93:7E:7D:3A | Gi1/0/15 | 30 |
| host1 | 10.100.30.3 | D0:94:66:C6:75:02 | Gi1/0/6 | 30 |
| host2 | 10.100.30.6 | D0:94:66:C6:75:79 | Gi1/0/3 | 30 |
| host3 | 10.100.30.9 | D0:94:66:C6:31:5C | Gi1/0/5 | 30 |

## 6. Workloads Proxmox - Rede

| ID | Nome | Tipo | Host | Status | IP | Bridge | VLAN config | VLAN efetiva | Porta observada | Porta do host | VLAN observada |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | Ubuntu-Server | VM | host1 | stopped | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 101 | Mine-Server | CT | host1 | stopped | 10.100.20.10/24 | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 102 | Nextcloud | VM | host1 | running | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 102 | Nextcloud | VM | host1 | running | Nao determinado | vmbr2 | Nao determinado | 60 via bridge | Gi1/0/6 | Gi1/0/6 | 60 |
| 103 | tailscale-vpn | VM | host1 | running | Nao determinado | vmbr0 | Nao determinado | Nao determinado | Nao determinado | Gi1/0/6 | Nao determinado |
| 103 | tailscale-vpn | VM | host1 | running | Nao determinado | vmbr2 | Nao determinado | 60 via bridge | Gi1/0/6 | Gi1/0/6 | 60 |
| 104 | Page-ServicesNET | CT | host1 | running | 10.100.30.12/24 | vmbr0 | Nao determinado | 30 (inferido pelo IP) | Gi1/0/6 | Gi1/0/6 | 30 |
| 106 | Interface-Web | CT | host1 | running | 10.100.60.16/24 | vmbr2 | Nao determinado | 60 via bridge | Gi1/0/6 | Gi1/0/6 | 60 |
| 107 | CT107 | CT | host1 | running | 10.100.60.71/24 | vmbr2 | Nao determinado | 60 via bridge | Gi1/0/6 | Gi1/0/6 | 60 |
| 109 | Zabbix-server | CT | host1 | running | 10.100.30.60/24 | vmbr0 | Nao determinado | 30 (inferido pelo IP) | Gi1/0/6 | Gi1/0/6 | 30 |
| 105 | LAB-REDES | VM | host2 | stopped | Nao determinado | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | Nao determinado |
| 108 | PiHole-2 | CT | host2 | running | 10.100.60.72/24 | vmbr1 | Nao determinado | 60 via bridge | Gi1/0/3 | Gi1/0/3 | 60 |
| 110 | bot-server | CT | host2 | stopped | 10.100.60.20/24 | vmbr1 | Nao determinado | 60 via bridge | Nao determinado | Gi1/0/3 | 60 |
| 111 | Pag-darling | CT | host2 | running | 10.100.60.80/24 | vmbr1 | Nao determinado | 60 via bridge | Gi1/0/3 | Gi1/0/3 | 60 |
| 112 | streaming | VM | host3 | stopped | Nao determinado | vmbr0 | 60 | 60 | Nao determinado | Gi1/0/5 | Nao determinado |

## 7. Observacoes de relacionamento

- A RB RT-SN-003 chega ao switch pela porta Gi1/0/1, associada ao ether3-switch/bridge-core.
- VLANs 30, 60, 90 e 130 passam no trunk RB <-> switch.
- VLAN 130 aparece segmentada para AP/guest e nao aparece permitida nos trunks Proxmox coletados.
- MAC table e ARP permitem mapear hosts Proxmox ao switch; workloads desligados ou sem trafego recente podem ficar sem porta observada.
- O comportamento do storage hd1tb visto no cluster nao e compartilhamento de rede; e uma definicao local/global do Proxmox documentada no inventario anterior.

## 8. Arquivos de origem

- Raw RouterOS: `raw/routeros.stream` e `raw/routeros/*.txt`
- Raw switch: `raw/switch.stream` e `raw/switch/*.txt`
- Dados tratados: `data/*.json`
- Topologia: `topology-current.md`
- Findings: `findings.md`
