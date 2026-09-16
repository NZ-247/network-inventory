# sep/15/2026 20:48:51 by RouterOS 6.49.18
# software id = GDDX-ALSL
#
# model = RB750Gr3
# serial number = HHK0A0BXD64
/interface bridge
add frame-types=admit-only-vlan-tagged ingress-filtering=yes name=bridge-core \
    pvid=999 vlan-filtering=yes
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
add name=MAC-RECOVERY
add name=DISCOVERY-UPLINK
/interface wireless security-profiles
set [ find default=yes ] supplicant-identity=MikroTik
/ip pool
add name=dhcp_pool8 ranges=10.100.60.100-10.100.60.254
add name=dhcp_pool11 ranges=10.100.90.100-10.100.90.105
add name=pool-wifi_guest ranges=10.100.130.40-10.100.130.254
/ip dhcp-server
add address-pool=pool-wifi_guest disabled=no interface=vlan130-guest_wifi \
    lease-time=1h name=dhcp_guest
add address-pool=dhcp_pool8 interface=vlan60-services lease-time=1h name=\
    dhcp_services
add address-pool=dhcp_pool11 interface=vlan90-MGMT lease-time=8h name=\
    dhcp_gerencia
/snmp community
add addresses=10.100.0.6/32 name=<REDACTED>
/interface bridge port
add bridge=bridge-core frame-types=admit-only-vlan-tagged ingress-filtering=\
    yes interface=ether3-switch pvid=999
add bridge=bridge-core frame-types=admit-only-untagged-and-priority-tagged \
    ingress-filtering=yes interface=ether2-PC_DN-06 pvid=90
/ip neighbor discovery-settings
set discover-interface-list=DISCOVERY-UPLINK protocol=lldp
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
add interface=ether2-PC_DN-06 list=MAC-RECOVERY
add interface=ether3-switch list=DISCOVERY-UPLINK
/ip address
add address=10.100.90.1/24 interface=vlan90-MGMT network=10.100.90.0
add address=10.100.30.1/24 interface=vlan30-proxmox-hosts network=10.100.30.0
add address=10.100.60.1/24 interface=vlan60-services network=10.100.60.0
add address=10.100.130.1/24 interface=vlan130-guest_wifi network=10.100.130.0
/ip dhcp-server lease
add address=10.100.130.139 client-id=1:f4:b3:1:94:35:90 mac-address=\
    F4:B3:01:94:35:90 server=dhcp_guest
add address=10.100.30.7 client-id=1:50:0:0:1:0:0 mac-address=\
    50:00:00:01:00:00
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
add address=10.100.30.4 comment="IP BKP VM Tailscale" list=rede-admin
add address=10.100.60.4 comment="IP VM Tailscale" list=rede-admin
add address=10.100.60.71 list=DNS
add address=10.100.60.72 list=DNS
add address=10.100.30.26 comment=TS-RESCUE list=rede-admin
/ip firewall filter
add action=accept chain=input comment="INPUT - ESTABLISHED RELATED" \
    connection-state=established,related
add action=drop chain=input comment="INPUT - DROP INVALID" connection-state=\
    invalid
add action=accept chain=input comment="INPUT - ADMIN VLAN90" in-interface=\
    vlan90-MGMT src-address=10.100.90.0/24
add action=accept chain=input comment="INPUT - ADMIN TS PRIMARY VLAN30" \
    in-interface=vlan30-proxmox-hosts src-address=10.100.30.4
add action=accept chain=input comment="INPUT - ADMIN TS HA VLAN30" \
    in-interface=vlan30-proxmox-hosts src-address=10.100.30.26
add action=accept chain=input comment="INPUT - ADMIN TS PRIMARY VLAN60" \
    in-interface=vlan60-services src-address=10.100.60.4
add action=accept chain=input comment="INPUT - DHCP GUEST" dst-port=67 \
    in-interface=vlan130-guest_wifi protocol=udp src-port=68
add action=accept chain=input comment="INPUT - SNMP ZABBIX" dst-port=161 \
    in-interface=vlan30-proxmox-hosts protocol=udp src-address=10.100.30.60
add action=accept chain=input comment="INPUT - ICMP LIMITED" limit=\
    50,5:packet protocol=icmp
add action=fasttrack-connection chain=forward comment=\
    "FORWARD - FASTTRACK EST REL" connection-state=established,related
add action=accept chain=forward comment="FORWARD - ESTABLISHED RELATED" \
    connection-state=established,related
add action=drop chain=forward comment="FORWARD - DROP INVALID" \
    connection-state=invalid
add action=accept chain=forward comment="FORWARD - MGMT ALL" in-interface=\
    vlan90-MGMT src-address=10.100.90.0/24
add action=accept chain=forward comment="FORWARD - ICMP FRAG NEEDED" \
    icmp-options=3:4 protocol=icmp
add action=drop chain=input comment="INPUT - DROP DEFAULT"
add action=accept chain=forward comment="GUEST - ALLOW DNS UDP" \
    dst-address-list=DNS dst-port=53 in-interface=vlan130-guest_wifi \
    protocol=udp
add action=accept chain=forward comment="GUEST - ALLOW DNS TCP" \
    dst-address-list=DNS dst-port=53 in-interface=vlan130-guest_wifi \
    protocol=tcp
add action=accept chain=forward comment="GUEST - ALLOW INTERNET" \
    in-interface=vlan130-guest_wifi out-interface=pppoe-Link-WaveMax
add action=drop chain=forward comment="GUEST - DROP INTERNAL" dst-address=\
    10.100.0.0/16 in-interface=vlan130-guest_wifi
add action=drop chain=forward comment="GUEST - DROP OTHER" in-interface=\
    vlan130-guest_wifi
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
set www disabled=yes
set ssh address=10.100.90.0/24,10.100.30.4/32,10.100.30.26/32,10.100.60.4/32
set api disabled=yes
set winbox address=\
    10.100.90.0/24,10.100.30.4/32,10.100.30.26/32,10.100.60.4/32
set api-ssl disabled=yes
/ip ssh
set strong-crypto=yes
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
set allowed-interface-list=none
/tool mac-server mac-winbox
set allowed-interface-list=MAC-RECOVERY
/tool mac-server ping
set enabled=no
