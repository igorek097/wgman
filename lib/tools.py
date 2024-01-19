from typing import Callable


def read_file(path):
    with open(path, 'r') as f:
        content = f.read()
    return content


def write_to_file(file_path:str, data:str):
    with open(file_path, 'a') as f:
        f.write(data)
        
        
def run_safe(function, args=[]):
    try:
        val = function(*args)
        return val, None
    except Exception as e:
        return None, e
    
    
def input_validated(prompt:str, validator:Callable, help='Incorrect input', loop=False, cancel='Q'):
    if cancel:
        prompt = f'{prompt} ("{cancel}" to abort): '
    while True:
        user_input = input(prompt)
        if user_input == cancel:
            return None
        if validator(user_input):
            return user_input
        if help:
            print(help)
        if not loop:
            return None
        