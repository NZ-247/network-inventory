# sep/15/2026 15:24:14 by RouterOS 6.49.18
# software id = GDDX-ALSL
#
# model = RB750Gr3
# serial number = HHK0A0BXD64
/interface bridge
add frame-types=admit-only-vlan-tagged ingress-filtering=yes name=bridge-core \
    protocol-mode=none pvid=999 vlan-filtering=yes
/interface ethernet
set [ find default-name=ether1 ] name=ether1-Link-WaveMax
set [ find default-name=ether2 ] name=ether2-PC_DN-06
set [ find default-name=ether3 ] name=ether3-switch
/interface pppoe-client
add add-default-route=yes disabled=no interface=ether1-Link-WaveMax name=\
    pppoe-Link-WaveMax use-peer-dns=yes user=<REDACTED>
/interface vlan
add interface=bridge-core name=vlan30-proxmox-hosts vlan-id=30
add interface=bridge-core name=vlan60-services vlan-id=60
add interface=bridge-core name=vlan90-MGMT vlan-id=90
add interface=bridge-core name=vlan130-guest_wifi vlan-id=130
/interface list
add name=interfaces-secure
/interface wireless security-profiles
set [ find default=yes ] supplicant-identity=MikroTik
/ip pool
add name=dhcp_pool1 ranges=10.100.10.10-10.100.255.254
add name=pool-wifi ranges=10.100.130.0-10.100.130.254
add name=dhcp_pool4 ranges=10.100.130.2-10.100.130.254
add name=dhcp_pool5 ranges=10.100.130.2-10.100.130.254
add name=dhcp_pool6 ranges=10.100.0.2-10.100.0.254
add name=dhcp_pool7 ranges=10.100.30.2-10.100.30.254
add name=dhcp_pool8 ranges=10.100.60.2-10.100.60.254
add name=dhcp_pool11 ranges=10.100.90.2-10.100.90.254
/ip dhcp-server
add address-pool=dhcp_pool5 disabled=no interface=vlan130-guest_wifi \
    lease-time=1h name=dhcp_guest
add address-pool=dhcp_pool7 disabled=no interface=vlan30-proxmox-hosts \
    lease-time=1h name=dhcp_proxmox
add address-pool=dhcp_pool8 disabled=no interface=vlan60-services lease-time=\
    1h name=dhcp_services
add address-pool=dhcp_pool11 disabled=no interface=vlan90-MGMT lease-time=8h \
    name=dhcp_gerencia
/snmp community
add addresses=10.100.0.6/32 name=<REDACTED>
/interface bridge port
add bridge=bridge-core frame-types=admit-only-vlan-tagged ingress-filtering=\
    yes interface=ether3-switch pvid=999
add bridge=bridge-core frame-types=admit-only-untagged-and-priority-tagged \
    ingress-filtering=yes interface=ether2-PC_DN-06 pvid=90
/ip neighbor discovery-settings
set discover-interface-list=!interfaces-secure
/interface bridge vlan
add bridge=bridge-core tagged=bridge-core,ether3-switch untagged=\
    ether2-PC_DN-06 vlan-ids=90
add bridge=bridge-core tagged=bridge-core,ether3-switch vlan-ids=30
add bridge=bridge-core tagged=bridge-core,ether3-switch vlan-ids=60
add bridge=bridge-core tagged=bridge-core,ether3-switch vlan-ids=130
/interface list member
add interface=ether3-switch list=interfaces-secure
add interface=ether2-PC_DN-06 list=interfaces-secure
add interface=vlan90-MGMT list=interfaces-secure
/ip address
add address=10.100.90.1/24 interface=vlan90-MGMT network=10.100.90.0
add address=10.100.30.1/24 interface=vlan30-proxmox-hosts network=10.100.30.0
add address=10.100.60.1/24 interface=vlan60-services network=10.100.60.0
add address=10.100.130.1/24 interface=vlan130-guest_wifi network=10.100.130.0
/ip dhcp-server lease
add address=10.100.130.139 client-id=1:f4:b3:1:94:35:90 mac-address=\
    F4:B3:01:94:35:90 server=dhcp_guest
add address=10.100.30.7 client-id=1:50:0:0:1:0:0 mac-address=\
    50:00:00:01:00:00 server=dhcp_proxmox
/ip dhcp-server network
add address=10.100.30.0/24 dns-server=1.1.1.1,8.8.8.8 domain=services.net.br \
    gateway=10.100.30.1
add address=10.100.60.0/24 dns-server=1.1.1.1,8.8.8.8 domain=services.net.br \
    gateway=10.100.60.1
add address=10.100.90.0/24 dns-server=1.1.1.1,8.8.8.8 domain=services.net.br \
    gateway=10.100.90.1
add address=10.100.130.0/24 dns-server=10.100.60.71,10.100.60.72 domain=\
    services.net.br gateway=10.100.130.1
