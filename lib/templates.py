INTERFACE_TEMPLATE = """[Interface]
Address = {server_ip}/24
ListenPort = {server_port}
PrivateKey = {server_private_key}
PostUp = iptables -I INPUT -p udp --dport {server_port} -j ACCEPT; iptables -I FORWARD -i {server_pub_interface} -o %i -j ACCEPT; iptables -I FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {server_pub_interface} -j MASQUERADE
PostDown = iptables -D INPUT -p udp --dport {server_port} -j ACCEPT; iptables -D FORWARD -i {server_pub_interface} -o %i -j ACCEPT; iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {server_pub_interface} -j MASQUERADE
"""

PEER_TEMPLATE = """
[Peer]
#Name = {peer_name}
PublicKey = {peer_public_key}
PresharedKey = {peer_preshared_key}
AllowedIPs = {peer_ip}/32
PersistentKeepalive = 25
"""

CLIENT_CONFIG_TEMPLATE = """[Interface]
PrivateKey = {peer_private_key}
Address = {peer_ip}/32

[Peer]
PublicKey = {server_public_key}
PresharedKey = {peer_preshared_key}
Endpoint = {server_public_ip}:{server_port}
AllowedIPs = {subnet}/24
PersistentKeepalive = 25
"""