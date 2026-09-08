# Nextcloud Storage and Network Notes

Notas tecnicas para orientar a futura migracao do Nextcloud e a reorganizacao do storage. Este arquivo e deliberadamente read-only: descreve fatos, riscos e decisoes, sem comandos de alteracao.

## 1. Estado Atual Comprovado

| Item | Estado |
| --- | --- |
| Workload | VM `102` - `Nextcloud` |
| Host atual | `host1` |
| Rede observada | Interfaces em `vmbr0` e `vmbr2`; `vmbr2` corresponde a VLAN 60 no `host1` |
| Porta fisica do host atual | Switch `Gi1/0/6`, trunk VLANs 30/60/90, 1 Gbps |
| Storage relevante | `hd1tb`, Proxmox type `dir`, path `/mnt/pve/hd1tb` |
| Backing real do `hd1tb` | Montado de fato no `host1` a partir de `/dev/sda1` ext4 |
| Compartilhamento | `hd1tb` nao e shared storage; `shared=0` no Proxmox |

## 2. Interpretacao do `hd1tb`

O comportamento de o storage aparecer nos demais hosts vem do fato de o `storage.cfg` ser clusterizado no Proxmox. Isso nao significa que o disco esteja realmente compartilhado pela rede.

Na pratica:

```text
Storage ID hd1tb
  -> definido no cluster Proxmox
  -> path /mnt/pve/hd1tb em todos os nos
  -> backing real comprovado apenas no host1
  -> nao e NFS/CIFS/Ceph/iSCSI/shared storage
```

Para padronizacao, o nome ideal do storage deveria deixar claro o escopo local, por exemplo `host1-hd1tb-local`, se essa for a decisao futura.

## 3. Ponto Critico Para Migrar Para o host0

O `host0` esta na porta Cisco `Gi1/0/15`, observada a `100 Mbps`. Antes de mover Nextcloud para ele, esse ponto merece revisao.

Impactos possiveis:

- Backup/restore e migracao ficam mais lentos.
- Upload/download de arquivos do Nextcloud podem ficar limitados.
- Sincronizacoes de clientes podem parecer instaveis sob carga.
- Um futuro storage redundante local no `host0` pode ficar subutilizado por gargalo de rede.

## 4. Perguntas de Arquitetura Antes da Mudanca

| Pergunta | Por que importa |
| --- | --- |
| O Nextcloud deve ficar permanentemente no `host0` ou apenas ate chegada da HBA/SAS no `host1`? | Define se vale investir mais no desenho local do `host0` |
| Os dois HDDs no `host0` serao dedicados somente ao Nextcloud? | Evita misturar workload, backup e dados antigos |
| Existe dado antigo/BitLocker/LVM nos discos candidatos? | O inventario detectou discos antigos; nao devem ser tocados sem confirmacao |
| O objetivo dos 4 SAS no `host1` e capacidade ou IOPS/resiliencia? | Mirror pairs e RAIDZ1 entregam compromissos diferentes |
| O banco/config do Nextcloud fica no mesmo disco dos dados? | Afeta performance e restauracao |
| Como sera feito backup externo ao mirror? | Mirror protege contra falha de disco, nao contra exclusao, ransomware ou erro humano |

## 5. Opcoes de Storage Futuro

| Opcao | Uso possivel | Vantagens | Pontos de atencao |
| --- | --- | --- | --- |
| Dois HDDs em mirror no `host0` | Etapa temporaria ou ambiente definitivo pequeno | Redundancia simples; facil de entender | Host0 hoje esta a 100 Mbps; confirmar discos limpos antes |
| 4 SAS em mirror pairs no `host1` | Nextcloud com foco em IOPS e resiliencia | Boa performance aleatoria; resiliencia por par | Menos capacidade util |
| 4 SAS em RAIDZ1 | Nextcloud com foco em capacidade | Mais capacidade util que mirror pairs | Menos IOPS; rebuild mais sensivel |
| Storage compartilhado real | HA/migracao com menos acoplamento ao host | Flexibilidade operacional | Exige desenho extra: NFS/iSCSI/Ceph/ZFS replication |

## 6. Sequencia Recomendada de Validacao

1. Corrigir ou justificar link do `host0` em 100 Mbps.
2. Confirmar quais discos serao usados e quais contem dados antigos.
3. Definir layout de redundancia e nome padrao do storage.
4. Confirmar backup completo e restauravel do Nextcloud atual.
5. Testar restauracao em VM temporaria ou ambiente isolado, se possivel.
6. Planejar janela de migracao.
7. Atualizar inventarios apos a mudanca real.

## 7. Relacao com a Rede

Para o Nextcloud, a rede atual mais relevante e:

```text
Internet/Clientes
  -> RT-SN-003
  -> VLAN 60 services
  -> Switch SW-SN-03
  -> Host Proxmox
  -> VM 102 Nextcloud
```

Hoje a VLAN 60 esta presente nos trunks Proxmox principais, mas os perfis de trunk nao estao 100% padronizados. Para reduzir surpresa em migracoes, padronizar VLANs permitidas/native VLAN antes de movimentar workloads criticos e uma boa proxima etapa.
