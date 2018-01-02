import socket
import select
import threading
import time
import socketserver
import json
import sys
from collections import OrderedDict

pool_address = 'fakepool'
pool_port = 9999
wallet='0xfakeaddress'
worker_name='devfee'

my_lock = threading.Lock()

def lock_print(msg):
    my_lock.acquire()
    try:
        print("[%s] %s" % (time.ctime(), msg))
    finally:
        my_lock.release()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

# modify any requests destined for the remote host
def remove_devfee(data):
    global wallet, worker_name
    data = bytes.decode(data)
    #If it is an Auth packet
    if ('submitLogin' in data) or ('eth_login' in data):
        json_data = json.loads(data, object_pairs_hook=OrderedDict)
        lock_print('[+] Auth in progress with address: ' + json_data['params'][0])
        #If the auth contain an other address than our
        if wallet not in json_data['params'][0]:
             lock_print('[*] DevFee Detected - Replacing Address')
             lock_print('[*] OLD: ' + json_data['params'][0])
             #We replace the address
             json_data['params'][0] = wallet + worker_name
             lock_print('[*] NEW: ' + json_data['params'][0])

        data = json.dumps(json_data) + '\n'

    #Packet is forged, ready to send.
    return str.encode(data)


class StratumProxy(socketserver.StreamRequestHandler):
    def handle_tcp(self, sock, remote):
        try:
            fdset = [sock, remote]
            while True:
                r, w, e = select.select(fdset, [], [])
                if sock in r:
                    r_data = sock.recv(4096)
                    if remote.send(remove_devfee(r_data)) <= 0:
                        break
                if remote in r:
                    if sock.send(remote.recv(4096)) <= 0:
                        break
        finally:
            remote.close()
            lock_print('Close connection: {}'.format(sock.getpeername()))

    def handle(self):
        try:
            global pool_address, pool_port
            sock = self.connection
            lock_print('New Connection: {}'.format(sock.getpeername()))
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((pool_address, pool_port))
            self.handle_tcp(sock, remote)
        except socket.error as e:
            lock_print('socket error')
            lock_print(e)


def main():
    # cursory check of command line args
    if len(sys.argv[1:]) != 4:
        lock_print("Usage: ./proxy.py [localport] [remotehost] [remoteport] [ETH Wallet]")
        lock_print("Example: ./proxy.py 9999 eth.realpool.org 9999 0x...")
        sys.exit(0)

    local_port = int(sys.argv[1])

    global pool_address, pool_port
    pool_address = sys.argv[2]
    pool_port = int(sys.argv[3])

    # Set the wallet
    global wallet 
    wallet = sys.argv[4]
    
    global worker_name
    
    #Uncomment if you meet issue with pool or worker name - This will disable the worker name
    #worker_name = ''
    pool_slash = ['nanopool.org','dwarfpool.com']
    pool_dot = ['ethpool.org','ethermine.org','alpereum.ch']
    if worker_name:
        if any(s in pool_address for s in pool_slash):
            worker_name = '/' + worker_name
        elif any(d in pool_address for d in pool_dot):
            worker_name = '.' + worker_name
        else:
            #No worker name for compatbility reason
            lock_print("Unknown pool - Worker name is empty")
            worker_name = ''

    lock_print("Wallet set: " + wallet + worker_name)

    lock_print('Starting stratum proxy at port %d' % local_port)
    server = ThreadingTCPServer(('', local_port), StratumProxy)
    server.serve_forever()

if __name__ == '__main__':
    main()
