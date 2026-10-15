from os import system

try:
    with open('/proc/sys/user/max_user_namespaces', 'r') as f:
        max_user_namespaces_s = f.read().strip()
except FileNotFoundError:
    print('/proc/sys/user/max_user_namespaces not found, user namespaces unavailable on this system')
    exit(1)
if (not max_user_namespaces_s.isnumeric()) or int(max_user_namespaces_s) <= 0:
    print('max user namespaces not positive integer, user namespaces unavailable on this system')
    exit(1)

system('unshare --mount --user --map-root-user bash')

