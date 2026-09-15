# Current Network Topology

Baseline real de 15/09/2026. Mermaid usa apenas sintaxe suportada pelo GitHub.

## 1. Physical Topology

```mermaid
flowchart LR
  INTERNET["Internet / ISP"] -->|"PPPoE"| RB["RT-SN-003\nMikroTik RB750Gr3\nL3 Gateway"]
  RB -- "ether3-switch <-> Gi1/0/1\n802.1Q 30,60,90,130\nSTP boundary" --> SW["SW-SN-03\nWS-C2960XR-24PS-I\n10.100.90.99"]
  SW -- "Gi1/0/15 1G\ntrunk 30,60 native 999" --> H_host0["host0\n10.100.30.2"]
  SW -- "Gi1/0/6 1G\ntrunk 30,60 native 999" --> H_host1["host1\n10.100.30.3"]
  SW -- "Gi1/0/3 1G\ntrunk 30,60 native 999" --> H_host2["host2\n10.100.30.6"]
  SW -- "Gi1/0/5 1G\ntrunk 30,60 native 999" --> H_host3["host3\n10.100.30.9"]
  SW -- "Gi1/0/10 100M\naccess VLAN 130" --> AP_Gi1_0_10["02 TPLink\nGuest AP"]
  SW -- "Gi1/0/7 1G\naccess VLAN 130" --> AP_Gi1_0_7["01 HUAWEI-BE3\nGuest AP"]
```

## 2. VLAN / L3 Topology

```mermaid
flowchart TB
  RB["RT-SN-003\nGateway L3"]
  RB --> VLAN_30["VLAN 30\nvlan30-proxmox-hosts\n10.100.30.0/24"]
  VLAN_30 --> PVE["Proxmox hosts\nhost0-host3"]
  RB --> VLAN_60["VLAN 60\nvlan60-services\n10.100.60.0/24"]
  VLAN_60 --> SVC["Services / workloads"]
  RB --> VLAN_90["VLAN 90\nvlan90-MGMT\n10.100.90.0/24"]
  VLAN_90 --> MGMT["Management\nSwitch 10.100.90.99"]
  RB --> VLAN_130["VLAN 130\nvlan130-guest_wifi\n10.100.130.0/24"]
  VLAN_130 --> GUEST["Guest Wi-Fi / APs"]
```

## 3. Proxmox Bridges

```mermaid
flowchart TB
  SW["Cisco Switch"]
  SW --> PVE_host0["host0\n10.100.30.2"]
  PVE_host0 --> B_host0_vmbr0["vmbr0\nports: nic0\nvlan-aware: True"]
  SW --> PVE_host1["host1\n10.100.30.3"]
  PVE_host1 --> B_host1_vmbr1["vmbr1\nports: vlan90\nvlan-aware: True"]
  PVE_host1 --> B_host1_vmbr2["vmbr2\nports: vlan60\nvlan-aware: True"]
  PVE_host1 --> B_host1_vmbr0["vmbr0\nports: enp1s0\nvlan-aware: True"]
  SW --> PVE_host2["host2\n10.100.30.6"]
  PVE_host2 --> B_host2_vmbr2["vmbr2\nports: vlan90\nvlan-aware: False"]
  PVE_host2 --> B_host2_vmbr1["vmbr1\nports: vlan60\nvlan-aware: False"]
  PVE_host2 --> B_host2_vmbr0["vmbr0\nports: nic0\nvlan-aware: True"]
  SW --> PVE_host3["host3\n10.100.30.9"]
  PVE_host3 --> B_host3_vmbr0["vmbr0\nports: nic0\nvlan-aware: True"]
  PVE_host3 --> B_host3_vmbr1["vmbr1\nports: vlan60\nvlan-aware: False"]
```

## 4. Workloads

```mermaid
flowchart TB
  CL["Proxmox Workloads"]
  CL --> N_host0["host0"]
  CL --> N_host1["host1"]
  CL --> N_host2["host2"]
  CL --> N_host3["host3"]
  N_host1 --> W_100_Ubuntu_Server_vmbr0["VM 100 - Ubuntu-Server\nvmbr0 / VLAN Nao determinado\nIP Nao determinado"]
  N_host1 --> W_101_Mine_Server_vmbr0["CT 101 - Mine-Server\nvmbr0 / VLAN Nao determinado\nIP 10.100.20.10/24"]
  N_host1 --> W_102_Nextcloud_vmbr0["VM 102 - Nextcloud\nvmbr0 / VLAN Nao determinado\nIP Nao determinado"]
  N_host1 --> W_102_Nextcloud_vmbr2["VM 102 - Nextcloud\nvmbr2 / VLAN 60 via bridge\nIP Nao determinado"]
  N_host1 --> W_103_tailscale_vpn_vmbr0["VM 103 - tailscale-vpn\nvmbr0 / VLAN Nao determinado\nIP Nao determinado"]
  N_host1 --> W_103_tailscale_vpn_vmbr2["VM 103 - tailscale-vpn\nvmbr2 / VLAN 60 via bridge\nIP Nao determinado"]
  N_host1 --> W_104_Page_ServicesNET_vmbr0["CT 104 - Page-ServicesNET\nvmbr0 / VLAN 30 (inferido pelo IP)\nIP 10.100.30.12/24"]
  N_host1 --> W_106_Interface_Web_vmbr2["CT 106 - Interface-Web\nvmbr2 / VLAN 60 via bridge\nIP 10.100.60.16/24"]
  N_host1 --> W_107_CT107_vmbr2["CT 107 - CT107\nvmbr2 / VLAN 60 via bridge\nIP 10.100.60.71/24"]
  N_host1 --> W_109_Zabbix_server_vmbr0["CT 109 - Zabbix-server\nvmbr0 / VLAN 30 (inferido pelo IP)\nIP 10.100.30.60/24"]
  N_host2 --> W_105_LAB_REDES_vmbr1["VM 105 - LAB-REDES\nvmbr1 / VLAN 60 via bridge\nIP Nao determinado"]
  N_host2 --> W_108_PiHole_2_vmbr1["CT 108 - PiHole-2\nvmbr1 / VLAN 60 via bridge\nIP 10.100.60.72/24"]
  N_host2 --> W_110_bot_server_vmbr1["CT 110 - bot-server\nvmbr1 / VLAN 60 via bridge\nIP 10.100.60.20/24"]
  N_host2 --> W_111_Pag_darling_vmbr1["CT 111 - Pag-darling\nvmbr1 / VLAN 60 via bridge\nIP 10.100.60.80/24"]
  N_host3 --> W_112_streaming_vmbr0["VM 112 - streaming\nvmbr0 / VLAN 60\nIP Nao determinado"]
```

## 5. STP Boundary

O Cisco opera PVST e e root das VLANs 30/60/90/130. A bridge-core da RB opera `protocol-mode=none`; portanto o link RB-Cisco e uma fronteira STP. Nao adicionar segundo enlace L2 sem redesign/MSTP.
