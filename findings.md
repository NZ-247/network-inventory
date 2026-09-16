# Network Findings

Findings atuais do baseline 15/09/2026. Findings legados sobre IOS antigo, link host0 degradado, VLANs removidas, web management Cisco, password-encryption, LLDP, trunks inconsistentes e running/startup divergente foram retirados por nao refletirem o baseline atual.

## [HIGH] RB-FW-002 - RB forward policy parcial; sem default-deny global

- Status: PARTIAL / IN PROGRESS
- Evidencia: VLAN130 possui politica de zona explicita.
- Impacto: A zona Guest ja esta isolada, mas VLAN30 PROXMOX e VLAN60 SERVICES ainda precisam de matriz inter-zonas antes de um default-deny global.
- Recomendacao: Mapear fluxos 30<->60, definir matriz completa e implementar default-deny global da chain forward de forma gradual.

## [MEDIUM] RB-NTP-001 - RB NTP client disabled

- Status: OPEN
- Evidencia: O export nao contem cliente NTP/SNTP ativo; o resumo tecnico valida NTP client desabilitado.
- Impacto: Relogio sem sincronismo confiavel prejudica correlacao de logs e auditoria.
- Recomendacao: Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba.

## [MEDIUM] RB-PWR-001 - Reboot nao planejado / shutdown incorreto na RT-SN-003

- Status: OPEN
- Evidencia: Log observed: system,error,critical router rebooted without proper shutdown, probably power outage.
- Impacto: Gateway central pode ter sofrido interrupcao nao limpa; isso aumenta risco de indisponibilidade e perda de estado volatil.
- Recomendacao: Verificar alimentacao/fonte, avaliar UPS/nobreak e monitorar novos eventos de reboot inesperado no Zabbix.

## [MEDIUM] RB-SNMP-001 - RB SNMP community difere da origem liberada no firewall

- Status: OPEN
- Evidencia: Community addresses=10.100.0.6/32; firewall UDP/161 src-address=10.100.30.60.
- Impacto: O poller real pode nao casar com a community ou a regra pode permitir uma origem diferente da pretendida.
- Recomendacao: Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv.

## [REVIEW] RB-DNS-HA-001 - DNS anti-bypass Guest sem HA efetivo

- Status: OPEN
- Evidencia: DHCP GUEST entrega 10.100.60.71, 10.100.60.72, mas DNAT TCP/UDP 53 redireciona somente para 10.100.60.71.
- Impacto: Se o Pi-hole primario ficar indisponivel, clientes com resolver manual externo continuam redirecionados para o primario indisponivel.
- Recomendacao: Avaliar estrategia de HA para o DNAT DNS da VLAN130 ou documentar dependencia do Pi-hole primario.

## [LOW] RB-DHCP-CLEAN-001 - Limpeza DHCP residual pendente

- Status: OPEN
- Evidencia: Servidores disabled: dhcp_gerencia, dhcp_services; pools sem servidor ativo: dhcp_pool11, dhcp_pool8; leases orfas: 10.100.30.7.
- Impacto: Residuos de DHCP nao representam colisao ativa, mas aumentam ruido operacional e risco de reuso equivocado.
- Recomendacao: Remover servidores disabled, pools nao usados, network definitions sem servidor ativo e lease orfa apos confirmar ausencia de dependencias.

## [LOW] SW-BANNER-001 - Cisco banner MOTD truncado/malformado

- Status: OPEN
- Evidencia: running-config mostra banner motd com delimitador/texto truncado; banner login esta integro.
- Impacto: Nao afeta encaminhamento, mas deixa a configuracao administrativa inconsistente.
- Recomendacao: Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado.

## [LOW] SW-CLEAN-001 - Cisco ACL 10 orfa apos remocao do SNMPv2c

- Status: OPEN
- Evidencia: running-config ainda contem access-list 10 permit 10.100.30.60, enquanto SNMP usa SNMP_ZABBIX_ONLY.
- Impacto: Configuracao residual aumenta ruido e pode confundir auditorias futuras.
- Recomendacao: Remover ACL 10 apos confirmar que nao ha referencia remanescente.
