import os, hashlib, collections, json

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def find_duplicates(root):
    hashes = collections.defaultdict(list)
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.startswith('.git'):
                continue
            full = os.path.join(dirpath, name)
            try:
                h = file_hash(full)
                hashes[h].append(full)
            except Exception:
                continue
    dup = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    return dup

if __name__ == '__main__':
    root = r"C:/Users/User/Documents/NEW_VERSION"
    duplicates = find_duplicates(root)
    print(json.dumps(duplicates, indent=2))
