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
| RB management plane | IP services administrativos restritos; SSH strong-crypto; HTTP/API/Telnet/FTP desativados. |
| RB MAC management | MAC Telnet e MAC Ping desativados; MAC-Winbox somente em ether2-PC_DN-06 via MAC-RECOVERY. |
| RB discovery | LLDP somente no uplink ether3-switch via DISCOVERY-UPLINK. |
| RB firewall input | Default-deny explicito com accepts restritos para MGMT/Tailscale, DHCP guest, SNMP Zabbix e ICMP limitado. |
| RB DHCP operacional | Somente VLAN130 GUEST possui DHCP ativo, com pool 10.100.130.40-10.100.130.254. |
| RB Guest zone | VLAN130 permite DNS para Pi-hole e Internet via PPPoE; bloqueia redes internas 10.100.0.0/16 e demais destinos. |
| RB DNS anti-bypass GUEST | DNAT TCP/UDP 53 da VLAN130 para Pi-hole primario 10.100.60.71. |

## 3. Prioridades abertas

| Severidade | Status | ID | Item | Proxima acao |
| --- | --- | --- | --- | --- |
| HIGH | PARTIAL / IN PROGRESS | RB-FW-002 | RB forward policy parcial; sem default-deny global | Mapear fluxos 30<->60, definir matriz completa e implementar default-deny global da chain forward de forma gradual. |
| MEDIUM | OPEN | RB-NTP-001 | RB NTP client disabled | Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba. |
| MEDIUM | OPEN | RB-PWR-001 | Reboot nao planejado / shutdown incorreto na RT-SN-003 | Verificar alimentacao/fonte, avaliar UPS/nobreak e monitorar novos eventos de reboot inesperado no Zabbix. |
| MEDIUM | OPEN | RB-SNMP-001 | RB SNMP community difere da origem liberada no firewall | Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv. |

## 4. Revisao e limpeza

| Severidade | Status | ID | Item | Proxima acao |
| --- | --- | --- | --- | --- |
| REVIEW | OPEN | RB-DNS-HA-001 | DNS anti-bypass Guest sem HA efetivo | Avaliar estrategia de HA para o DNAT DNS da VLAN130 ou documentar dependencia do Pi-hole primario. |
| LOW | OPEN | RB-DHCP-CLEAN-001 | Limpeza DHCP residual pendente | Remover servidores disabled, pools nao usados, network definitions sem servidor ativo e lease orfa apos confirmar ausencia de dependencias. |
| LOW | OPEN | SW-BANNER-001 | Cisco banner MOTD truncado/malformado | Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado. |
| LOW | OPEN | SW-CLEAN-001 | Cisco ACL 10 orfa apos remocao do SNMPv2c | Remover ACL 10 apos confirmar que nao ha referencia remanescente. |

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

1. Mapear dependencias VLAN30 PROXMOX <-> VLAN60 SERVICES.
2. Definir matriz completa inter-zonas.
3. Implementar default-deny global da chain forward de forma gradual.
4. Migrar SNMP da MikroTik para SNMPv3 authPriv.
5. Habilitar NTP/SNTP na RB.
6. Revisar HA do DNS anti-bypass da VLAN130.
7. Remover residuos DHCP.
8. Monitorar alimentacao/reboots inesperados.
9. Limpar ACL 10 orfa no Cisco.
10. Corrigir/remover banner MOTD Cisco.

## 7. Guardrails

- Cisco remoto: backup, `reload in`, alteracao pequena, validacao, `reload cancel`, `write memory`.
- MikroTik remoto: export + backup, Safe Mode, alteracao pequena, validacao e saida limpa do Safe Mode.
- Nao adicionar segundo link L2 Cisco-RB sem redesign de STP, preferencialmente MSTP comum.
