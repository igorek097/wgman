#!/usr/bin/python3
from subprocess import run, call, PIPE
import configparser
import sys, os


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


config = configparser.ConfigParser()


class WgEntity:
    
    def __init__(self, params:dict) -> None:
        self._params = params
        
    def get(self, param_name):
        return self._params.get(param_name, None)
        
    def set(self, param_name, value):
        self._params[param_name] = value
        
    def keys(self):
        return self._params.keys()
    
    def param_to_str(self, param_name):
        param = self._params[param_name]
        return f'{param_name} = {param}'


class WgInterface(WgEntity):
    
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        
        
class WgPeer(WgEntity):
    
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        

def generate_private_key() -> str:
    generate = run(['sudo', 'wg', 'genkey'], stdout=PIPE)
    return generate.stdout.decode().replace('\n', '')


def generate_public_key(private_key:str) -> str:
    generate = run(['sudo', 'echo', f'{private_key}'], stdout=PIPE)
    generate = run(['sudo', 'wg', 'pubkey'], input=generate.stdout, stdout=PIPE)
    return generate.stdout.decode().replace('\n', '')


def generate_preshared_key() -> str:
    generate = run(['sudo', 'wg', 'genpsk'], stdout=PIPE)
    return generate.stdout.decode().replace('\n', '')


def read_file(path):
    with open(path, 'r') as f:
        content = f.read()
    return content


def write_to_file(file_path:str, data:str):
    with open(file_path, 'a') as f:
        f.write(data)


def menu(items:list, prompt:str=None):
    if not prompt:
        prompt = f'Your choice'
    prompt += f' [1-{len(items)}]: '
    for i, item in enumerate(items):
        print(f'{i+1}. {item}')
    return input(prompt)


def parse_record(record, object_class):
    dct = {}
    for line in record.split('\n'):
        try:
            dct.update({line.split(' = ')[0]:line.split(' = ')[1]})
        except:
            continue
    return object_class(dct)


def get_interfaces(wg_dir):
    interfaces = []
    config_files = os.listdir(wg_dir)
    for config in config_files:
        if not config.endswith('.conf'):
            continue
        config_content = read_file(f'{wg_dir}/{config}')
        for record in config_content.split('\n\n'):
            if '[Interface]' in record:
                interface = parse_record(record, WgInterface)
                interface.name = config.split('.')[0]
                interface.peers = []
            if '[Peer]' in record:
                peer = parse_record(record, WgPeer)
                interface.peers.append(peer)
        interfaces.append(interface)
    return interfaces


def list_interfaces(interfaces):
    os.system('clear')
    for i, interface in enumerate(interfaces):
        print(f'{i+1}. {interface.name}')
    
    
def list_peers(interfaces):
    os.system('clear')
    choice = menu([i.name for i in interfaces], f'Please choose interface')
    interface = interfaces[int(choice)-1]
    for i, peer in enumerate(interface.peers):
        print(f'{i+1}. {peer.get("#Name")}')
                

def get_next_server_port(config, interfaces):
    if interfaces == []:
        return config['server']['start_listen_port']
    return max([int(interface.get('ListenPort')) for interface in interfaces]) + 1


def add_interface(config, interfaces):
    os.system('clear')
    interface_name = input('Please enter new interface unique name (default: "my-vlan" ): ') or 'my-vlan'
    initial_ip = input('Please enter initial IP address (default: 10.0.0.1): ') or '10.0.0.1'
    server_port = get_next_server_port(config, interfaces)
    server_private_key = generate_private_key()
    interface_config = INTERFACE_TEMPLATE.format(
        server_ip = initial_ip,
        server_port = server_port,
        server_private_key = server_private_key,
        server_pub_interface = config['server']['public_interface']
    )
    print(interface_config)
    config_path = os.path.join(config['wireguard']['wg_dir'], f'{interface_name}.conf')
    write_to_file(config_path, interface_config)


def get_next_ip(ip:str) -> str:
    if '/' in ip:
        ip = ip.split('/')[0]
    ip_lst = ip.split('.')
    ip_lst[-1] = str(int(ip_lst[-1]) + 1)
    return '.'.join(ip_lst)


def get_next_peer_ip(interface):
    if interface.peers == []:
        return get_next_ip(interface.get('Address'))
    return get_next_ip(interface.peers[-1].get('AllowedIPs'))
    

def get_subnet(ip:str):
    ip_lst = ip.split('.')
    ip_lst[-1] = '0'
    return '.'.join(ip_lst)


def add_peer(config, interfaces):
    os.system('clear')
    peer_name = input('Please enter new peer unique name: ')
    choice = menu([i.name for i in interfaces], f'Please choose interface to add this peer to')
    interface = interfaces[int(choice)-1]
    peer_private_key = generate_private_key()
    peer_public_key = generate_public_key(peer_private_key)
    peer_preshared_key = generate_preshared_key()
    peer_ip = get_next_peer_ip(interface)
    server_public_key = generate_public_key(interface.get('PrivateKey'))
    peer_interface_config = PEER_TEMPLATE.format(
        peer_name = peer_name,
        peer_public_key = peer_public_key,
        peer_preshared_key = peer_preshared_key,
        peer_ip=peer_ip
    )
    peer_client_config = CLIENT_CONFIG_TEMPLATE.format(
        peer_private_key = peer_private_key,
        peer_ip = peer_ip,
        server_public_key = server_public_key,
        peer_preshared_key = peer_preshared_key,
        server_public_ip = config['server']['public_ip'],
        server_port = interface.get('ListenPort'),
        subnet = get_subnet(peer_ip)
    )
    interface_config_path = os.path.join(config['wireguard']['wg_dir'], f'{interface.name}.conf')
    client_config_path = os.path.join(config['general']['client_conf_dir'], f'{interface.name}-{peer_name}.conf')
    write_to_file(interface_config_path, peer_interface_config)
    write_to_file(client_config_path, peer_client_config)
    

def get_main_menu(interfaces):
    menu_items = []
    if interfaces:
        menu_items.extend(['List peers', 'List interfaces', 'Add peer'])
    menu_items.extend(['Add interface', 'Exit'])
    return menu_items


if __name__ == "__main__":
    try:
        config.read('./wgman.cfg')
    except:
        print('Error reading wgman.cfg')
        quit()
    while True:
        interfaces = get_interfaces(config['wireguard']['wg_dir'])
        os.system('clear')
        menu_items = get_main_menu(interfaces)
        key = menu(menu_items)
        try:
            choice = menu_items[int(key)-1]
        except:
            continue
        if choice == 'List interfaces':
            list_interfaces(interfaces)
            input('Any key to go back...')
        if choice == 'List peers':
            list_peers(interfaces)
            input('Any key to go back...')
        if choice == 'Add interface':
            add_interface(config, interfaces)
        if choice == 'Add peer':
            add_peer(config, interfaces)
        if choice == 'Exit':
            break
    