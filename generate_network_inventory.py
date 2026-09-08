#!/usr/bin/env python3
from __future__ import annotations

import csv
import ipaddress
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
PROXMOX_DATA = ROOT.parent / "proxmox-inventory" / "data"
NA = "Nao determinado"


def clean_text(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = text.replace("\r", "")
    text = re.sub(r"^Script started.*\n", "", text, flags=re.M)
    text = re.sub(r"^Script done.*\n?", "", text, flags=re.M)
    return text


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return clean_text(path.read_text(errors="replace"))


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def norm_mac(mac: str | None) -> str:
    if not mac:
        return NA
    mac = mac.strip()
    if re.fullmatch(r"[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}", mac):
        raw = mac.replace(".", "")
        mac = ":".join(raw[i : i + 2] for i in range(0, 12, 2))
    mac = mac.replace("-", ":").upper()
    parts = [p.zfill(2) for p in mac.split(":") if p]
    if len(parts) == 6 and all(re.fullmatch(r"[0-9A-F]{2}", p) for p in parts):
        return ":".join(parts)
    return mac.upper()


def kv_pairs(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"([\w-]+)=(\"[^\"]*\"|'[^']*'|[^ \t\n]+)", blob):
        value = m.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[m.group(1)] = value
    return out


def colon_pairs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = re.sub(r"\s+", "_", key.strip().lower())
        if key:
            out[key] = value.strip()
    return out


def detail_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("Flags:"):
            continue
        if line.startswith("###"):
            continue
        if re.match(r"^\s*\d+\s+", line):
            if cur:
                blocks.append(cur)
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        blocks.append(cur)

    parsed: list[dict[str, Any]] = []
    for block in blocks:
        flat = " ".join(part.strip() for part in block if part.strip())
        m = re.match(r"^(\d+)\s+([A-Z ]*?)\s*(.*)$", flat)
        if not m:
            continue
        item = kv_pairs(m.group(3))
        item["_index"] = int(m.group(1))
        item["_flags"] = re.sub(r"\s+", "", m.group(2).strip())
        parsed.append(item)
    return parsed


def extract_router_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        begin = re.match(r"^### NETINV_BEGIN path=(.+)$", line)
        end = re.match(r"^### NETINV_END path=(.+)$", line)
        if begin:
            current = begin.group(1).strip()
            buf = []
            continue
        if end:
            if current:
                sections[current] = list(buf)
            current = None
            buf = []
            continue
        if current and not line.startswith("### NETINV_COMMAND"):
            buf.append(line)
    return {path: "\n".join(lines).strip() for path, lines in sections.items()}


def safe_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "item"


def short_if(name: str | None) -> str:
    if not name:
        return NA
    return (
        name.replace("GigabitEthernet", "Gi")
        .replace("FastEthernet", "Fa")
        .replace("TenGigabitEthernet", "Te")
        .strip()
    )


def parse_router(raw_text: str) -> dict[str, Any]:
    sections = extract_router_sections(raw_text)
    for rel_path, content in sections.items():
        write_text(RAW / rel_path, content or "# No output captured")

    identity = colon_pairs(sections.get("routeros/system_identity.txt", ""))
    resource = colon_pairs(sections.get("routeros/system_resource.txt", ""))
    routerboard = colon_pairs(sections.get("routeros/system_routerboard.txt", ""))
    interfaces = detail_blocks(sections.get("routeros/interface_print_detail.txt", ""))
    bridge_ports = detail_blocks(sections.get("routeros/interface_bridge_port_print_detail.txt", ""))
    bridge_vlans = detail_blocks(sections.get("routeros/interface_bridge_vlan_print_detail.txt", ""))
    bridge_hosts = detail_blocks(sections.get("routeros/interface_bridge_host_print_detail.txt", ""))
    vlan_interfaces = detail_blocks(sections.get("routeros/interface_vlan_print_detail.txt", ""))
    addresses = detail_blocks(sections.get("routeros/ip_address_print_detail.txt", ""))
    routes = detail_blocks(sections.get("routeros/ip_route_print_detail.txt", ""))
    dhcp_servers = detail_blocks(sections.get("routeros/ip_dhcp_server_print_detail.txt", ""))
    dhcp_networks = detail_blocks(sections.get("routeros/ip_dhcp_server_network_print_detail.txt", ""))
    dhcp_leases = detail_blocks(sections.get("routeros/ip_dhcp_server_lease_print_detail.txt", ""))
    arp = detail_blocks(sections.get("routeros/ip_arp_print_detail.txt", ""))
    ip_services = detail_blocks(sections.get("routeros/ip_service_print_detail.txt", ""))
    address_lists = detail_blocks(sections.get("routeros/ip_firewall_address_list_print_detail.txt", ""))

    for rows in (interfaces, bridge_hosts, dhcp_leases, arp):
        for row in rows:
            for key in ("mac-address", "active-mac-address"):
                if key in row:
                    row[key] = norm_mac(row[key])

    address_by_interface = {a.get("interface"): a for a in addresses if a.get("interface")}
    dhcp_by_network = {d.get("address"): d for d in dhcp_networks if d.get("address")}
    server_by_interface = {d.get("interface"): d for d in dhcp_servers if d.get("interface")}

    vlans: list[dict[str, Any]] = []
    for vlan in vlan_interfaces:
        iface = vlan.get("name", NA)
        ip_addr = address_by_interface.get(iface, {})
        network = ip_addr.get("address", "")
        network_key = ip_addr.get("network", "")
        if network_key and "/" not in network_key:
            prefix = network.split("/", 1)[1] if "/" in network else ""
            network_key = f"{network_key}/{prefix}" if prefix else network_key
        dhcp_network = dhcp_by_network.get(network_key, {})
        vlans.append(
            {
                "id": vlan.get("vlan-id", NA),
                "name": iface,
                "parent": vlan.get("interface", NA),
                "gateway": ip_addr.get("address", NA),
                "network": network_key or NA,
                "dhcp_server": server_by_interface.get(iface, {}).get("name", NA),
                "dhcp_pool": server_by_interface.get(iface, {}).get("address-pool", NA),
                "dhcp_dns": dhcp_network.get("dns-server", NA),
                "domain": dhcp_network.get("domain", NA),
            }
        )

    return {
        "device": {
            "name": identity.get("name", NA),
            "platform": resource.get("platform", "MikroTik"),
            "board_name": resource.get("board-name", routerboard.get("board-name", NA)),
            "model": routerboard.get("model", NA),
            "serial": routerboard.get("serial-number", NA),
            "routeros_version": resource.get("version", NA),
            "firmware_current": routerboard.get("current-firmware", NA),
            "firmware_available": routerboard.get("upgrade-firmware", NA),
            "uptime": resource.get("uptime", NA),
            "cpu": resource.get("cpu", NA),
            "memory_total": resource.get("total-memory", NA),
            "management_ip": "10.100.30.1",
        },
        "interfaces": interfaces,
        "bridge_ports": bridge_ports,
        "bridge_vlans": bridge_vlans,
        "bridge_hosts": bridge_hosts,
        "vlans": vlans,
        "ip_addresses": addresses,
        "routes": routes,
        "dns": colon_pairs(sections.get("routeros/ip_dns_print.txt", "")),
        "dhcp_servers": dhcp_servers,
        "dhcp_networks": dhcp_networks,
        "dhcp_leases": dhcp_leases,
        "arp": arp,
        "ip_services": ip_services,
        "address_lists": address_lists,
        "collection_warnings": [
            "Comando /ip pool print detail marcou timeout; pools aparecem referenciados pelos DHCP servers, mas os ranges nao foram comprovados nesta coleta."
            if "NETINV_TIMEOUT" in sections.get("routeros/ip_pool_print_detail.txt", "")
            else "",
            "Comandos /routing table print detail e /routing route print detail nao existem no RouterOS 6.49; rotas foram coletadas por /ip route print detail."
            if "bad command name" in sections.get("routeros/routing_table_print_detail.txt", "")
            else "",
        ],
    }


def extract_switch_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^([A-Za-z0-9_.-]+#)([^\n]+)$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        command = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if not command:
            continue
        sections[command] = text[start:end].strip()
        write_text(RAW / "switch" / f"{safe_name(command)}.txt", sections[command] or "# No output captured")
    return sections


def parse_interface_config(config: str) -> dict[str, dict[str, Any]]:
    ports: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r"(?ms)^interface\s+(.+?)\n(.*?)(?=^!$|^interface\s+|\Z)", config):
        full = match.group(1).strip()
        body = match.group(2)
        key = short_if(full)
        desc = re.search(r"^\s*description\s+(.+)$", body, flags=re.M)
        mode = re.search(r"^\s*switchport mode\s+(\S+)", body, flags=re.M)
        access = re.search(r"^\s*switchport access vlan\s+(\d+)", body, flags=re.M)
        allowed = re.search(r"^\s*switchport trunk allowed vlan\s+(.+)$", body, flags=re.M)
        native = re.search(r"^\s*switchport trunk native vlan\s+(\d+)", body, flags=re.M)
        ports[key] = {
            "interface": key,
            "full_interface": full,
            "description": desc.group(1).strip() if desc else "",
            "mode": mode.group(1).strip() if mode else NA,
            "access_vlan": access.group(1) if access else NA,
            "trunk_allowed_vlans": allowed.group(1).strip() if allowed else NA,
            "native_vlan": native.group(1) if native else ("1" if mode and mode.group(1) == "trunk" else NA),
            "native_vlan_explicit": bool(native),
            "shutdown": bool(re.search(r"^\s*shutdown$", body, flags=re.M)),
            "portfast": bool(re.search(r"^\s*spanning-tree portfast", body, flags=re.M)),
        }
    return ports


def parse_status(text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        m = re.match(
            r"^(Gi\S+|Fa\S+|Te\S+)\s+(.*?)\s{2,}(connected|notconnect|disabled|err-disabled|inactive)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$",
            line,
        )
        if not m:
            continue
        rows[m.group(1)] = {
            "interface": m.group(1),
            "name": m.group(2).strip(),
            "status": m.group(3),
            "vlan": m.group(4),
            "duplex": m.group(5),
            "speed": m.group(6),
            "type": m.group(7).strip(),
        }
    return rows


def parse_vlans(text: str) -> list[dict[str, Any]]:
    vlans: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if not line.strip() or line.startswith("VLAN ") or line.startswith("----"):
            continue
        if re.match(r"^\s*\d+\s+\S+", line):
            m = re.match(r"^\s*(\d+)\s+(.+?)\s{2,}(active|act/unsup|suspended)\s*(.*)$", line)
            if not m:
                continue
            ports = [p.strip() for p in m.group(4).split(",") if p.strip()]
            current = {"id": m.group(1), "name": m.group(2).strip(), "status": m.group(3), "ports": ports}
            vlans.append(current)
        elif current and re.search(r"(Gi|Fa|Te)\d", line):
            current["ports"].extend([p.strip() for p in line.split(",") if p.strip()])
    return vlans


def parse_mac_table(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = re.match(r"^\s*(All|\d+)\s+([0-9a-fA-F.]{14})\s+(\S+)\s+(\S+)", line)
        if not m:
            continue
        rows.append({"vlan": m.group(1), "mac": norm_mac(m.group(2)), "type": m.group(3), "port": m.group(4)})
    return rows


def parse_cdp(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for block in text.split("-------------------------"):
        if "Device ID:" not in block:
            continue
        item: dict[str, str] = {}
        dev = re.search(r"Device ID:\s*(.+)", block)
        ip = re.search(r"IP address:\s*([0-9.]+)", block)
        platform = re.search(r"Platform:\s*([^,\n]+)", block)
        iface = re.search(r"Interface:\s*([^,]+),\s*Port ID \(outgoing port\):\s*(.+)", block)
        if dev:
            item["device_id"] = dev.group(1).strip()
        if ip:
            item["ip"] = ip.group(1).strip()
        if platform:
            item["platform"] = platform.group(1).strip()
        if iface:
            item["local_interface"] = short_if(iface.group(1).strip())
            item["remote_port"] = iface.group(2).strip()
        if item:
            out.append(item)
    return out


def parse_switch(raw_text: str) -> dict[str, Any]:
    sections = extract_switch_sections(raw_text)
    version = sections.get("show version", "")
    running = sections.get("show running-config", "")
    startup = sections.get("show startup-config", "")
    hostname = re.search(r"^hostname\s+(\S+)", running, flags=re.M)
    ios = re.search(r"Cisco IOS Software.*Version\s+([^,\n]+)", version)
    uptime = re.search(r"^(\S+)\s+uptime is\s+(.+)$", version, flags=re.M)
    model = re.search(r"Model number\s+:\s+(.+)", version)
    serial = re.search(r"System serial number\s+:\s+(.+)", version)
    base_mac = re.search(r"Base ethernet MAC Address\s+:\s+(.+)", version)
    svi = re.search(r"interface Vlan90\n\s+ip address\s+([0-9.]+)\s+([0-9.]+)", running)
    gateway = re.search(r"^ip default-gateway\s+([0-9.]+)", running, flags=re.M)

    config_ports = parse_interface_config(running)
    startup_ports = parse_interface_config(startup)
    statuses = parse_status(sections.get("show interfaces status", ""))
    mac_table = parse_mac_table(sections.get("show mac address-table", ""))
    cdp = parse_cdp(sections.get("show cdp neighbors detail", ""))
    vlans = parse_vlans(sections.get("show vlan brief", sections.get("show vlan", "")))

    ports: dict[str, dict[str, Any]] = {}
    for key in sorted(set(config_ports) | set(statuses)):
        port = {"interface": key}
        port.update(config_ports.get(key, {}))
        port.update({f"oper_{k}": v for k, v in statuses.get(key, {}).items() if k != "interface"})
        port["learned_macs"] = [m for m in mac_table if m["port"] == key]
        if key in startup_ports and config_ports.get(key) != startup_ports.get(key):
            port["startup_differs"] = True
            port["startup_config"] = startup_ports[key]
        else:
            port["startup_differs"] = False
        ports[key] = port

    return {
        "device": {
            "hostname": hostname.group(1) if hostname else "SW-SN-03",
            "management_ip": svi.group(1) if svi else "10.100.90.99",
            "default_gateway": gateway.group(1) if gateway else NA,
            "platform": "Cisco Catalyst 2960XR",
            "model": model.group(1).strip() if model else NA,
            "serial": serial.group(1).strip() if serial else NA,
            "base_mac": base_mac.group(1).strip() if base_mac else NA,
            "ios_version": ios.group(1).strip() if ios else NA,
            "uptime": uptime.group(2).strip() if uptime else NA,
        },
        "ports": list(ports.values()),
        "ports_by_name": ports,
        "vlans": vlans,
        "mac_table": mac_table,
        "cdp_neighbors": cdp,
        "running_config_differs_from_startup": running.strip() != startup.strip(),
        "lldp_enabled": "% LLDP is not enabled" not in sections.get("show lldp neighbors", ""),
        "raw_sections": sorted(sections),
    }


def ip_to_vlan(ip_value: str, router_vlans: list[dict[str, Any]]) -> str:
    if not ip_value or ip_value == NA:
        return NA
    ip_part = ip_value.split("/", 1)[0]
    try:
        addr = ipaddress.ip_address(ip_part)
    except ValueError:
        return NA
    for vlan in router_vlans:
        network = vlan.get("network", "")
        if not network or network == NA:
            continue
        try:
            if addr in ipaddress.ip_network(network, strict=False):
                return str(vlan.get("id", NA))
        except ValueError:
            continue
    return NA


def build_topology(router: dict[str, Any], switch: dict[str, Any], prox_net: dict[str, Any], guests: list[dict[str, Any]], prox_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    arp_by_ip = {a.get("address"): a for a in router.get("arp", []) if a.get("address")}
    mac_entries: dict[str, list[dict[str, str]]] = {}
    for row in switch.get("mac_table", []):
        mac_entries.setdefault(row["mac"], []).append(row)

    node_meta = {n.get("name"): n for n in prox_nodes if n.get("name")}
    prox_nodes_net = prox_net.get("nodes", {}) if isinstance(prox_net, dict) else {}
    node_links: list[dict[str, Any]] = []
    for node, net_data in sorted(prox_nodes_net.items()):
        ip = net_data.get("management_ip") or node_meta.get(node, {}).get("corosync_ring0_addr") or NA
        arp = arp_by_ip.get(ip, {})
        mac = norm_mac(arp.get("mac-address"))
        entries = mac_entries.get(mac, [])
        port = entries[0]["port"] if entries else NA
        observed_vlan = entries[0]["vlan"] if entries else ip_to_vlan(ip, router.get("vlans", []))
        node_links.append(
            {
                "node": node,
                "management_ip": ip,
                "management_mac": mac,
                "switch_port": port,
                "observed_vlan": observed_vlan,
                "bridges": net_data.get("bridges", {}),
            }
        )

    node_port_by_node = {n["node"]: n.get("switch_port", NA) for n in node_links}
    workload_links: list[dict[str, Any]] = []
    for guest in sorted(guests, key=lambda g: (str(g.get("node", "")), int(g.get("id", 0)))):
        networks = guest.get("networks") or []
        if not networks:
            workload_links.append(
                {
                    "id": guest.get("id", NA),
                    "name": guest.get("name", NA),
                    "type": guest.get("type", NA),
                    "node": guest.get("node", NA),
                    "status": guest.get("status", NA),
                    "bridge": NA,
                    "mac": NA,
                    "ip": NA,
                    "configured_vlan": NA,
                    "effective_vlan": NA,
                    "observed_switch_port": NA,
                    "observed_vlan": NA,
                }
            )
            continue
        for net in networks:
            mac = norm_mac(net.get("mac"))
            observed = mac_entries.get(mac, [])
            ip_value = net.get("ip") or NA
            inferred_vlan = ip_to_vlan(ip_value, router.get("vlans", []))
            effective = net.get("effective_vlan") or NA
            if effective == NA and inferred_vlan != NA:
                effective = f"{inferred_vlan} (inferido pelo IP)"
            workload_links.append(
                {
                    "id": guest.get("id", NA),
                    "name": guest.get("name", NA),
                    "type": guest.get("type", NA),
                    "node": guest.get("node", NA),
                    "status": guest.get("status", NA),
                    "bridge": net.get("bridge", NA),
                    "mac": mac,
                    "ip": ip_value,
                    "configured_vlan": net.get("tag", NA),
                    "effective_vlan": effective,
                    "observed_switch_port": observed[0]["port"] if observed else NA,
                    "observed_vlan": observed[0]["vlan"] if observed else inferred_vlan,
                    "host_switch_port": node_port_by_node.get(guest.get("node"), NA),
                }
            )

    return {
        "router_to_switch": {
            "router": router.get("device", {}).get("name", NA),
            "router_interface": "ether3-switch",
            "switch": switch.get("device", {}).get("hostname", NA),
            "switch_interface": "Gi1/0/1",
            "vlans": ["30", "60", "90", "130"],
            "source": "CDP do switch e bridge VLAN do RouterOS",
        },
        "proxmox_nodes": node_links,
        "workloads": workload_links,
    }


def make_findings(router: dict[str, Any], switch: dict[str, Any], topology: dict[str, Any], storage: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(level: str, title: str, evidence: str, impact: str, recommendation: str) -> None:
        findings.append(
            {
                "level": level,
                "title": title,
                "evidence": evidence,
                "impact": impact,
                "recommendation": recommendation,
            }
        )

    if switch.get("running_config_differs_from_startup"):
        add(
            "WARNING",
            "Running-config do switch difere do startup-config",
            "O running-config tem alteracao posterior ao NVRAM update; Gi1/0/15 aparece com allowed VLANs diferente entre running e startup.",
            "Apos reboot do switch, parte da configuracao atual pode voltar ao estado anterior.",
            "Revisar a diferenca e decidir, fora desta coleta read-only, se deve salvar ou ajustar a configuracao.",
        )

    for port in switch.get("ports", []):
        if port.get("oper_status") == "connected" and port.get("oper_speed") in {"a-100", "100"} and "1000" in str(port.get("oper_type", "")):
            role = port.get("description") or port.get("oper_name") or port.get("interface")
            if "HOST-0" in str(role).upper():
                impact = "Pode limitar trafego do host0; isso importa especialmente em migracoes e servicos com disco/rede mais intensivos."
            elif "AP" in str(role).upper():
                impact = "Pode limitar a capacidade de clientes ligados a esse AP ou enlace guest."
            else:
                impact = "Pode limitar trafego desse enlace em relacao ao esperado para porta gigabit."
            add(
                "WARNING",
                f"Porta {port.get('interface')} conectada a 100 Mbps",
                f"{port.get('interface')} ({port.get('description') or port.get('oper_name')}) esta connected com speed {port.get('oper_speed')}.",
                impact,
                "Validar cabo, porta, autonegociacao e NIC quando for fazer janela de manutencao.",
            )

    router_vlan_ids = {str(v.get("id")) for v in router.get("vlans", [])}
    switch_vlan_ids = {str(v.get("id")) for v in switch.get("vlans", []) if str(v.get("id")) not in {"1", "1002", "1003", "1004", "1005"}}
    orphan = sorted(switch_vlan_ids - router_vlan_ids, key=lambda x: int(x) if x.isdigit() else 9999)
    if orphan:
        add(
            "REVIEW",
            "VLANs existem no switch sem interface L3 correspondente no RouterOS",
            "VLANs no switch nao roteadas/coletadas na RB: " + ", ".join(orphan) + ".",
            "Pode ser legado/teste, mas aumenta ambiguidade durante padronizacao.",
            "Confirmar se devem permanecer, ser documentadas como reserva ou removidas em mudanca planejada.",
        )

    prox_ports = [
        p
        for p in switch.get("ports", [])
        if "PROXMOX" in str(p.get("description") or p.get("oper_name", "")).upper() and p.get("mode") == "trunk"
    ]
    native_values = sorted({str(p.get("native_vlan", NA)) for p in prox_ports})
    allowed_values = sorted({str(p.get("trunk_allowed_vlans", NA)) for p in prox_ports})
    if len(native_values) > 1 or len(allowed_values) > 1:
        add(
            "REVIEW",
            "Trunks Proxmox com native/allowed VLANs diferentes",
            f"Native VLANs vistas: {', '.join(native_values)}; allowed VLANs vistas: {', '.join(allowed_values)}.",
            "Nao e necessariamente erro no homelab, mas pode causar comportamento diferente entre hosts.",
            "Padronizar trunk por perfil de host ou registrar explicitamente excecoes.",
        )

    if not switch.get("lldp_enabled"):
        add(
            "INFO",
            "LLDP desabilitado no switch",
            "show lldp neighbors retornou que LLDP nao esta habilitado; CDP esta ativo e viu a RB.",
            "Topologia multi-vendor depende mais de CDP/MAC table/ARP do que de LLDP.",
            "Opcionalmente avaliar LLDP em momento separado, se fizer sentido para descoberta automatica.",
        )

    if any("timeout" in w.lower() for w in router.get("collection_warnings", []) if w):
        add(
            "REVIEW",
            "Ranges dos pools DHCP nao foram comprovados",
            "A consulta /ip pool print detail marcou timeout nesta coleta.",
            "DHCP server, redes, gateway e DNS foram coletados, mas ranges exatos dos pools ficam pendentes.",
            "Coletar novamente em janela separada se os ranges forem decisivos para o playbook.",
        )

    if router.get("device", {}).get("firmware_current") != router.get("device", {}).get("firmware_available"):
        add(
            "INFO",
            "Firmware RouterBOARD diferente da versao disponivel",
            f"current-firmware={router.get('device', {}).get('firmware_current')} upgrade-firmware={router.get('device', {}).get('firmware_available')}.",
            "Nao afeta diretamente a topologia atual; e um ponto de manutencao.",
            "Avaliar upgrade de firmware em manutencao planejada, nunca dentro de inventario read-only.",
        )

    if "hd1tb" in json.dumps(storage, ensure_ascii=False):
        add(
            "INFO",
            "hd1tb e um storage local definido globalmente no Proxmox, nao um compartilhamento de rede",
            "Inventario Proxmox mostra hd1tb como dir em /mnt/pve/hd1tb, shared=0, montado de fato no host1.",
            "A aparencia de 'disco em todos os hosts' vem da configuracao clusterizada do Proxmox, nao do switch/RB.",
            "Para espelhamento/migracao do Nextcloud, tratar isso no desenho de storage Proxmox/ZFS/LVM, separado da rede.",
        )

    if "ip http server" in read_text(RAW / "switch" / "show_running_config.txt"):
        add(
            "REVIEW",
            "HTTP/HTTPS habilitados no switch",
            "running-config contem ip http server e ip http secure-server.",
            "Pode ser aceitavel em homelab, mas e superficie administrativa adicional.",
            "Revisar politica de gerenciamento na VLAN 90 durante a padronizacao.",
        )

    if "no service password-encryption" in read_text(RAW / "switch" / "show_running_config.txt"):
        add(
            "REVIEW",
            "Switch com no service password-encryption",
            "running-config contem no service password-encryption; secrets foram redigidos no inventario.",
            "Pode expor senhas tipo 0/7 se forem adicionadas futuramente.",
            "Revisar hardening de configuracao em etapa propria.",
        )

    switch_keyscan = read_text(RAW / "ssh_known_hosts_switch") + read_text(RAW / "ssh_known_hosts_switch_legacy")
    if "ssh-rsa" not in switch_keyscan:
        add(
            "REVIEW",
            "Acesso SSH ao switch dependeu de algoritmos legados",
            "Coleta do switch exigiu diffie-hellman-group14-sha1/ssh-rsa e o ssh-keyscan retornou apenas banner, sem chave RSA utilizavel.",
            "Nao muda a topologia, mas e ponto de seguranca/operabilidade para automacao futura.",
            "Planejar revisao de firmware/ciphers/SSH do switch quando houver janela, sem misturar com inventario read-only.",
        )

    findings.sort(key=lambda f: {"CRITICAL": 0, "WARNING": 1, "REVIEW": 2, "INFO": 3}.get(f["level"], 9))
    return findings


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        text = str(value if value not in (None, "") else NA)
        return text.replace("|", "\\|").replace("\n", "<br>")

    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def vlan_name(vlan_id: str, router: dict[str, Any], switch: dict[str, Any]) -> str:
    for vlan in router.get("vlans", []):
        if str(vlan.get("id")) == str(vlan_id):
            return vlan.get("name", NA)
    for vlan in switch.get("vlans", []):
        if str(vlan.get("id")) == str(vlan_id):
            return vlan.get("name", NA)
    return NA


def generate_markdown(router: dict[str, Any], switch: dict[str, Any], topology: dict[str, Any], findings: list[dict[str, str]], guests: list[dict[str, Any]]) -> None:
    rdev = router["device"]
    sdev = switch["device"]
    connected_ports = [p for p in switch["ports"] if p.get("oper_status") == "connected"]
    warning_count = sum(1 for f in findings if f["level"] == "WARNING")
    critical_count = sum(1 for f in findings if f["level"] == "CRITICAL")

    vlan_rows = []
    for vlan in sorted(router.get("vlans", []), key=lambda v: int(v.get("id", 9999))):
        vlan_rows.append(
            [
                vlan.get("id"),
                vlan.get("name"),
                vlan.get("network"),
                vlan.get("gateway"),
                vlan.get("dhcp_server"),
                vlan.get("dhcp_dns"),
            ]
        )

    switch_rows = []
    for p in sorted(switch.get("ports", []), key=lambda x: (0 if x["interface"].startswith("Gi") else 1, [int(n) for n in re.findall(r"\d+", x["interface"])])):
        if not p["interface"].startswith(("Gi", "Fa")):
            continue
        switch_rows.append(
            [
                p.get("interface"),
                p.get("description") or p.get("oper_name"),
                p.get("oper_status"),
                p.get("mode"),
                p.get("oper_vlan"),
                p.get("trunk_allowed_vlans"),
                p.get("native_vlan"),
                p.get("oper_speed"),
            ]
        )

    node_rows = [
        [n["node"], n["management_ip"], n["management_mac"], n["switch_port"], n["observed_vlan"]]
        for n in topology["proxmox_nodes"]
    ]

    workload_rows = [
        [
            w["id"],
            w["name"],
            w["type"],
            w["node"],
            w["status"],
            w["ip"],
            w["bridge"],
            w["configured_vlan"],
            w["effective_vlan"],
            w["observed_switch_port"],
            w.get("host_switch_port", NA),
            w["observed_vlan"],
        ]
        for w in topology["workloads"]
    ]

    docs = [
        "# Network Inventory - Homelab",
        "",
        "## 1. Executive Summary",
        "",
        f"- Router principal: {rdev['name']} ({rdev['model']}, RouterOS {rdev['routeros_version']})",
        f"- Switch principal: {sdev['hostname']} ({sdev['model']}, IOS {sdev['ios_version']})",
        f"- VLANs roteadas na RB: {', '.join(v.get('id', NA) for v in router.get('vlans', []))}",
        f"- Portas conectadas no switch: {len(connected_ports)}",
        f"- Hosts Proxmox mapeados no switch: {len([n for n in topology['proxmox_nodes'] if n['switch_port'] != NA])}/{len(topology['proxmox_nodes'])}",
        f"- Workloads Proxmox no inventario cruzado: {len({w['id'] for w in topology['workloads']})}",
        f"- Findings: {critical_count} critical, {warning_count} warnings, {len(findings)} total",
        "",
        "Coleta feita em modo somente leitura. Credenciais, hashes e communities foram redigidos quando apareceram em saida de configuracao.",
        "",
        "## 2. RouterBOARD / Gateway",
        "",
        md_table(
            ["Campo", "Valor"],
            [
                ["Nome", rdev["name"]],
                ["IP de gerenciamento", rdev["management_ip"]],
                ["Modelo", f"{rdev['board_name']} / {rdev['model']}"],
                ["Serial", rdev["serial"]],
                ["RouterOS", rdev["routeros_version"]],
                ["Firmware atual/disponivel", f"{rdev['firmware_current']} / {rdev['firmware_available']}"],
                ["Uptime", rdev["uptime"]],
                ["CPU/RAM", f"{rdev['cpu']} / {rdev['memory_total']}"],
            ],
        ),
        "",
        "### VLANs roteadas pela RB",
        "",
        md_table(["VLAN", "Interface", "Rede", "Gateway", "DHCP", "DNS entregue"], vlan_rows),
        "",
        "### Bridge e trunk",
        "",
        md_table(
            ["Bridge", "VLAN", "Tagged", "Untagged"],
            [
                [v.get("bridge"), v.get("vlan-ids"), v.get("tagged", ""), v.get("untagged", "")]
                for v in router.get("bridge_vlans", [])
                if str(v.get("vlan-ids")) != "1"
            ],
        ),
        "",
        "## 3. Cisco Switch",
        "",
        md_table(
            ["Campo", "Valor"],
            [
                ["Hostname", sdev["hostname"]],
                ["IP de gerenciamento", sdev["management_ip"]],
                ["Gateway", sdev["default_gateway"]],
                ["Modelo", sdev["model"]],
                ["Serial", sdev["serial"]],
                ["IOS", sdev["ios_version"]],
                ["Uptime", sdev["uptime"]],
                ["LLDP", "habilitado" if switch.get("lldp_enabled") else "desabilitado"],
            ],
        ),
        "",
        "### Portas do switch",
        "",
        md_table(["Porta", "Descricao", "Status", "Modo", "VLAN operacional", "Allowed VLANs", "Native", "Speed"], switch_rows),
        "",
        "## 4. VLANs e Subnets",
        "",
        md_table(
            ["VLAN", "Nome RouterOS", "Nome Switch", "Rede", "Gateway"],
            [
                [v.get("id"), v.get("name"), vlan_name(str(v.get("id")), {"vlans": []}, switch), v.get("network"), v.get("gateway")]
                for v in sorted(router.get("vlans", []), key=lambda x: int(x.get("id", 9999)))
            ],
        ),
        "",
        "## 5. Proxmox na rede",
        "",
        md_table(["Host", "IP gerencia", "MAC observado", "Porta switch", "VLAN observada"], node_rows),
        "",
        "## 6. Workloads Proxmox - Rede",
        "",
        md_table(
            ["ID", "Nome", "Tipo", "Host", "Status", "IP", "Bridge", "VLAN config", "VLAN efetiva", "Porta observada", "Porta do host", "VLAN observada"],
            workload_rows,
        ),
        "",
        "## 7. Observacoes de relacionamento",
        "",
        "- A RB RT-SN-003 chega ao switch pela porta Gi1/0/1, associada ao ether3-switch/bridge-core.",
        "- VLANs 30, 60, 90 e 130 passam no trunk RB <-> switch.",
        "- VLAN 130 aparece segmentada para AP/guest e nao aparece permitida nos trunks Proxmox coletados.",
        "- MAC table e ARP permitem mapear hosts Proxmox ao switch; workloads desligados ou sem trafego recente podem ficar sem porta observada.",
        "- O comportamento do storage hd1tb visto no cluster nao e compartilhamento de rede; e uma definicao local/global do Proxmox documentada no inventario anterior.",
        "",
        "## 8. Arquivos de origem",
        "",
        "- Raw RouterOS: `raw/routeros.stream` e `raw/routeros/*.txt`",
        "- Raw switch: `raw/switch.stream` e `raw/switch/*.txt`",
        "- Dados tratados: `data/*.json`",
        "- Topologia: `topology-current.md`",
        "- Findings: `findings.md`",
    ]
    write_text(ROOT / "network-inventory.md", "\n".join(docs))

    readme = [
        "# Network Inventory",
        "",
        "Inventario read-only da infraestrutura de rede do homelab.",
        "",
        "## Arquivos principais",
        "",
        "- `network-inventory.md`: documentacao tecnica principal.",
        "- `topology-current.md`: diagramas Mermaid de topologia.",
        "- `findings.md`: inconsistencias, riscos e itens de revisao.",
        "- `inventory.csv`: endpoints, hosts e workloads em formato tabular.",
        "- `data/`: JSONs tratados.",
        "- `raw/`: saidas brutas redigidas.",
        "",
        "## Escopo",
        "",
        "Foram coletadas configuracoes de consulta da RB MikroTik, switch Cisco e dados de rede ja inventariados do Proxmox. Nenhum comando de alteracao foi executado nos equipamentos.",
    ]
    write_text(ROOT / "README.md", "\n".join(readme))

    finding_lines = ["# Network Findings", ""]
    for f in findings:
        finding_lines.extend(
            [
                f"## [{f['level']}] {f['title']}",
                "",
                f"- Evidencia: {f['evidence']}",
                f"- Impacto: {f['impact']}",
                f"- Recomendacao: {f['recommendation']}",
                "",
            ]
        )
    write_text(ROOT / "findings.md", "\n".join(finding_lines))

    write_topology_md(router, switch, topology)


def mermaid_id(prefix: str, value: str) -> str:
    return prefix + re.sub(r"[^A-Za-z0-9_]", "_", value)


def write_topology_md(router: dict[str, Any], switch: dict[str, Any], topology: dict[str, Any]) -> None:
    rdev = router["device"]
    sdev = switch["device"]
    physical = [
        "```mermaid",
        "flowchart LR",
        f'  INTERNET["Internet / ISP"] --> RB["{rdev["name"]}\\nMikroTik {rdev["model"]}"]',
        f'  RB -- "ether3-switch trunk\\nVLAN 30/60/90/130" --> SW["{sdev["hostname"]}\\n{sdev["model"]}"]',
    ]
    for node in topology["proxmox_nodes"]:
        if node["switch_port"] == NA:
            continue
        nid = mermaid_id("H_", node["node"])
        speed = ""
        for p in switch.get("ports", []):
            if p.get("interface") == node["switch_port"]:
                speed = p.get("oper_speed", "")
                break
        physical.append(f'  SW -- "{node["switch_port"]} {speed}\\nVLAN {node["observed_vlan"]}" --> {nid}["{node["node"]}\\n{node["management_ip"]}"]')
    for port in switch.get("ports", []):
        desc = port.get("description") or port.get("oper_name") or ""
        if port.get("oper_status") == "connected" and "AP_GUEST" in desc:
            pid = mermaid_id("AP_", port["interface"])
            physical.append(f'  SW -- "{port["interface"]}\\naccess VLAN {port.get("oper_vlan")}" --> {pid}["AP / Guest\\n{port["interface"]}"]')
    physical.append("```")

    vlan_graph = ["```mermaid", "flowchart TB", f'  RB["{rdev["name"]}\\nGateway L3"]']
    for vlan in sorted(router.get("vlans", []), key=lambda x: int(x.get("id", 9999))):
        vid = str(vlan.get("id"))
        vnode = mermaid_id("VLAN_", vid)
        vlan_graph.append(f'  RB --> {vnode}["VLAN {vid}\\n{vlan.get("name")}\\n{vlan.get("network")}"]')
        if vid == "30":
            vlan_graph.append(f'  {vnode} --> PVE["Proxmox hosts\\nhost0-host3"]')
        if vid == "60":
            vlan_graph.append(f'  {vnode} --> SVC["Services / workloads"]')
        if vid == "90":
            vlan_graph.append(f'  {vnode} --> MGMT["Management\\nSwitch {sdev["management_ip"]}"]')
        if vid == "130":
            vlan_graph.append(f'  {vnode} --> GUEST["Guest Wi-Fi / APs"]')
    vlan_graph.append("```")

    prox_graph = ["```mermaid", "flowchart TB", '  SW["Cisco Switch"]']
    for node in topology["proxmox_nodes"]:
        nid = mermaid_id("PVE_", node["node"])
        prox_graph.append(f'  SW --> {nid}["{node["node"]}\\n{node["management_ip"]}"]')
        bridges = node.get("bridges", {})
        for bridge, bdata in bridges.items():
            bid = mermaid_id(f"B_{node['node']}_", bridge)
            label = f"{bridge}\\nports: {','.join(bdata.get('ports', []))}\\nvlan-aware: {bdata.get('vlan_aware')}"
            prox_graph.append(f'  {nid} --> {bid}["{label}"]')
    prox_graph.append("```")

    workload_graph = ["```mermaid", "flowchart TB", '  CL["Proxmox Workloads"]']
    for node in topology["proxmox_nodes"]:
        nid = mermaid_id("N_", node["node"])
        workload_graph.append(f'  CL --> {nid}["{node["node"]}"]')
    for w in topology["workloads"]:
        wid = mermaid_id("W_", f"{w['id']}_{w['name']}_{w['bridge']}")
        label = f"{w['type']} {w['id']} - {w['name']}\\n{w['bridge']} / VLAN {w['effective_vlan']}\\nIP {w['ip']}"
        workload_graph.append(f'  {mermaid_id("N_", w["node"])} --> {wid}["{label}"]')
    workload_graph.append("```")

    text = [
        "# Current Network Topology",
        "",
        "## 1. Physical Topology",
        "",
        "\n".join(physical),
        "",
        "## 2. VLAN / L3 Topology",
        "",
        "\n".join(vlan_graph),
        "",
        "## 3. Proxmox Bridges",
        "",
        "\n".join(prox_graph),
        "",
        "## 4. Workloads",
        "",
        "\n".join(workload_graph),
    ]
    write_text(ROOT / "topology-current.md", "\n".join(text))


def write_csv(topology: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for node in topology["proxmox_nodes"]:
        rows.append(
            {
                "record_type": "proxmox-host",
                "name": node["node"],
                "ip": node["management_ip"],
                "mac": node["management_mac"],
                "vlan": node["observed_vlan"],
                "observed_switch_port": node["switch_port"],
                "host_switch_port": "",
                "bridge": "",
                "status": "",
                "source": "router arp + switch mac table",
            }
        )
    for w in topology["workloads"]:
        rows.append(
            {
                "record_type": "workload",
                "name": f"{w['type']} {w['id']} {w['name']}",
                "ip": w["ip"],
                "mac": w["mac"],
                "vlan": w["observed_vlan"],
                "observed_switch_port": w["observed_switch_port"],
                "host_switch_port": w.get("host_switch_port", NA),
                "bridge": w["bridge"],
                "status": w["status"],
                "source": "proxmox inventory + switch mac table + router subnets",
            }
        )
    with (ROOT / "inventory.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    router = parse_router(read_text(RAW / "routeros.stream"))
    switch = parse_switch(read_text(RAW / "switch.stream"))
    prox_net = read_json(PROXMOX_DATA / "network.json", {})
    guests = read_json(PROXMOX_DATA / "guests.json", [])
    prox_nodes = read_json(PROXMOX_DATA / "nodes.json", [])
    storage = read_json(PROXMOX_DATA / "storage.json", {})
    topology = build_topology(router, switch, prox_net, guests, prox_nodes)
    findings = make_findings(router, switch, topology, storage)

    write_json(DATA / "router.json", router)
    write_json(DATA / "switch.json", switch)
    write_json(DATA / "topology.json", topology)
    write_json(DATA / "findings.json", findings)
    write_json(
        DATA / "network.json",
        {
            "router": router["device"],
            "switch": switch["device"],
            "vlans": router["vlans"],
            "proxmox_nodes": topology["proxmox_nodes"],
            "workloads": topology["workloads"],
            "findings_summary": {
                "critical": sum(1 for f in findings if f["level"] == "CRITICAL"),
                "warnings": sum(1 for f in findings if f["level"] == "WARNING"),
                "review": sum(1 for f in findings if f["level"] == "REVIEW"),
                "info": sum(1 for f in findings if f["level"] == "INFO"),
            },
        },
    )
    write_csv(topology)
    generate_markdown(router, switch, topology, findings, guests)

    print("Network inventory completed")
    print("")
    print(f"Router: {router['device']['name']} ({router['device']['model']})")
    print(f"Switch: {switch['device']['hostname']} ({switch['device']['model']})")
    print(f"VLANs: {len(router['vlans'])}")
    print(f"Subnets: {len([v for v in router['vlans'] if v.get('network') != NA])}")
    print(f"Proxmox hosts: {len(topology['proxmox_nodes'])}")
    print(f"Workloads: {len({w['id'] for w in topology['workloads']})}")
    print(f"Warnings: {sum(1 for f in findings if f['level'] == 'WARNING')}")
    print(f"Critical findings: {sum(1 for f in findings if f['level'] == 'CRITICAL')}")
    print("")
    print(f"Report: {ROOT / 'network-inventory.md'}")
    print(f"Raw data: {RAW}")


if __name__ == "__main__":
    main()
