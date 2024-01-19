import re

ip_regex = r'^10.(?:(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]?|[1-9][0-9]?|0)\.){2}(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]?|[1-9][0-9]?)$'
interface_name_regex = r'^[\w\-]{3,15}$'


class BaseValidator:
    regex = ''
    
    @classmethod
    def validate(self, target:str) -> bool:
        return True if re.fullmatch(self.regex, target) else False
    
    
class IPValidator(BaseValidator):
    regex = ip_regex
    
    
class PeerNameValidator(BaseValidator):
    regex = interface_name_regex
    
    
class InterfaceNameValidator(BaseValidator):
    regex = interface_name_regex