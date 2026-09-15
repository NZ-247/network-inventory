# Homelab Standardization Roadmap

Roadmap atualizado pelo baseline real de 15/09/2026. As etapas abaixo nao sao script de execucao; cada mudanca deve ter backup, janela e rollback.

## 1. Baseline atual

| Area | Estado |
| --- | --- |
| Gateway | RT-SN-003, RB750Gr3, RouterOS 6.49.18 long-term |
| Switch | SW-SN-03, WS-C2960XR-24PS-I, IOS 15.2(7)E14 |
| VLANs funcionais | 30 PROXMOX, 60 SERVICES, 90 MGMT, 130 GUESTs |
| Blackhole | VLAN 999 como native/blackhole no Cisco, sem SVI/L3 funcional |
| Uplink RB-Cisco | ether3-switch <-> Gi1/0/1, tagged 30/60/90/130, STP boundary |
| STP | Cisco PVST root; RouterOS bridge-core protocol-mode=none |

## 2. Concluido no baseline

| Item | Resultado |
| --- | --- |
| Cisco IOS | Validado em 15.2(7)E14; finding antigo de IOS removido. |
| VLANs legadas | VLANs legadas removidas do baseline atual do switch. |
| Trunks Proxmox | Gi1/0/3, Gi1/0/5, Gi1/0/6 e Gi1/0/15 padronizados com allowed 30,60 e native 999. |
| host0 | Gi1/0/15 validado em 1G apos troca de cabo. |
| LLDP/CDP | LLDP habilitado e CDP desabilitado no Cisco. |
| Web management Cisco | HTTP e HTTPS desabilitados. |
| SNMP Cisco | v3 authPriv com ACL SNMP_ZABBIX_ONLY; v1/v2c removidos. |
| NTP/DNS Cisco | NTP.br redundante e DNS via Pi-hole 10.100.60.71/72. |

## 3. Prioridades abertas

| Severidade | ID | Item | Proxima acao |
| --- | --- | --- | --- |
| CRITICAL | RB-FW-001 | RB input firewall: DROP GERAL disabled | Auditar /ip service print detail, restringir servicos administrativos e aplicar default-deny seguro em Safe Mode. |
| HIGH | RB-DHCP-001 | DHCP pools sobrepoem IPs estaticos | Separar faixas dinamicas das reservas/estaticos e revisar leases antes da mudanca. |
| HIGH | RB-FW-002 | RB forward policy sem default-deny explicito | Definir matriz de fluxos inter-VLAN e implantar default-deny gradual, preservando fluxos necessarios. |
| MEDIUM | RB-DNS-001 | DNS DHCP inconsistente entre VLANs | Definir politica DNS por VLAN; se Pi-hole for padrao, alinhar DHCP e NAT anti-bypass para as VLANs aplicaveis. |
| MEDIUM | RB-NTP-001 | RB NTP client disabled | Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba. |
| MEDIUM | RB-SNMP-001 | RB SNMP community difere da origem liberada no firewall | Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv. |

## 4. Revisao e limpeza

| Severidade | ID | Item | Proxima acao |
| --- | --- | --- | --- |
| REVIEW | RB-DISC-001 | Neighbor discovery usa lista invertida | Validar intencao no RouterOS antes de alterar; limitar descoberta somente onde for necessario. |
| LOW | RB-KNOCK-001 | Port-knocking popula rede-suporte sem accept correspondente | Revisar a intencao; concluir o fluxo de accept ou remover as regras orfas. |
| LOW | RB-POOL-001 | Pools DHCP legados aparentemente nao usados | Confirmar ausencia de dependencias e remover em mudanca separada. |
| LOW | SW-BANNER-001 | Cisco banner MOTD truncado/malformado | Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado. |
| LOW | SW-CLEAN-001 | Cisco ACL 10 orfa apos remocao do SNMPv2c | Remover ACL 10 apos confirmar que nao ha referencia remanescente. |

## 5. Mapa operacional de portas

| Porta | Uso | Modo | Allowed | Native | Speed |
| --- | --- | --- | --- | --- | --- |
| Gi1/0/1 | UPLINK_RT-SN-003 | trunk | 30,60,90,130 | 999 | 1G |
| Gi1/0/3 | PROXMOX_HOST2 | trunk | 30,60 | 999 | 1G |
| Gi1/0/5 | PROXMOX_HOST3 | trunk | 30,60 | 999 | 1G |
| Gi1/0/6 | PROXMOX_HOST1 | trunk | 30,60 | 999 | 1G |
| Gi1/0/7 | AP_GUEST_01_HUAWEI-BE3 | access | Nao determinado | Nao determinado | 1G |
| Gi1/0/10 | AP_GUEST_02_TPLink | access | Nao determinado | Nao determinado | 100M |
| Gi1/0/15 | PROXMOX_HOST0 | trunk | 30,60 | 999 | 1G |

## 6. Sequencia segura sugerida

1. Auditar `/ip service print detail` na RB e restringir management plane.
2. Ativar default-deny seguro no input da RB em Safe Mode.
3. Definir matriz inter-VLAN e aplicar default-deny forward gradual.
4. Redesenhar pools DHCP para nao sobrepor IPs estaticos.
5. Alinhar SNMP da RB ao Zabbix real e migrar para v3.
6. Habilitar NTP/SNTP na RB.
7. Unificar politica DNS/Pi-hole por VLAN.
8. Limpar ACL 10 e corrigir/remover banner MOTD no Cisco.

## 7. Guardrails

- Cisco remoto: backup, `reload in`, alteracao pequena, validacao, `reload cancel`, `write memory`.
- MikroTik remoto: export + backup, Safe Mode, alteracao pequena, validacao e saida limpa do Safe Mode.
- Nao adicionar segundo link L2 Cisco-RB sem redesign de STP, preferencialmente MSTP comum.
