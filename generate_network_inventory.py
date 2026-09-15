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
BASELINE_MD = ROOT / "network-baseline-2026-09-15.md"
NA = "Nao determinado"
REDACTED = "<REDACTED>"
SEVERITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "WARNING": 2,
    "MEDIUM": 3,
    "REVIEW": 4,
    "LOW": 5,
    "INFO": 6,
}


def clean_text(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = text.replace("\r", "")
    text = re.sub(r"^Script started.*\n", "", text, flags=re.M)
    text = re.sub(r"^Script done.*\n?", "", text, flags=re.M)
    return text


def sanitize_text(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", text)
    text = re.sub(r"(?i)(\busername\s+\S+(?:\s+\S+)*\s+secret\s+(?:5|8|9)\s+)\S+", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(\benable\s+secret\s+(?:5|8|9)?\s*)\S+", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(\bpassword\s+)(?:0|7\s+)?\S+", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(snmp-server\s+community\s+)\S+", r"\1<REDACTED>", text)
    text = re.sub(
        r"(?i)(snmp-server\s+user\s+\S+\s+\S+\s+v3\s+auth\s+\S+\s+)\S+(\s+priv\s+\S+\s+)\S+",
        r"\1<REDACTED>\2<REDACTED>",
        text,
    )
    text = re.sub(r"(?i)(\b(?:password|passwd|pwd|secret|token|api-key|apikey|access-token|refresh-token|private-key|shared-secret|psk|trap-community)=)(\"[^\"]*\"|'[^']*'|[^ \t\n]+)", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(/snmp\s+community\s+\S+.*\bname=)(\"[^\"]*\"|'[^']*'|[^ \t\n]+)", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(\bpppoe\S*.*\buser=)(\"[^\"]*\"|'[^']*'|[^ \t\n]+)", r"\1<REDACTED>", text)
    text = re.sub(r"(?i)(COMMAND=\"ssh[^\"]*\s)\S+@([0-9.]+)", r"\1<REDACTED_USER>@\2", text)
    text = re.sub(r"\([^@\n]+@([0-9.]+)\) Password:\s*", r"(<REDACTED_USER>@\1) Password: <REDACTED>", text)
    return text


def sanitize_data(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_data(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_data(item) for key, item in value.items()}
    return value


def sanitize_raw_tree() -> None:
    if not RAW.exists():
        return
    for path in RAW.rglob("*"):
        if not path.is_file():
            continue
        original = path.read_text(errors="replace")
        sanitized = sanitize_text(original)
        if sanitized != original:
            write_text(path, sanitized)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return sanitize_text(path.read_text(errors="replace"))


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_data(data), indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sanitize_text(text).rstrip() + "\n")


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


def parse_markdown_table(text: str, heading: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if heading in line:
            start = idx
            break
    if start is None:
        return []

    table: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("|"):
            table.append(line)
        elif table:
            break
    if len(table) < 3:
        return []

    headers = [h.strip() for h in table[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def baseline_facts() -> dict[str, Any]:
    text = read_text(BASELINE_MD)
    facts: dict[str, Any] = {
        "baseline_date": "2026-09-15" if "15/09/2026" in text else NA,
        "source": str(BASELINE_MD.name) if text else NA,
        "port_speeds": {},
    }
    if not text:
        return facts

    cisco_rows = parse_markdown_table(text, "Cisco SW-SN-03")
    for row in cisco_rows:
        key = row.get("Item", "")
        value = row.get("Estado", "")
        if key == "Modelo":
            facts["switch_model"] = value
        elif key == "Serial":
            facts["switch_serial"] = value
        elif key == "IOS":
            facts["switch_ios"] = value
        elif key == "Management":
            facts["switch_management"] = value
        elif key == "Gateway":
            facts["switch_gateway"] = value
        elif key == "DNS":
            facts["switch_dns"] = value
        elif key == "NTP":
            facts["switch_ntp"] = value
        elif key == "Timezone":
            facts["switch_timezone"] = value

    router_rows = parse_markdown_table(text, "MikroTik RT-SN-003")
    for row in router_rows:
        key = row.get("Item", "")
        value = row.get("Estado", "")
        if key == "Modelo":
            facts["router_model_text"] = value
        elif key == "Serial":
            facts["router_serial"] = value
        elif key == "RouterOS":
            facts["routeros_version"] = value
        elif key == "WAN":
            facts["router_wan"] = value
        elif key == "Bridge":
            facts["router_bridge"] = value
        elif key == "Uplink Cisco":
            facts["router_uplink"] = value
        elif key == "NTP client":
            facts["router_ntp_client"] = value
        elif key == "Timezone":
            facts["router_timezone"] = value

    if re.search(r"Gi1/0/15.*?(voltou|1 Gb/s)", text, flags=re.I | re.S):
        facts["port_speeds"]["Gi1/0/15"] = "1G"
    if re.search(r"Gi1/0/7.*?1 Gb/s", text, flags=re.I | re.S):
        facts["port_speeds"]["Gi1/0/7"] = "1G"
    if re.search(r"Gi1/0/10.*?100 Mb/s", text, flags=re.I | re.S):
        facts["port_speeds"]["Gi1/0/10"] = "100M"
    for port in ("Gi1/0/1", "Gi1/0/3", "Gi1/0/5", "Gi1/0/6"):
        facts["port_speeds"].setdefault(port, "1G")

    if "RouterOS 6.49.18" in text:
        facts.setdefault("routeros_version", "6.49.18 long-term")
    if "15.2(7)E14" in text:
        facts.setdefault("switch_ios", "15.2(7)E14")
    return facts


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


def routeros_export_commands(text: str) -> dict[str, list[dict[str, Any]]]:
    logical_lines: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.endswith("\\"):
            part = line[:-1].strip()
            if current and not current.endswith((" ", "=")):
                current += " "
            current += part
            if not current.endswith("="):
                current += " "
            continue
        if current and not current.endswith((" ", "=")):
            current += " "
        current += line.strip()
        logical_lines.append(current.strip())
        current = ""
    if current:
        logical_lines.append(current.strip())

    commands: dict[str, list[dict[str, Any]]] = {}
    section = ""
    action_words = {"add", "set", "remove", "enable", "disable"}
    for line in logical_lines:
        if not line or line.startswith("#"):
            continue
        if line.startswith("/"):
            tokens = line.split()
            action_index = next((i for i, token in enumerate(tokens) if token in action_words), None)
            if action_index is None:
                section = line.strip()
                commands.setdefault(section, [])
                continue
            section = " ".join(tokens[:action_index])
            command = " ".join(tokens[action_index:])
        else:
            command = line
        if not section or not command:
            continue

        tokens = command.split()
        action = tokens[0] if tokens else ""
        kv_start = next((i for i, token in enumerate(tokens[1:], 1) if "=" in token), len(tokens))
        target = " ".join(tokens[1:kv_start]).strip()
        item = kv_pairs(command)
        item["_action"] = action
        item["_target"] = target
        item["_raw"] = command
        if section == "/ip service" and target and "name" not in item:
            item["name"] = target
        commands.setdefault(section, []).append(item)
    return commands


def write_routeros_export_raw(commands: dict[str, list[dict[str, Any]]], export_text: str) -> None:
    write_text(RAW / "routeros.stream", export_text)
    write_text(RAW / "routeros" / "export_hide_sensitive_terse.txt", export_text)

    mapping = {
        "/interface bridge": "interface_bridge_print_detail.txt",
        "/interface bridge port": "interface_bridge_port_print_detail.txt",
        "/interface bridge vlan": "interface_bridge_vlan_print_detail.txt",
        "/interface ethernet": "interface_ethernet_print_detail.txt",
        "/interface list": "interface_list_print_detail.txt",
        "/interface list member": "interface_list_member_print_detail.txt",
        "/interface vlan": "interface_vlan_print_detail.txt",
        "/ip address": "ip_address_print_detail.txt",
        "/ip dhcp-server": "ip_dhcp_server_print_detail.txt",
        "/ip dhcp-server lease": "ip_dhcp_server_lease_print_detail.txt",
        "/ip dhcp-server network": "ip_dhcp_server_network_print_detail.txt",
        "/ip dns": "ip_dns_print.txt",
        "/ip firewall address-list": "ip_firewall_address_list_print_detail.txt",
        "/ip firewall filter": "ip_firewall_filter_print_detail.txt",
        "/ip firewall nat": "ip_firewall_nat_print_detail.txt",
        "/ip pool": "ip_pool_print_detail.txt",
        "/ip service": "ip_service_print_detail.txt",
        "/snmp": "snmp_print.txt",
        "/snmp community": "snmp_community_print_detail.txt",
        "/system clock": "system_clock.txt",
        "/system identity": "system_identity.txt",
        "/system package update": "system_package.txt",
        "/tool mac-server": "tool_mac_server.txt",
        "/tool mac-server mac-winbox": "tool_mac_server_mac_winbox.txt",
    }
    for section, filename in mapping.items():
        rows = commands.get(section, [])
        if not rows:
            continue
        lines = [f"# Derived from sanitized RouterOS export section {section}"]
        for idx, row in enumerate(rows):
            raw = row.get("_raw", "")
            flags = "X " if row.get("disabled") == "yes" else "  "
            lines.append(f"{idx} {flags}{raw}")
        write_text(RAW / "routeros" / filename, "\n".join(lines))

    not_provided = [
        "interface_print_detail.txt",
        "interface_bridge_host_print_detail.txt",
        "ip_arp_print_detail.txt",
        "ip_neighbor_print_detail.txt",
        "ip_route_print_detail.txt",
        "routing_route_print_detail.txt",
        "routing_table_print_detail.txt",
        "system_resource.txt",
        "system_routerboard.txt",
    ]
    note = "# Not provided by sanitized RouterOS export baseline 2026-09-15"
    for filename in not_provided:
        write_text(RAW / "routeros" / filename, note)


def ros_disabled(row: dict[str, Any]) -> bool:
    return str(row.get("disabled", "no")).lower() == "yes" or row.get("_flags") == "X"


def parse_router_export(raw_text: str, facts: dict[str, Any]) -> dict[str, Any]:
    commands = routeros_export_commands(raw_text)
    write_routeros_export_raw(commands, raw_text)

    header_model = re.search(r"(?im)^#\s*model\s*=\s*(.+)$", raw_text)
    header_serial = re.search(r"(?im)^#\s*serial number\s*=\s*(.+)$", raw_text)
    header_version = re.search(r"(?im)^# .* by RouterOS\s+([0-9.]+)", raw_text)
    identity_rows = commands.get("/system identity", [])
    clock_rows = commands.get("/system clock", [])
    package_rows = commands.get("/system package update", [])
    bridge_rows = commands.get("/interface bridge", [])
    vlan_interfaces = commands.get("/interface vlan", [])
    addresses = commands.get("/ip address", [])
    pools = commands.get("/ip pool", [])
    dhcp_servers = commands.get("/ip dhcp-server", [])
    dhcp_networks = commands.get("/ip dhcp-server network", [])
    dhcp_leases = commands.get("/ip dhcp-server lease", [])
    bridge_ports = commands.get("/interface bridge port", [])
    bridge_vlans = commands.get("/interface bridge vlan", [])
    interfaces = commands.get("/interface ethernet", []) + commands.get("/interface pppoe-client", []) + vlan_interfaces
    firewall_filters = commands.get("/ip firewall filter", [])
    firewall_nat = commands.get("/ip firewall nat", [])
    address_lists = commands.get("/ip firewall address-list", [])
    ip_services = commands.get("/ip service", [])
    snmp_rows = commands.get("/snmp", [])
    snmp_communities = commands.get("/snmp community", [])
    neighbor = commands.get("/ip neighbor discovery-settings", [])

    for rows in (interfaces, bridge_ports, bridge_vlans, dhcp_leases):
        for row in rows:
            for key in ("mac-address", "active-mac-address"):
                if key in row:
                    row[key] = norm_mac(row[key])

    address_by_interface = {a.get("interface"): a for a in addresses if a.get("interface")}
    dhcp_by_network = {d.get("address"): d for d in dhcp_networks if d.get("address")}
    server_by_interface = {d.get("interface"): d for d in dhcp_servers if d.get("interface")}
    pool_by_name = {p.get("name"): p for p in pools if p.get("name")}

    vlans: list[dict[str, Any]] = []
    for vlan in vlan_interfaces:
        iface = vlan.get("name", NA)
        ip_addr = address_by_interface.get(iface, {})
        gateway = ip_addr.get("address", NA)
        network_key = NA
        if gateway != NA:
            try:
                network_key = str(ipaddress.ip_interface(gateway).network)
            except ValueError:
                network = ip_addr.get("network", "")
                prefix = gateway.split("/", 1)[1] if "/" in gateway else ""
                network_key = f"{network}/{prefix}" if network and prefix else network or NA
        dhcp_network = dhcp_by_network.get(network_key, {})
        server = server_by_interface.get(iface, {})
        pool = pool_by_name.get(server.get("address-pool"), {})
        vlans.append(
            {
                "id": vlan.get("vlan-id", NA),
                "name": iface,
                "parent": vlan.get("interface", NA),
                "gateway": gateway,
                "network": network_key,
                "dhcp_server": server.get("name", NA),
                "dhcp_pool": server.get("address-pool", NA),
                "dhcp_pool_range": pool.get("ranges", NA),
                "dhcp_dns": dhcp_network.get("dns-server", NA),
                "domain": dhcp_network.get("domain", NA),
            }
        )

    channel = package_rows[0].get("channel") if package_rows else ""
    version = facts.get("routeros_version") or (header_version.group(1) if header_version else NA)
    if channel and version != NA and channel not in version:
        version = f"{version} {channel}"
    vlan90 = next((v for v in vlans if str(v.get("id")) == "90"), {})
    vlan30 = next((v for v in vlans if str(v.get("id")) == "30"), {})
    management_ip = vlan90.get("gateway", vlan30.get("gateway", NA))
    if management_ip != NA:
        management_ip = management_ip.split("/", 1)[0]

    return {
        "device": {
            "name": identity_rows[0].get("name", "RT-SN-003") if identity_rows else "RT-SN-003",
            "platform": "MikroTik",
            "board_name": "hEX" if (header_model and "RB750Gr3" in header_model.group(1)) else NA,
            "model": header_model.group(1).strip() if header_model else NA,
            "serial": header_serial.group(1).strip() if header_serial else facts.get("router_serial", NA),
            "routeros_version": version,
            "firmware_current": NA,
            "firmware_available": NA,
            "uptime": NA,
            "cpu": NA,
            "memory_total": NA,
            "management_ip": management_ip,
            "timezone": clock_rows[0].get("time-zone-name", facts.get("router_timezone", NA)) if clock_rows else facts.get("router_timezone", NA),
            "wan": facts.get("router_wan", "PPPoE em ether1-Link-WaveMax"),
        },
        "interfaces": interfaces,
        "bridge": bridge_rows[0] if bridge_rows else {},
        "bridge_ports": bridge_ports,
        "bridge_vlans": bridge_vlans,
        "bridge_hosts": [],
        "vlans": vlans,
        "pools": pools,
        "ip_addresses": addresses,
        "routes": [],
        "dns": commands.get("/ip dns", [{}])[0] if commands.get("/ip dns") else {},
        "dhcp_servers": dhcp_servers,
        "dhcp_networks": dhcp_networks,
        "dhcp_leases": dhcp_leases,
        "arp": [],
        "ip_services": ip_services,
        "address_lists": address_lists,
        "firewall_filters": firewall_filters,
        "firewall_nat": firewall_nat,
        "snmp": snmp_rows[0] if snmp_rows else {},
        "snmp_communities": snmp_communities,
        "neighbor_discovery": neighbor[0] if neighbor else {},
        "ntp_client_enabled": bool(commands.get("/system ntp client") or commands.get("/system ntp client servers")),
        "collection_warnings": [
            "RouterOS facts derived from sanitized export base_line-RT.rsc; operational ARP/MAC/route counters were not part of this baseline."
        ],
    }


def parse_router(raw_text: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
    facts = facts or {}
    if "/interface bridge" in raw_text and "NETINV_BEGIN" not in raw_text:
        return parse_router_export(raw_text, facts)

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


def parse_vlans_from_config(config: str, ports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    vlans: list[dict[str, Any]] = []
    for match in re.finditer(r"(?ms)^vlan\s+(\d+)\n(.*?)(?=^!$|^vlan\s+|\Z)", config):
        vlan_id = match.group(1)
        body = match.group(2)
        name = re.search(r"^\s*name\s+(.+)$", body, flags=re.M)
        vlans.append(
            {
                "id": vlan_id,
                "name": name.group(1).strip() if name else f"VLAN{vlan_id}",
                "status": "active",
                "ports": [
                    p["interface"]
                    for p in ports.values()
                    if str(p.get("access_vlan")) == vlan_id and p.get("mode") == "access" and not p.get("shutdown")
                ],
            }
        )
    return vlans


def poe_state(interface_body: str) -> str:
    return "off" if re.search(r"^\s*power inline never$", interface_body, flags=re.M) else "auto"


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
            "mode": mode.group(1).strip() if mode else ("routed" if key == "Fa0" else NA),
            "access_vlan": access.group(1) if access else NA,
            "trunk_allowed_vlans": allowed.group(1).strip() if allowed else NA,
            "native_vlan": native.group(1) if native else ("1" if mode and mode.group(1) == "trunk" else NA),
            "native_vlan_explicit": bool(native),
            "shutdown": bool(re.search(r"^\s*shutdown$", body, flags=re.M)),
            "portfast": bool(re.search(r"^\s*spanning-tree portfast", body, flags=re.M)),
            "bpduguard": bool(re.search(r"^\s*spanning-tree bpduguard enable", body, flags=re.M)),
            "nonegotiate": bool(re.search(r"^\s*switchport nonegotiate", body, flags=re.M)),
            "poe": poe_state(body),
        }
    return ports


def synthesize_switch_status(config_ports: dict[str, dict[str, Any]], facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    connected_names = {
        "UPLINK_RT-SN-003",
        "PROXMOX_HOST0",
        "PROXMOX_HOST1",
        "PROXMOX_HOST2",
        "PROXMOX_HOST3",
        "AP_GUEST_01_HUAWEI-BE3",
        "AP_GUEST_02_TPLink",
    }
    speed_overrides = facts.get("port_speeds", {})
    rows: dict[str, dict[str, Any]] = {}
    for key, port in config_ports.items():
        desc = str(port.get("description", ""))
        connected = desc in connected_names
        shutdown = bool(port.get("shutdown"))
        mode = port.get("mode", NA)
        if shutdown:
            status = "disabled"
        elif connected:
            status = "connected"
        elif desc.startswith(("RESERVED", "UNUSED")):
            status = "notconnect"
        else:
            status = NA
        if mode == "trunk" and status == "connected":
            vlan = "trunk"
        elif port.get("access_vlan") != NA:
            vlan = port.get("access_vlan")
        else:
            vlan = mode
        speed = speed_overrides.get(key)
        if not speed and status == "connected" and key.startswith("Gi"):
            speed = "1G"
        rows[key] = {
            "interface": key,
            "name": desc,
            "status": status,
            "vlan": vlan,
            "duplex": "full" if status == "connected" else "auto",
            "speed": speed or ("auto" if shutdown or status == "notconnect" else NA),
            "type": "10/100/1000BaseTX" if key.startswith("Gi") else "10/100BaseTX" if key.startswith("Fa") else NA,
        }
    return rows


def write_switch_synthetic_raw(
    raw_text: str,
    sections: dict[str, str],
    switch: dict[str, Any],
    config_ports: dict[str, dict[str, Any]],
    statuses: dict[str, dict[str, Any]],
) -> None:
    write_text(RAW / "switch.stream", raw_text)
    write_text(RAW / "switch.session", raw_text)
    running = sections.get("show running-config", raw_text)
    write_text(RAW / "switch" / "show_running_config.txt", running)
    write_text(RAW / "switch" / "show_startup_config.txt", "# Not provided by 2026-09-15 baseline")
    sdev = switch["device"]
    write_text(
        RAW / "switch" / "show_version.txt",
        "\n".join(
            [
                "# Derived from sanitized 2026-09-15 operator baseline",
                f"Cisco IOS Software Version {sdev['ios_version']}",
                f"Model number                    : {sdev['model']}",
                f"System serial number            : {sdev['serial']}",
            ]
        ),
    )
    status_rows = ["Port      Name                 Status       Vlan       Duplex Speed Type"]
    for key in sorted(statuses, key=lambda x: (0 if x.startswith("Gi") else 1, [int(n) for n in re.findall(r"\d+", x)])):
        row = statuses[key]
        status_rows.append(
            f"{key:<9} {row.get('name', '')[:20]:<20} {row.get('status', NA):<12} {row.get('vlan', NA):<10} {row.get('duplex', NA):<6} {row.get('speed', NA):<5} {row.get('type', NA)}"
        )
    write_text(RAW / "switch" / "show_interfaces_status.txt", "\n".join(status_rows))

    switchport_rows: list[str] = []
    for key in sorted(config_ports, key=lambda x: (0 if x.startswith("Gi") else 1, [int(n) for n in re.findall(r"\d+", x)])):
        port = config_ports[key]
        switchport_rows.extend(
            [
                f"Name: {key}",
                "Switchport: Enabled" if port.get("mode") != "routed" else "Switchport: Disabled",
                f"Administrative Mode: {port.get('mode', NA)}",
                f"Access Mode VLAN: {port.get('access_vlan', NA)}",
                f"Trunking Native Mode VLAN: {port.get('native_vlan', NA)}",
                f"Trunking VLANs Enabled: {port.get('trunk_allowed_vlans', NA)}",
                "",
            ]
        )
    write_text(RAW / "switch" / "show_interfaces_switchport.txt", "\n".join(switchport_rows))

    vlan_rows = ["VLAN Name                             Status    Ports", "---- -------------------------------- --------- -------------------------------"]
    for vlan in switch.get("vlans", []):
        vlan_rows.append(f"{str(vlan.get('id')):<4} {vlan.get('name', ''):<32} {vlan.get('status', 'active'):<9} {', '.join(vlan.get('ports', []))}")
    write_text(RAW / "switch" / "show_vlan.txt", "\n".join(vlan_rows))
    write_text(RAW / "switch" / "show_vlan_brief.txt", "\n".join(vlan_rows))
    write_text(RAW / "switch" / "show_lldp_neighbors.txt", "# LLDP enabled in running-config; neighbor table was not provided in 2026-09-15 baseline")
    write_text(RAW / "switch" / "show_lldp_neighbors_detail.txt", "# LLDP enabled in running-config; detailed neighbor table was not provided in 2026-09-15 baseline")
    write_text(RAW / "switch" / "show_cdp_neighbors_detail.txt", "# CDP disabled in running-config")
    write_text(
        RAW / "switch" / "show_spanning_tree.txt",
        "PVST enabled; switch priority 24576 for VLANs 30,60,90,130 per running-config. RouterOS bridge-core is protocol-mode=none, so Cisco-RB is an STP boundary.",
    )
    not_provided = [
        "exit.txt",
        "show_arp.txt",
        "show_interfaces.txt",
        "show_interfaces_description.txt",
        "show_inventory.txt",
        "show_ip_interface.txt",
        "show_ip_route.txt",
        "show_lacp.txt",
        "show_mac_addr_table.txt",
        "show_mac_address_table.txt",
        "show_port.txt",
        "show_system.txt",
        "terminal_datadump.txt",
    ]
    note = "# Not provided by sanitized Cisco running-config baseline 2026-09-15"
    for filename in not_provided:
        write_text(RAW / "switch" / filename, note)


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


def parse_switch(raw_text: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
    facts = facts or {}
    sections = extract_switch_sections(raw_text)
    version = sections.get("show version", "")
    running = sections.get("show running-config", "")
    startup = sections.get("show startup-config", "")
    if not running and "show running-config" in raw_text:
        running = raw_text
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
    if not statuses and config_ports:
        statuses = synthesize_switch_status(config_ports, facts)
    mac_table = parse_mac_table(sections.get("show mac address-table", ""))
    cdp = parse_cdp(sections.get("show cdp neighbors detail", ""))
    vlans = parse_vlans(sections.get("show vlan brief", sections.get("show vlan", "")))
    if not vlans and running:
        vlans = parse_vlans_from_config(running, config_ports)

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

    switch = {
        "device": {
            "hostname": hostname.group(1) if hostname else "SW-SN-03",
            "management_ip": svi.group(1) if svi else str(facts.get("switch_management", "10.100.90.99")).split("/", 1)[0],
            "default_gateway": gateway.group(1) if gateway else facts.get("switch_gateway", NA),
            "platform": "Cisco Catalyst 2960XR",
            "model": model.group(1).strip() if model else facts.get("switch_model", NA),
            "serial": serial.group(1).strip() if serial else facts.get("switch_serial", NA),
            "base_mac": base_mac.group(1).strip() if base_mac else NA,
            "ios_version": ios.group(1).strip() if ios else facts.get("switch_ios", NA),
            "uptime": uptime.group(2).strip() if uptime else NA,
            "dns": facts.get("switch_dns", NA),
            "ntp": facts.get("switch_ntp", NA),
            "timezone": facts.get("switch_timezone", NA),
        },
        "ports": list(ports.values()),
        "ports_by_name": ports,
        "vlans": vlans,
        "mac_table": mac_table,
        "cdp_neighbors": cdp,
        "running_config_differs_from_startup": bool(startup.strip()) and running.strip() != startup.strip(),
        "lldp_enabled": bool(re.search(r"^lldp run$", running, flags=re.M))
        or "% LLDP is not enabled" not in sections.get("show lldp neighbors", "% LLDP is not enabled"),
        "cdp_enabled": not bool(re.search(r"^no cdp run$", running, flags=re.M)),
        "http_enabled": bool(re.search(r"^ip http server$", running, flags=re.M)),
        "https_enabled": bool(re.search(r"^ip http secure-server$", running, flags=re.M)),
        "service_password_encryption": bool(re.search(r"^service password-encryption$", running, flags=re.M)),
        "vtp_mode": re.search(r"^vtp mode\s+(\S+)", running, flags=re.M).group(1)
        if re.search(r"^vtp mode\s+(\S+)", running, flags=re.M)
        else NA,
        "stp_summary": "PVST; priority 24576 for VLANs 30,60,90,130"
        if "spanning-tree vlan 30,60,90,130 priority 24576" in running
        else NA,
        "ssh_mgmt_acl": "SSH_MGMT_ONLY" if "ip access-list standard SSH_MGMT_ONLY" in running else NA,
        "snmp_mode": "v3 authPriv read-only via SNMP_ZABBIX_ONLY"
        if "snmp-server group ZABBIX_V3 v3 priv" in running
        else NA,
        "orphan_acl_10": bool(re.search(r"^access-list\s+10\s+permit\s+10\.100\.30\.60$", running, flags=re.M)),
        "motd_truncated": "banner motd ^Coggin ^" in running or "Este sistema e de uso exc^C" in running,
        "raw_running_config": running,
        "raw_sections": sorted(sections),
    }
    if raw_text and "show running-config" in raw_text:
        write_switch_synthetic_raw(raw_text, sections, switch, config_ports, statuses)
    return switch


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

    host_port_by_name: dict[str, str] = {}
    for port in switch.get("ports", []):
        desc = str(port.get("description") or port.get("oper_name") or "").upper()
        m = re.search(r"PROXMOX[_-]?HOST[-_]?(\d+)", desc)
        if m:
            host_port_by_name[f"host{m.group(1)}"] = port.get("interface", NA)

    node_meta = {n.get("name"): n for n in prox_nodes if n.get("name")}
    prox_nodes_net = prox_net.get("nodes", {}) if isinstance(prox_net, dict) else {}
    node_links: list[dict[str, Any]] = []
    for node, net_data in sorted(prox_nodes_net.items()):
        ip = net_data.get("management_ip") or node_meta.get(node, {}).get("corosync_ring0_addr") or NA
        arp = arp_by_ip.get(ip, {})
        mac = norm_mac(arp.get("mac-address"))
        entries = mac_entries.get(mac, [])
        port = entries[0]["port"] if entries else host_port_by_name.get(node, NA)
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

    def add(level: str, title: str, evidence: str, impact: str, recommendation: str, finding_id: str) -> None:
        findings.append(
            {
                "level": level,
                "id": finding_id,
                "title": title,
                "evidence": evidence,
                "impact": impact,
                "recommendation": recommendation,
            }
        )

    filters = router.get("firewall_filters", [])
    drop_input_disabled = any(
        row.get("chain") == "input"
        and row.get("action") == "drop"
        and "DROP GERAL" in str(row.get("comment", ""))
        and ros_disabled(row)
        for row in filters
    )
    if drop_input_disabled:
        add(
            "CRITICAL",
            "RB input firewall: DROP GERAL disabled",
            "RouterOS export mostra chain=input action=drop comment=\"DROP GERAL\" disabled=yes.",
            "Sem drop final ativo, trafego ao plano de controle da RB que nao casa com regras anteriores pode ser aceito por padrao.",
            "Auditar /ip service print detail, restringir servicos administrativos e aplicar default-deny seguro em Safe Mode.",
            "RB-FW-001",
        )

    forward_has_drop = any(row.get("chain") == "forward" and row.get("action") in {"drop", "reject"} and not ros_disabled(row) for row in filters)
    if not forward_has_drop:
        add(
            "HIGH",
            "RB forward policy sem default-deny explicito",
            "Export contem accepts/fasttrack na chain forward, mas nao contem regra final drop/reject ativa.",
            "VLANs separam L2, mas nao provam isolamento L3 entre redes quando forward fica aceito por padrao.",
            "Definir matriz de fluxos inter-VLAN e implantar default-deny gradual, preservando fluxos necessarios.",
            "RB-FW-002",
        )

    static_ips: set[str] = set()
    for vlan in router.get("vlans", []):
        gw = str(vlan.get("gateway", "")).split("/", 1)[0]
        if gw:
            static_ips.add(gw)
    static_ips.add(str(switch.get("device", {}).get("management_ip", "")))
    for node in topology.get("proxmox_nodes", []):
        static_ips.add(str(node.get("management_ip", "")).split("/", 1)[0])
    for workload in topology.get("workloads", []):
        ip_value = str(workload.get("ip", "")).split("/", 1)[0]
        if ip_value and ip_value != NA:
            static_ips.add(ip_value)
    for row in router.get("address_lists", []):
        address = str(row.get("address", ""))
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+(?:/\d+)?", address):
            static_ips.add(address.split("/", 1)[0])

    active_pool_names = {row.get("address-pool") for row in router.get("dhcp_servers", []) if row.get("address-pool")}
    active_overlap_pool_names = {
        vlan.get("dhcp_pool")
        for vlan in router.get("vlans", [])
        if str(vlan.get("id")) in {"30", "60", "90"} and vlan.get("dhcp_pool")
    }
    overlaps: list[str] = []
    for pool in router.get("pools", []):
        if pool.get("name") not in active_overlap_pool_names:
            continue
        ranges = str(pool.get("ranges", ""))
        if not ranges:
            continue
        for part in ranges.split(","):
            if "-" not in part:
                continue
            start, end = [p.strip() for p in part.split("-", 1)]
            try:
                start_ip = ipaddress.ip_address(start)
                end_ip = ipaddress.ip_address(end)
            except ValueError:
                continue
            hits = sorted(
                ip
                for ip in static_ips
                if ip and ip != NA and start_ip <= ipaddress.ip_address(ip) <= end_ip
            )
            if hits:
                overlaps.append(f"{pool.get('name')} {part}: {', '.join(hits[:8])}")
    if overlaps:
        add(
            "HIGH",
            "DHCP pools sobrepoem IPs estaticos",
            "; ".join(overlaps[:3]),
            "DHCP pode entregar endereco ja usado por PVE, Tailscale, Zabbix, Pi-hole, switch ou gateways.",
            "Separar faixas dinamicas das reservas/estaticos e revisar leases antes da mudanca.",
            "RB-DHCP-001",
        )

    community_sources = sorted({row.get("addresses", NA) for row in router.get("snmp_communities", []) if row.get("addresses")})
    firewall_sources = sorted(
        {
            row.get("src-address", NA)
            for row in filters
            if row.get("chain") == "input" and row.get("protocol") == "udp" and row.get("dst-port") == "161"
        }
    )
    if community_sources and firewall_sources and set(community_sources) != set(firewall_sources):
        add(
            "MEDIUM",
            "RB SNMP community difere da origem liberada no firewall",
            f"Community addresses={', '.join(community_sources)}; firewall UDP/161 src-address={', '.join(firewall_sources)}.",
            "O poller real pode nao casar com a community ou a regra pode permitir uma origem diferente da pretendida.",
            "Confirmar IP do Zabbix, alinhar a origem e migrar a RB para SNMPv3 authPriv.",
            "RB-SNMP-001",
        )

    if not router.get("ntp_client_enabled"):
        add(
            "MEDIUM",
            "RB NTP client disabled",
            "O export nao contem cliente NTP/SNTP ativo; o resumo tecnico valida NTP client desabilitado.",
            "Relogio sem sincronismo confiavel prejudica correlacao de logs e auditoria.",
            "Habilitar NTP/SNTP com fontes confiaveis e validar timezone America/Cuiaba.",
            "RB-NTP-001",
        )

    dns_by_vlan = {str(v.get("id")): str(v.get("dhcp_dns", NA)) for v in router.get("vlans", [])}
    if len(set(dns_by_vlan.values())) > 1:
        add(
            "MEDIUM",
            "DNS DHCP inconsistente entre VLANs",
            ", ".join(f"VLAN {vid}: {dns}" for vid, dns in sorted(dns_by_vlan.items(), key=lambda x: int(x[0]))),
            "VLANs 30/60/90 usam DNS publico enquanto VLAN130 usa Pi-hole e anti-bypass, dificultando observabilidade e politica unica.",
            "Definir politica DNS por VLAN; se Pi-hole for padrao, alinhar DHCP e NAT anti-bypass para as VLANs aplicaveis.",
            "RB-DNS-001",
        )

    discovery = router.get("neighbor_discovery", {}).get("discover-interface-list")
    if discovery == "!interfaces-secure":
        add(
            "REVIEW",
            "Neighbor discovery usa lista invertida",
            "Export contem discover-interface-list=!interfaces-secure.",
            "A expressao parece inversa ao nome da lista e pode expor descoberta em interfaces nao administrativas.",
            "Validar intencao no RouterOS antes de alterar; limitar descoberta somente onde for necessario.",
            "RB-DISC-001",
        )

    legacy = sorted(
        p.get("name", "")
        for p in router.get("pools", [])
        if p.get("name") and p.get("name") not in active_pool_names
    )
    if legacy:
        add(
            "LOW",
            "Pools DHCP legados aparentemente nao usados",
            "Pools nao referenciados por DHCP servers ativos: " + ", ".join(legacy) + ".",
            "Residuos aumentam ambiguidade operacional e risco de reuso indevido.",
            "Confirmar ausencia de dependencias e remover em mudanca separada.",
            "RB-POOL-001",
        )

    support_populated = any(row.get("address-list") == "rede-suporte" for row in filters if row.get("action") == "add-src-to-address-list")
    support_accept = any(
        row.get("src-address-list") == "rede-suporte" and row.get("action") == "accept" for row in filters
    )
    if support_populated and not support_accept:
        add(
            "LOW",
            "Port-knocking popula rede-suporte sem accept correspondente",
            "Regras adicionam pre-rede-suporte/rede-suporte, mas o export nao mostra regra action=accept usando rede-suporte.",
            "O fluxo de suporte pode estar incompleto ou apenas acumulando listas sem efeito pratico.",
            "Revisar a intencao; concluir o fluxo de accept ou remover as regras orfas.",
            "RB-KNOCK-001",
        )

    if switch.get("orphan_acl_10"):
        add(
            "LOW",
            "Cisco ACL 10 orfa apos remocao do SNMPv2c",
            "running-config ainda contem access-list 10 permit 10.100.30.60, enquanto SNMP usa SNMP_ZABBIX_ONLY.",
            "Configuracao residual aumenta ruido e pode confundir auditorias futuras.",
            "Remover ACL 10 apos confirmar que nao ha referencia remanescente.",
            "SW-CLEAN-001",
        )

    if switch.get("motd_truncated"):
        add(
            "LOW",
            "Cisco banner MOTD truncado/malformado",
            "running-config mostra banner motd com delimitador/texto truncado; banner login esta integro.",
            "Nao afeta encaminhamento, mas deixa a configuracao administrativa inconsistente.",
            "Remover o MOTD ou recria-lo com delimitador limpo e texto unico aprovado.",
            "SW-BANNER-001",
        )

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["level"], 99), f.get("id", "")))
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
    severity_counts = {level: sum(1 for f in findings if f["level"] == level) for level in SEVERITY_ORDER}

    vlan_rows = []
    for vlan in sorted(router.get("vlans", []), key=lambda v: int(v.get("id", 9999))):
        vlan_rows.append(
            [
                vlan.get("id"),
                vlan.get("name"),
                vlan.get("network"),
                vlan.get("gateway"),
                vlan.get("dhcp_server"),
                vlan.get("dhcp_pool"),
                vlan.get("dhcp_pool_range"),
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
                "shutdown" if p.get("shutdown") else "enabled",
                p.get("oper_status"),
                p.get("mode"),
                p.get("access_vlan"),
                p.get("trunk_allowed_vlans"),
                p.get("native_vlan"),
                p.get("oper_speed"),
                p.get("poe"),
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

    finding_rows = [
        [f.get("level"), f.get("id"), f.get("title"), f.get("evidence"), f.get("recommendation")]
        for f in findings
    ]

    docs = [
        "# Network Inventory - Homelab",
        "",
        "## 1. Baseline executivo",
        "",
        "- Baseline pos-padronizacao validado em 15/09/2026.",
        f"- Gateway/L3: {rdev['name']} ({rdev['model']}, RouterOS {rdev['routeros_version']}).",
        f"- Core L2: {sdev['hostname']} ({sdev['model']}, IOS {sdev['ios_version']}).",
        f"- VLANs funcionais: {', '.join(v.get('id', NA) for v in router.get('vlans', []))}; VLAN 999 e native/blackhole no Cisco.",
        "- Uplink RB-Cisco: ether3-switch para Gi1/0/1, 802.1Q 30/60/90/130, native 999 no Cisco e RB tagged-only.",
        "- Trunks Proxmox: Gi1/0/3 host2, Gi1/0/5 host3, Gi1/0/6 host1, Gi1/0/15 host0; allowed 30,60 e native 999.",
        "- STP: Cisco PVST root para VLANs 30/60/90/130; RouterOS bridge-core protocol-mode=none. O enlace Cisco-RB e uma fronteira STP.",
        f"- Portas conectadas no switch: {len(connected_ports)}",
        f"- Hosts Proxmox mapeados no switch: {len([n for n in topology['proxmox_nodes'] if n['switch_port'] != NA])}/{len(topology['proxmox_nodes'])}",
        f"- Workloads Proxmox preservados do inventario PVE: {len({w['id'] for w in topology['workloads']})}",
        f"- Findings abertos: {severity_counts['CRITICAL']} critical, {severity_counts['HIGH']} high, {severity_counts['MEDIUM']} medium, {severity_counts['REVIEW']} review, {severity_counts['LOW']} low.",
        "",
        "Fontes primarias: `Base_line-SW.txt` (running-config Cisco), `base_line-RT.rsc` (RouterOS export) e `network-baseline-2026-09-15.md` como criterio tecnico. Segredos, hashes, PPPoE user, SNMP communities/trap-community e e-mail foram redigidos antes de gravar artefatos.",
        "",
        "## 2. MikroTik RT-SN-003",
        "",
        md_table(
            ["Campo", "Valor"],
            [
                ["Nome", rdev["name"]],
                ["IP de gerenciamento preferencial", rdev["management_ip"]],
                ["Modelo", f"{rdev['board_name']} / {rdev['model']}"],
                ["Serial", rdev["serial"]],
                ["RouterOS", rdev["routeros_version"]],
                ["Firmware atual/disponivel", f"{rdev['firmware_current']} / {rdev['firmware_available']}"],
                ["WAN", rdev.get("wan", NA)],
                ["Bridge", f"{router.get('bridge', {}).get('name', 'bridge-core')} vlan-filtering={router.get('bridge', {}).get('vlan-filtering', NA)} frame-types={router.get('bridge', {}).get('frame-types', NA)} pvid={router.get('bridge', {}).get('pvid', NA)} protocol-mode={router.get('bridge', {}).get('protocol-mode', NA)}"],
                ["Timezone", rdev.get("timezone", NA)],
                ["NTP client", "enabled" if router.get("ntp_client_enabled") else "disabled"],
                ["SNMP", "enabled; community redigida; revisar migracao para v3" if router.get("snmp", {}).get("enabled") == "yes" else NA],
            ],
        ),
        "",
        "### VLANs roteadas / DHCP",
        "",
        md_table(["VLAN", "Interface", "Rede", "Gateway", "DHCP", "Pool", "Range", "DNS entregue"], vlan_rows),
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
        "## 3. Cisco SW-SN-03",
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
                ["CDP", "habilitado" if switch.get("cdp_enabled") else "desabilitado"],
                ["HTTP/HTTPS", f"{'on' if switch.get('http_enabled') else 'off'} / {'on' if switch.get('https_enabled') else 'off'}"],
                ["VTP", switch.get("vtp_mode", NA)],
                ["STP", switch.get("stp_summary", NA)],
                ["SSH", f"v2; ACL {switch.get('ssh_mgmt_acl', NA)}"],
                ["SNMP", switch.get("snmp_mode", NA)],
                ["DNS", sdev.get("dns", NA)],
                ["NTP", sdev.get("ntp", NA)],
            ],
        ),
        "",
        "### Portas do switch",
        "",
        md_table(["Porta", "Descricao", "Admin", "Status", "Modo", "Access", "Allowed", "Native", "Speed", "PoE"], switch_rows),
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
        "### VLAN 999 / blackhole",
        "",
        "A VLAN 999 existe no Cisco como native/blackhole para trunks e portas inutilizadas. Ela nao possui SVI/L3 funcional na RB no baseline atual.",
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
        "## 7. Findings abertos",
        "",
        md_table(["Severidade", "ID", "Finding", "Evidencia", "Recomendacao"], finding_rows),
        "",
        "## 8. Observacoes de relacionamento",
        "",
        "- A RB RT-SN-003 chega ao switch pela porta Gi1/0/1, associada ao ether3-switch/bridge-core.",
        "- VLANs 30, 60, 90 e 130 passam no trunk RB-Cisco; VLAN 999 e somente native/blackhole no Cisco.",
        "- VLAN 130 aparece segmentada para AP/guest e nao aparece permitida nos trunks Proxmox.",
        "- O export atual da RB nao traz ARP/MAC operacional; por isso os hosts PVE sao ligados as portas pelo baseline Cisco e os fatos PVE ja existentes.",
        "- O comportamento do storage hd1tb visto no cluster Proxmox continua fora do escopo deste baseline de rede.",
        "",
        "## 9. Arquivos de origem",
        "",
        "- Fontes sanitizadas: `Base_line-SW.txt`, `base_line-RT.rsc`, `network-baseline-2026-09-15.md`",
        "- Raw RouterOS sanitizado: `raw/routeros.stream` e `raw/routeros/*.txt`",
        "- Raw switch sanitizado/derivado: `raw/switch.stream` e `raw/switch/*.txt`",
        "- Dados tratados: `data/*.json`",
        "- Topologia: `topology-current.md`",
        "- Findings: `findings.md`",
    ]
    write_text(ROOT / "network-inventory.md", "\n".join(docs))

    readme = [
        "# Network Inventory",
        "",
        "Inventario da infraestrutura de rede do homelab com baseline pos-padronizacao validado em 15/09/2026.",
        "",
        "O estado atual foi regenerado a partir do running-config Cisco `SW-SN-03`, export RouterOS `RT-SN-003` e resumo tecnico `network-baseline-2026-09-15.md`. Os raw/configs publicados foram sanitizados antes de serem gravados.",
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
        "O baseline cobre RB MikroTik, switch Cisco, VLANs, trunks, management plane e relacao com dados ja inventariados do Proxmox. Nenhum comando de alteracao foi executado por este gerador.",
    ]
    write_text(ROOT / "README.md", "\n".join(readme))

    finding_lines = [
        "# Network Findings",
        "",
        "Findings atuais do baseline 15/09/2026. Findings legados sobre IOS antigo, link host0 degradado, VLANs removidas, web management Cisco, password-encryption, LLDP, trunks inconsistentes e running/startup divergente foram retirados por nao refletirem o baseline atual.",
        "",
    ]
    for f in findings:
        finding_lines.extend(
            [
                f"## [{f['level']}] {f.get('id', 'NO-ID')} - {f['title']}",
                "",
                f"- Evidencia: {f['evidence']}",
                f"- Impacto: {f['impact']}",
                f"- Recomendacao: {f['recommendation']}",
                "",
            ]
        )
    write_text(ROOT / "findings.md", "\n".join(finding_lines))

    write_topology_md(router, switch, topology)
    write_roadmap(router, switch, findings)


def write_roadmap(router: dict[str, Any], switch: dict[str, Any], findings: list[dict[str, str]]) -> None:
    rdev = router["device"]
    sdev = switch["device"]
    completed_rows = [
        ["Cisco IOS", f"Validado em {sdev.get('ios_version', NA)}; finding antigo de IOS removido."],
        ["VLANs legadas", "VLANs legadas removidas do baseline atual do switch."],
        ["Trunks Proxmox", "Gi1/0/3, Gi1/0/5, Gi1/0/6 e Gi1/0/15 padronizados com allowed 30,60 e native 999."],
        ["host0", "Gi1/0/15 validado em 1G apos troca de cabo."],
        ["LLDP/CDP", "LLDP habilitado e CDP desabilitado no Cisco."],
        ["Web management Cisco", "HTTP e HTTPS desabilitados."],
        ["SNMP Cisco", "v3 authPriv com ACL SNMP_ZABBIX_ONLY; v1/v2c removidos."],
        ["NTP/DNS Cisco", "NTP.br redundante e DNS via Pi-hole 10.100.60.71/72."],
    ]
    priority_rows = [
        [f["level"], f.get("id", ""), f["title"], f["recommendation"]]
        for f in findings
        if f["level"] in {"CRITICAL", "HIGH", "MEDIUM"}
    ]
    cleanup_rows = [
        [f["level"], f.get("id", ""), f["title"], f["recommendation"]]
        for f in findings
        if f["level"] in {"REVIEW", "LOW"}
    ]
    port_rows = [
        [
            p.get("interface"),
            p.get("description") or p.get("oper_name"),
            p.get("mode"),
            p.get("trunk_allowed_vlans"),
            p.get("native_vlan"),
            p.get("oper_speed"),
        ]
        for p in sorted(switch.get("ports", []), key=lambda x: (0 if x["interface"].startswith("Gi") else 1, [int(n) for n in re.findall(r"\d+", x["interface"])]))
        if str(p.get("description", "")).startswith(("UPLINK", "PROXMOX", "AP_GUEST"))
    ]
    text = [
        "# Homelab Standardization Roadmap",
        "",
        "Roadmap atualizado pelo baseline real de 15/09/2026. As etapas abaixo nao sao script de execucao; cada mudanca deve ter backup, janela e rollback.",
        "",
        "## 1. Baseline atual",
        "",
        md_table(
            ["Area", "Estado"],
            [
                ["Gateway", f"{rdev.get('name', NA)}, {rdev.get('model', NA)}, RouterOS {rdev.get('routeros_version', NA)}"],
                ["Switch", f"{sdev.get('hostname', NA)}, {sdev.get('model', NA)}, IOS {sdev.get('ios_version', NA)}"],
                ["VLANs funcionais", "30 PROXMOX, 60 SERVICES, 90 MGMT, 130 GUESTs"],
                ["Blackhole", "VLAN 999 como native/blackhole no Cisco, sem SVI/L3 funcional"],
                ["Uplink RB-Cisco", "ether3-switch <-> Gi1/0/1, tagged 30/60/90/130, STP boundary"],
                ["STP", "Cisco PVST root; RouterOS bridge-core protocol-mode=none"],
            ],
        ),
        "",
        "## 2. Concluido no baseline",
        "",
        md_table(["Item", "Resultado"], completed_rows),
        "",
        "## 3. Prioridades abertas",
        "",
        md_table(["Severidade", "ID", "Item", "Proxima acao"], priority_rows),
        "",
        "## 4. Revisao e limpeza",
        "",
        md_table(["Severidade", "ID", "Item", "Proxima acao"], cleanup_rows),
        "",
        "## 5. Mapa operacional de portas",
        "",
        md_table(["Porta", "Uso", "Modo", "Allowed", "Native", "Speed"], port_rows),
        "",
        "## 6. Sequencia segura sugerida",
        "",
        "1. Auditar `/ip service print detail` na RB e restringir management plane.",
        "2. Ativar default-deny seguro no input da RB em Safe Mode.",
        "3. Definir matriz inter-VLAN e aplicar default-deny forward gradual.",
        "4. Redesenhar pools DHCP para nao sobrepor IPs estaticos.",
        "5. Alinhar SNMP da RB ao Zabbix real e migrar para v3.",
        "6. Habilitar NTP/SNTP na RB.",
        "7. Unificar politica DNS/Pi-hole por VLAN.",
        "8. Limpar ACL 10 e corrigir/remover banner MOTD no Cisco.",
        "",
        "## 7. Guardrails",
        "",
        "- Cisco remoto: backup, `reload in`, alteracao pequena, validacao, `reload cancel`, `write memory`.",
        "- MikroTik remoto: export + backup, Safe Mode, alteracao pequena, validacao e saida limpa do Safe Mode.",
        "- Nao adicionar segundo link L2 Cisco-RB sem redesign de STP, preferencialmente MSTP comum.",
    ]
    write_text(ROOT / "standardization-roadmap.md", "\n".join(text))


def mermaid_id(prefix: str, value: str) -> str:
    return prefix + re.sub(r"[^A-Za-z0-9_]", "_", value)


def write_topology_md(router: dict[str, Any], switch: dict[str, Any], topology: dict[str, Any]) -> None:
    rdev = router["device"]
    sdev = switch["device"]
    physical = [
        "```mermaid",
        "flowchart LR",
        f'  INTERNET["Internet / ISP"] -->|"PPPoE"| RB["{rdev["name"]}\\nMikroTik {rdev["model"]}\\nL3 Gateway"]',
        f'  RB -- "ether3-switch <-> Gi1/0/1\\n802.1Q 30,60,90,130\\nSTP boundary" --> SW["{sdev["hostname"]}\\n{sdev["model"]}\\n{sdev["management_ip"]}"]',
    ]
    for node in topology["proxmox_nodes"]:
        if node["switch_port"] == NA:
            continue
        nid = mermaid_id("H_", node["node"])
        speed = NA
        for p in switch.get("ports", []):
            if p.get("interface") == node["switch_port"]:
                speed = p.get("oper_speed", NA)
                break
        physical.append(f'  SW -- "{node["switch_port"]} {speed}\\ntrunk 30,60 native 999" --> {nid}["{node["node"]}\\n{node["management_ip"]}"]')
    for port in switch.get("ports", []):
        desc = port.get("description") or port.get("oper_name") or ""
        if port.get("oper_status") == "connected" and "AP_GUEST" in desc:
            pid = mermaid_id("AP_", port["interface"])
            speed = port.get("oper_speed", NA)
            label = desc.replace("AP_GUEST_", "").replace("_", " ")
            physical.append(f'  SW -- "{port["interface"]} {speed}\\naccess VLAN 130" --> {pid}["{label}\\nGuest AP"]')
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
        "Baseline real de 15/09/2026. Mermaid usa apenas sintaxe suportada pelo GitHub.",
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
        "",
        "## 5. STP Boundary",
        "",
        "O Cisco opera PVST e e root das VLANs 30/60/90/130. A bridge-core da RB opera `protocol-mode=none`; portanto o link RB-Cisco e uma fronteira STP. Nao adicionar segundo enlace L2 sem redesign/MSTP.",
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
                "source": "proxmox inventory + switch baseline descriptions + router subnets",
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
                "source": "proxmox inventory + switch baseline descriptions + router subnets",
            }
        )
    with (ROOT / "inventory.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def preferred_source(primary: Path, fallback: Path) -> str:
    if primary.exists():
        text = read_text(primary)
        write_text(primary, text)
        return text
    return read_text(fallback)


def sanitize_workspace_sources() -> None:
    for path in (BASELINE_MD, ROOT / "Base_line-SW.txt", ROOT / "base_line-RT.rsc"):
        if path.exists():
            write_text(path, read_text(path))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    facts = baseline_facts()
    sanitize_workspace_sources()
    router = parse_router(preferred_source(ROOT / "base_line-RT.rsc", RAW / "routeros.stream"), facts)
    switch = parse_switch(preferred_source(ROOT / "Base_line-SW.txt", RAW / "switch.stream"), facts)
    prox_net = read_json(PROXMOX_DATA / "network.json", {})
    guests = read_json(PROXMOX_DATA / "guests.json", [])
    prox_nodes = read_json(PROXMOX_DATA / "nodes.json", [])
    storage = read_json(PROXMOX_DATA / "storage.json", {})
    topology = build_topology(router, switch, prox_net, guests, prox_nodes)
    findings = make_findings(router, switch, topology, storage)
    sanitize_raw_tree()

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
                "high": sum(1 for f in findings if f["level"] == "HIGH"),
                "medium": sum(1 for f in findings if f["level"] == "MEDIUM"),
                "review": sum(1 for f in findings if f["level"] == "REVIEW"),
                "low": sum(1 for f in findings if f["level"] == "LOW"),
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
    print(f"High findings: {sum(1 for f in findings if f['level'] == 'HIGH')}")
    print(f"Medium findings: {sum(1 for f in findings if f['level'] == 'MEDIUM')}")
    print(f"Critical findings: {sum(1 for f in findings if f['level'] == 'CRITICAL')}")
    print("")
    print(f"Report: {ROOT / 'network-inventory.md'}")
    print(f"Raw data: {RAW}")


if __name__ == "__main__":
    main()
