import subprocess


def flush_dns():
    subprocess.call('ipconfig /flushdns')

def change_dns_to_localhost ():
    subprocess.call('netsh interface ip set dns "Wi-Fi" static 127.0.0.1'.split())

def change_dns_to_dhcp ():
    subprocess.call('netsh interface ip set dns "Wi-Fi" dhcp'.split())


