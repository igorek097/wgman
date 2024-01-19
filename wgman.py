#!/usr/bin/python3
from configparser import ConfigParser
from os import system, listdir
from os.path import join, basename, dirname

from lib.templates import *
from lib.wireguard import *
from lib.tools import *
from lib.menu import *
from lib import validators
from lib.styling import colors, fonts


config = ConfigParser()


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


def get_interface(config_path:str):
    config_content = read_file(config_path)
    for record in config_content.split('\n\n'):
        if '[Interface]' in record:
            interface = parse_record(record, WgInterface)
            interface.name = basename(config_path).split('.')[0]
            interface.peers = []
            interface.config_path = config_path
        if '[Peer]' in record:
            peer = parse_record(record, WgPeer)
            peer.config_path = join(config['general']['client_conf_dir'], f'{interface.name}-{peer.name}.conf')
            interface.peers.append(peer)
    return interface
    

def get_interfaces(wg_dir):
    interfaces = []
    config_files = listdir(wg_dir)
    for config_file in config_files:
        if not config_file.endswith('.conf'):
            continue
        interfaces.append(get_interface(join(wg_dir, config_file)))
    interfaces = list(sorted(interfaces, key=lambda i: i.name))
    return interfaces


def list_interfaces(interfaces):
    system('clear')
    print('| Configured interfaces |\n')
    for i, interface in enumerate(interfaces):
        print(f'{i+1}. {interface.name} / {interface.get("Address")}')
    input('\nPress ENTER to continue...')
    
    
def list_peers(interfaces):
    interface_menu = Menu('| Select interface to list peers from |', exit_title='Back')
    for face in interfaces:
        interface_menu.add_item(MenuItem(face))
    choice = interface_menu.show()
    if choice == -1:
        return
    interface = interfaces[choice-1]
    if interface.peers:
        print(f'\nConfigured peers of {interface.name}:\n')
        for i, peer in enumerate(interface.peers):
            print(f'{i+1}. {peer}')
    else:
        print(f'{colors.WARNING}No peers in this interface yet{colors.DEFAULT}')
    input('\nPress ENTER to continue...')
                

def get_next_server_port(config, interfaces):
    try:
        return max([int(interface.get('ListenPort')) for interface in interfaces]) + 1
    except:
        return config['server']['start_listen_port']


def add_interface(config, interfaces):
    system('clear')
    prompt = f'Please enter new interface unique name'
    while True:
        interface_name = input_validated(prompt, validators.InterfaceNameValidator.validate, loop=True)
        if not interface_name:
            return
        if not interface_name in [i.name for i in interfaces]:
            break
        print(f'{colors.FAIL}Interface {interface_name} already exists!{colors.DEFAULT}')
        
    prompt = f'Please enter initial IP address e.g 10.0.0.1'
    initial_ip = input_validated(prompt, validators.IPValidator.validate, loop=True)
    if not initial_ip:
        return
    server_port = get_next_server_port(config, interfaces)
    server_private_key = generate_private_key()
    interface_config = INTERFACE_TEMPLATE.format(
        server_ip = initial_ip,
        server_port = server_port,
        server_private_key = server_private_key,
        server_pub_interface = config['server']['public_interface']
    )
    config_path = join(config['wireguard']['wg_dir'], f'{interface_name}.conf')
    
    print(f'Adding new interface {interface_name} configuration...', end='')
    _, err = run_safe(write_to_file, [config_path, interface_config])
    if err:
        print(f'{colors.FAIL}FAILED\n{str(err)}{colors.DEFAULT}')
        input('\nPress ENTER to go back to Main Menu...')
        return
    else:
        print(f'{colors.SUCCESS}SUCCESS{colors.DEFAULT}')
    
    interface = get_interface(config_path)
    if confirm_input(f'Bring {interface_name} up?', 'yes', 'no'):
        interface.enable_service()
        interface.up()
    else:
        print(f'You will have to bring up the interface manually by running:\n{colors.WARNING}sudo systemctl enable wg-quick@{interface.name}.service && sudo wg-quick up {interface.name}{colors.DEFAULT}')
    input('\nPress ENTER to go back to Main Menu...')
    


def get_next_ip(ip:str) -> str:
    # TODO: check if next IP is in legal range
    if '/' in ip:
        ip = ip.split('/')[0]
    ip_lst = ip.split('.')
    ip_lst[-1] = str(int(ip_lst[-1]) + 1)
    return '.'.join(ip_lst)


def get_new_peer_ip(interface):
    # TODO: use the first vacant IP (not nesessarily the next one)
    if interface.peers == []:
        return get_next_ip(interface.get('Address'))
    return get_next_ip(interface.peers[-1].get('AllowedIPs'))
    

def get_subnet(ip:str):
    ip_lst = ip.split('.')
    ip_lst[-1] = '0'
    return '.'.join(ip_lst)


