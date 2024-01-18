def read_file(path):
    with open(path, 'r') as f:
        content = f.read()
    return content


def write_to_file(file_path:str, data:str):
    with open(file_path, 'a') as f:
        f.write(data)