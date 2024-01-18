from subprocess import run, PIPE
from os import remove, system
from os.path import join


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
        
    def __str__(self) -> str:
        return f'{self.name} / {self.get("Address")}'
        
    def pop_peer(self, peer_num):
        self.peers.pop(peer_num)
        
    def remove_config(self, wg_path):
        config_path = join(wg_path, f'{self.name}.conf')
        try:
            remove(config_path)
        except:
            pass
        
    def save(self, path:str):
        with open(path, 'w') as f:
            f.write('[Interface]\n')
            for param, value in self._params.items():
                f.write(f'{param} = {value}')
                f.write('\n')
            for peer in self.peers:
                f.write('\n[Peer]\n')
                for param, value in peer._params.items():
                    f.write(f'{param} = {value}')
                    f.write('\n')
                    
    def syncconf(self):
        temp_file = f'./{self.name}-tmp.conf'
        system(f'sudo wg-quick strip {self.name} > {temp_file}')
        system(f'sudo wg syncconf {self.name} {temp_file}')
        remove(temp_file)
        
    def up(self):
        system(f'sudo wg-quick up {self.name}')
        
    def down(self):
        system(f'sudo wg-quick down {self.name}')
        
    def stop_service(self):
        system(f'sudo systemctl stop wg-quick@{self.name}.service')
        
    def disable_service(self):
        system(f'sudo systemctl disable wg-quick@{self.name}.service')
        
    def start_service(self):
        system(f'sudo systemctl start wg-quick@{self.name}.service')
        
    def enable_service(self):
        system(f'sudo systemctl enable wg-quick@{self.name}.service')
        
                    
                    
class WgPeer(WgEntity):
    
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        
    def __str__(self):
        return f'{self.name} / {self.get("AllowedIPs")}'
    
    def remove_config(self):
        try:
            remove(self.config_path)
        except:
            pass
    
    @property
    def name(self):
        return self.get('#Name')
        

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