def add_peer(config, interfaces):
    interface_menu = Menu('| Please select interface to add peer to |')
    for face in interfaces:
        interface_menu.add_item(MenuItem(face.name))
    choice = interface_menu.show()
    if choice == -1:
        return
    interface = interfaces[choice-1]
    print()
    prompt = 'Please enter new peer unique name'
    while True:
        peer_name = input_validated(prompt, validators.PeerNameValidator.validate, loop=True)
        if not peer_name:
            return
        if not peer_name in [i.name for i in interface.peers]:
            break
        print(f'{colors.FAIL}Peer {peer_name} already exists in {interface.name}{colors.DEFAULT}')
        
    peer_private_key = generate_private_key()
    peer_public_key = generate_public_key(peer_private_key)
    peer_preshared_key = generate_preshared_key()
    peer_ip = get_new_peer_ip(interface)
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
    interface_config_path = join(config['wireguard']['wg_dir'], f'{interface.name}.conf')
    client_config_path = join(config['general']['client_conf_dir'], f'{interface.name}-{peer_name}.conf')
    
    print(f'Adding {peer_name} to {interface.name}...', end='')
    _, err = run_safe(write_to_file, [interface_config_path, peer_interface_config])
    if err:
        print(f'{colors.FAIL}FAILED\n{str(err)}{colors.DEFAULT}')
        print(f'Please manually add the following to {interface_config_path}:')
        print(f'{colors.WARNING}{peer_interface_config}')
    else:
        print(f'{colors.SUCCESS}SUCCESS{colors.DEFAULT}')
        
    print(f'Creating {peer_name} config in {client_config_path}...', end='')
    _, err = run_safe(write_to_file, [client_config_path, peer_client_config])
    if err:
        print(f'{colors.FAIL}FAILED\n{str(err)}{colors.DEFAULT}')
        print('Please manually create peer config file on the client device:')
        print(f'{colors.WARNING}{peer_client_config}')
    else:
        print(f'{colors.SUCCESS}SUCCESS{colors.DEFAULT}')
        
    if confirm_input('Apply config?', 'yes', 'no'):
        interface.syncconf()
    input('\nPress ENTER to go back to Main Menu...')


def remove_peer(config, interfaces):
    while True:
        system('clear')
        interface_menu = Menu('| Please select interface to add peer to |', exit_title='Back')
        for face in interfaces:
            interface_menu.add_item(MenuItem(face.name))
        choice = interface_menu.show()
        if choice == -1:
            break
        interface = interfaces[choice-1]
        if not interface.peers:
            input('No peers configured for this interface.\nPress ENTER to continue...')
            continue
        peers_menu = Menu(f'| Select peer to remove from {interface.name} |', exit_title='Back')
        for i, peer in enumerate(interface.peers):
            peers_menu.add_item(MenuItem(peer))
        choice = peers_menu.show()
        if choice == -1:
            continue
        target_peer = interface.peers[choice-1]
        interface_config_path = join(config['wireguard']['wg_dir'], f'{interface.name}.conf')
        if confirm_input(f'{colors.WARNING}Are you sure to permanently remove {target_peer.get("#Name")} from {interface.name}?{colors.DEFAULT}', 'yes', 'no'):
            target_peer.remove_config()
            interface.pop_peer(choice-1)
            interface.save(interface_config_path)
            interface.syncconf()
            input(f'Peer removed\nPress ENTER to continue...')
        break
    
    
def remove_interface(config, interfaces):
    interface_menu = Menu('| Select interface to remove |', exit_title='Back')
    for face in interfaces:
        interface_menu.add_item(MenuItem(face.name))
    interface = interfaces[interface_menu.show()-1]
    if confirm_input(f'{colors.WARNING}Are you sure to permanently remove {interface.name}?{colors.DEFAULT}', 'yes', 'no'):
        for peer in interface.peers:
            peer.remove_config()
        interface.down()
        interface.stop_service()
        interface.disable_service()
        interface.remove_config(config['wireguard']['wg_dir'])
    input('Interface removed.\nPress ENTER to continue...')


def get_main_menu(interfaces):
    main_menu = Menu('| Main Menu |')
    if interfaces:
        main_menu.add_item(MenuItem('List peers', list_peers, [interfaces] ))
        main_menu.add_item(MenuItem('List interfaces', list_interfaces, [interfaces]))
    main_menu.add_item(MenuItem('Add peer', add_peer, [config, interfaces]))
    main_menu.add_item(MenuItem('Add interface', add_interface, [config, interfaces]))
    if interfaces:
        main_menu.add_item(MenuItem('Remove peer', remove_peer, [config, interfaces]))
        main_menu.add_item(MenuItem('Remove interface', remove_interface, [config, interfaces]))
    return main_menu


if __name__ == "__main__":
    try:
        config.read('./wgman.cfg')
    except:
        print('Error reading wgman.cfg')
        quit()
    while True:
        interfaces = get_interfaces(config['wireguard']['wg_dir'])
        main_menu = get_main_menu(interfaces)
        if main_menu.show() == -1:
            break
    