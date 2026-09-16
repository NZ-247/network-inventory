# Network Inventory

Inventario da infraestrutura de rede do homelab com baseline pos-padronizacao validado em 15/09/2026.

O estado atual foi regenerado a partir do running-config Cisco `SW-SN-03`, do snapshot RouterOS pos-hardening `baseline-guest-zone.rsc`, do export historico `base_line-RT.rsc` e do resumo tecnico `network-baseline-2026-09-15.md`. Quando houver conflito, `baseline-guest-zone.rsc` prevalece para fatos da MikroTik. Os raw/configs publicados foram sanitizados antes de serem gravados.

## Arquivos principais

- `network-inventory.md`: documentacao tecnica principal.
- `topology-current.md`: diagramas Mermaid de topologia.
- `findings.md`: inconsistencias, riscos e itens de revisao.
- `inventory.csv`: endpoints, hosts e workloads em formato tabular.
- `data/validated-overrides.json`: evidencias validadas pelo operador que nao aparecem no export RouterOS.
- `data/`: JSONs tratados.
- `raw/`: saidas brutas redigidas.

## Escopo

O baseline cobre RB MikroTik, switch Cisco, VLANs, trunks, management plane e relacao com dados ja inventariados do Proxmox. Nenhum comando de alteracao foi executado por este gerador.