/ip dns
set servers=8.8.8.8,1.1.1.1
/ip firewall address-list
add address=10.100.90.0/24 list=rede-admin
add address=10.100.130.139 comment="DN-06 Via WI-FI" list=rede-admin
add address=10.100.30.4 comment="IP BKP VM Tailscale" list=rede-admin
add address=10.100.60.4 comment="IP VM Tailscale" list=rede-admin
add address=10.100.60.71 list=DNS
add address=10.100.60.72 list=DNS
add address=10.100.30.26 comment=TS-RESCUE list=rede-admin
/ip firewall filter
add action=fasttrack-connection chain=forward comment="Ativa FastTrack" \
    connection-state=established,related
add action=accept chain=input comment=Rede-Admin src-address-list=rede-admin
add action=accept chain=forward comment=\
    "Permite tr\E1fego passar no FastTrack" connection-state=\
    established,related
add action=accept chain=input comment="Allow full access from MGMT VLAN" \
    in-interface=vlan90-MGMT
add action=accept chain=forward comment="MGMT -> ALL" in-interface=\
    vlan90-MGMT src-address=10.100.90.0/24
add action=accept chain=input comment=\
    "Aceita conex\F5es estabelecidas ou relacionadas" connection-state=\
    established,related
add action=accept chain=input comment="Aceita 50 packages ICMP/S" limit=\
    50,5:packet protocol=icmp
add action=accept chain=input comment="Libera SMNP para Zabbix" dst-port=161 \
    protocol=udp src-address=10.100.30.60
add action=accept chain=forward comment="Permitir ICMP Frag Needed" \
    icmp-options=3:4 protocol=icmp
add action=accept chain=input comment="Permitir Frag Needed para o Mikrotik" \
    icmp-options=3:4 protocol=icmp
add action=add-src-to-address-list address-list=pre-rede-suporte \
    address-list-timeout=3s chain=input comment="Pega IP para pre-rede-Admin" \
    dst-port=3399 protocol=tcp
add action=add-src-to-address-list address-list=rede-suporte \
    address-list-timeout=5h chain=input comment="Pega IP para rede Admin" \
    dst-port=6699 protocol=tcp src-address-list=pre-rede-suporte
add action=drop chain=input comment="DROP GERAL" disabled=yes
/ip firewall nat
add action=masquerade chain=srcnat out-interface=pppoe-Link-WaveMax
add action=dst-nat chain=dstnat comment="For\E7a DNS Pi-Hole" \
    dst-address-list=!DNS dst-port=53 protocol=tcp src-address=\
    10.100.130.0/24 to-addresses=10.100.60.71
add action=dst-nat chain=dstnat dst-address-list=!DNS dst-port=53 protocol=\
    udp src-address=10.100.130.0/24 to-addresses=10.100.60.71
add action=accept chain=dstnat src-address-list=DNS
/ip service
set telnet disabled=yes
set ftp disabled=yes
set api disabled=yes
set api-ssl disabled=yes
/snmp
set contact=<REDACTED_EMAIL> enabled=yes location=Homelab \
    trap-community=<REDACTED> trap-generators=\
    temp-exception,start-trap,interfaces trap-interfaces=all
/system clock
set time-zone-name=America/Cuiaba
/system identity
set name=RT-SN-003
/system note
set note="\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \n\r\
    \nSSSSSS    EEEEEEE  RRRRRR   V       V  III  CCCCCCC  EEEEEEE  SSSSSS\r\
    \nSS        EE       RR   RR  V       V  III  CC       EE      SS\r\
    \nSSSSS     EEEEE    RRRRRR    V     V   III  CC       EEEEE    SSSSS\r\
    \n    SS    EE       RR  RR     V   V    III  CC       EE           SS\r\
    \nSSSSSS    EEEEEEE  RR   RR     VVV     III  CCCCCCC  EEEEEEE  SSSSSS\r\
    \n\r\
    \n                 SERVICES.NET\r\
    \n\r\
    \n=================================================================\r\
    \n ACESSO RESTRITO - SERVICES.NET\r\
    \n\r\
    \n Este sistema e de uso exclusivo de usuarios autorizados.\r\
    \n As atividades realizadas podem ser monitoradas e registradas\r\
    \n para fins de seguranca, auditoria e conformidade legal.\r\
    \n\r\
    \n O uso nao autorizado e proibido e podera resultar em medidas\r\
    \n administrativas, civis e penais, conforme legislacao vigente,\r\
    \n incluindo a Lei Geral de Protecao de Dados (LGPD - Lei 13.709).\r\
    \n\r\
    \n Ao prosseguir, voce declara estar ciente e de acordo.\r\
    \n================================================================="
/system package update
set channel=long-term
/tool mac-server
set allowed-interface-list=interfaces-secure
/tool mac-server mac-winbox
set allowed-interface-list=interfaces-secure
