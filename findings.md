# Network Findings

Findings atuais do baseline 15/09/2026. Findings legados sobre IOS antigo, link host0 degradado, VLANs removidas, web management Cisco, password-encryption, LLDP, trunks inconsistentes e running/startup divergente foram retirados por nao refletirem o baseline atual.

## [CRITICAL] RB-FW-001 - RB input firewall: DROP GERAL disabled

- Evidencia: RouterOS export mostra chain=input action=drop comment="DROP GERAL" disabled=yes.
- Impacto: Sem drop final ativo, trafego ao plano de controle da RB que nao casa com regras anteriores pode ser aceito por padrao.
- Recomendacao: Auditar /ip service print detail, restringir servicos administrativos e aplicar default-deny seguro em Safe Mode.

## [HIGH] RB-DHCP-001 - DHCP pools sobrepoem IPs estaticos

- Evidencia: dhcp_pool7 10.100.30.2-10.100.30.254: 10.100.30.12, 10.100.30.2, 10.100.30.26, 10.100.30.3, 10.100.30.4, 10.100.30.6, 10.100.30.60, 10.100.30.9; dhcp_pool8 10.100.60.2-10.100.60.254: 10.100.60.16, 10.100.60.20, 10.100.60.4, 10.100.60.71, 10.100.60.72, 10.100.60.80; dhcp_pool11 10.100.90.2-10.100.90.254: 10.100.90.99
- Impacto: DHCP pode entregar endereco ja usado por PVE, Tailscale, Zabbix, Pi-hole, switch ou gateways.
- Recomendacao: Separar faixas dinamicas das reservas/estaticos e revisar leases antes da mudanca.

## [HIGH] RB-FW-002 - RB forward policy sem default-deny explicito

- Evidencia: Export contem accepts/fasttrack na chain forward, mas nao contem regra final drop/reject ativa.
- Impacto: VLANs separam L2, mas nao provam isolamento L3 entre redes quando forward fica aceito por padrao.
- Recomendacao: Definir matriz de fluxos inter-VLAN e implantar default-deny gradual, preservando fluxos necessarios.

## [MEDIUM] RB-DNS-001 - DNS DHCP inconsistente entre VLANs

- Evidencia: VLAN 30: 1.1.1.1,8.8.8.8, VLAN 60: 1.1.1.1,8.8.8.8, VLAN 90: 1.1.1.1,8.8.8.8, VLAN 130: 10.100.60.71,10.100.60.72
- Impacto: VLANs 30/60/90 usam DNS publico enquanto VLAN130 usa Pi-hole e anti-bypass, dificultando observabilidade e politica unica.
- Recomendacao: Definir politica DNS por VLAN; se Pi-hole for padrao, alinhar DHCP e NAT anti-bypass para as VLANs aplicaveis.

## [MEDIUM] RB-NTP-001 - RB NTP client disabled

- Evidencia: O export nao contem cliente NTP/SNTP ativo; o resumo tecnico valida NTP client desabilitado.
- Impacto: Relogio sem sincronismo confiavel prejudica correlacao de logs e auditoria.
- Recomendacao: Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba.

## [MEDIUM] RB-SNMP-001 - RB SNMP community difere da origem liberada no firewall

- Evidencia: Community addresses=10.100.0.6/32; firewall UDP/161 src-address=10.100.30.60.
- Impacto: O poller real pode nao casar com a community ou a regra pode permitir uma origem diferente da pretendida.
- Recomendacao: Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv.

## [REVIEW] RB-DISC-001 - Neighbor discovery usa lista invertida

- Evidencia: Export contem discover-interface-list=!interfaces-secure.
- Impacto: A expressao parece inversa ao nome da lista e pode expor descoberta em interfaces nao administrativas.
- Recomendacao: Validar intencao no RouterOS antes de alterar; limitar descoberta somente onde for necessario.

## [LOW] RB-KNOCK-001 - Port-knocking popula rede-suporte sem accept correspondente

- Evidencia: Regras adicionam pre-rede-suporte/rede-suporte, mas o export nao mostra regra action=accept usando rede-suporte.
- Impacto: O fluxo de suporte pode estar incompleto ou apenas acumulando listas sem efeito pratico.
- Recomendacao: Revisar a intencao; concluir o fluxo de accept ou remover as regras orfas.

## [LOW] RB-POOL-001 - Pools DHCP legados aparentemente nao usados

- Evidencia: Pools nao referenciados por DHCP servers ativos: dhcp_pool1, dhcp_pool4, dhcp_pool6, pool-wifi.
- Impacto: Residuos aumentam ambiguidade operacional e risco de reuso indevido.
- Recomendacao: Confirmar ausencia de dependencias e remover em mudanca separada.

## [LOW] SW-BANNER-001 - Cisco banner MOTD truncado/malformado

- Evidencia: running-config mostra banner motd com delimitador/texto truncado; banner login esta integro.
- Impacto: Nao afeta encaminhamento, mas deixa a configuracao administrativa inconsistente.
- Recomendacao: Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado.

## [LOW] SW-CLEAN-001 - Cisco ACL 10 orfa apos remocao do SNMPv2c

- Evidencia: running-config ainda contem access-list 10 permit 10.100.30.60, enquanto SNMP usa SNMP_ZABBIX_ONLY.
- Impacto: Configuracao residual aumenta ruido e pode confundir auditorias futuras.
- Recomendacao: Remover ACL 10 apos confirmar que nao ha referencia remanescente.
