#!/usr/bin/env python3

from argparse import ArgumentParser
from configparser import ConfigParser

from dnslib import *
from ipaddress import ip_address

import logging
import threading
import random
import operator
import socketserver
import socket
import sys
import os
import binascii
import string
import base64


class DNSChefFormatter(logging.Formatter):

    FORMATS = {
        logging.ERROR: "(%(asctime)s) [!] %(msg)s",
        logging.INFO: "(%(asctime)s) [*] %(msg)s",
        logging.WARNING: "WARNING: %(msg)s",
        logging.DEBUG: "DBG: %(module)s: %(lineno)d: %(msg)s",
        "DEFAULT": "%(asctime)s - %(msg)s"
    }

    def format(self, record):
        format_orig = self._style._fmt

        self._style._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        result = logging.Formatter.format(self, record)

        self._style._fmt = format_orig

        return result

log = logging.getLogger("dnschef")
log.setLevel(logging.DEBUG)

log_ch = logging.StreamHandler()
log_ch.setLevel(logging.INFO)
log_ch.setFormatter(DNSChefFormatter(datefmt="%H:%M:%S"))
log.addHandler(log_ch)

# DNSHandler Mixin. The class contains generic functions to parse DNS requests and
# calculate an appropriate response based on user parameters.
dns_lock = None  #type: threading.Lock
class DNSHandler():

    def parse(self, data):
        response = ""

        try:
            # Parse data as DNS
            d = DNSRecord.parse(data)

        except Exception:
            log.error(f"{self.client_address[0]}: ERROR: invalid DNS request")

        else:
            # Only Process DNS Queries
            if QR[d.header.qr] == "QUERY":

                # Gather query parameters
                # NOTE: Do not lowercase qname here, because we want to see
                #       any case request weirdness in the logs.
                qname = str(d.q.qname)

                # Chop off the last period
                if qname[-1] == '.': qname = qname[:-1]

                qtype = QTYPE[d.q.qtype]

                # Find all matching fake DNS records for the query name or get False
                #print("nametodns in parse()  id :{}".format(id(self.server.nametodns)))
                try:
                    # critical section - lock
                    fake_records = dict()
                    dns_lock.acquire()
                    for record in self.server.nametodns:
                        fake_records[record] = self.findnametodns(qname, self.server.nametodns[record])
                finally:
                    dns_lock.release()

                # Check if there is a fake record for the current request qtype
                if qtype in fake_records and fake_records[qtype]:

                    fake_record = fake_records[qtype]

                    # Create a custom response to the query
                    response = DNSRecord(DNSHeader(id=d.header.id, bitmap=d.header.bitmap, qr=1, aa=1, ra=1), q=d.q)

                    log.info(f"{self.client_address[0]}: cooking the response of type '{qtype}' for {qname} to {fake_record}")

                    # IPv6 needs additional work before inclusion:
                    if qtype == "AAAA":
                        ipv6_hex_tuple = list(map(int, ip_address(fake_record).packed))
                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](ipv6_hex_tuple)))

                    elif qtype == "SOA":
                        mname,rname,t1,t2,t3,t4,t5 = fake_record.split(" ")
                        times = tuple([int(t) for t in [t1,t2,t3,t4,t5]])

                        # dnslib doesn't like trailing dots
                        if mname[-1] == ".": mname = mname[:-1]
                        if rname[-1] == ".": rname = rname[:-1]

                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](mname,rname,times)))

                    elif qtype == "NAPTR":
                        order,preference,flags,service,regexp,replacement = list(map(lambda x: x.encode(), fake_record.split(" ")))
                        order = int(order)
                        preference = int(preference)

                        # dnslib doesn't like trailing dots
                        if replacement[-1] == ".": replacement = replacement[:-1]

                        response.add_answer( RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](order,preference,flags,service,regexp,DNSLabel(replacement))) )

                    elif qtype == "SRV":
                        priority, weight, port, target = fake_record.split(" ")
                        priority = int(priority)
                        weight = int(weight)
                        port = int(port)
                        if target[-1] == ".": target = target[:-1]

                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](priority, weight, port, target) ))

                    elif qtype == "DNSKEY":
                        flags, protocol, algorithm, key = fake_record.split(" ")
                        flags = int(flags)
                        protocol = int(protocol)
                        algorithm = int(algorithm)
                        key = base64.b64decode(("".join(key)).encode('ascii'))

                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](flags, protocol, algorithm, key) ))

                    elif qtype == "RRSIG":
                        covered, algorithm, labels, orig_ttl, sig_exp, sig_inc, key_tag, name, sig = fake_record.split(" ")
                        covered = getattr(QTYPE,covered) # NOTE: Covered QTYPE
                        algorithm = int(algorithm)
                        labels = int(labels)
                        orig_ttl = int(orig_ttl)
                        sig_exp = int(time.mktime(time.strptime(sig_exp +'GMT',"%Y%m%d%H%M%S%Z")))
                        sig_inc = int(time.mktime(time.strptime(sig_inc +'GMT',"%Y%m%d%H%M%S%Z")))
                        key_tag = int(key_tag)
                        if name[-1] == '.': name = name[:-1]
                        sig = base64.b64decode(("".join(sig)).encode('ascii'))

                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](covered, algorithm, labels,orig_ttl, sig_exp, sig_inc, key_tag, name, sig) ))

                    else:
                        # dnslib doesn't like trailing dots
                        if fake_record[-1] == ".": fake_record = fake_record[:-1]
                        response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](fake_record)))

                    response = response.pack()

                elif qtype == "*" and not None in list(fake_records.values()):
                    log.info(f"{self.client_address[0]}: cooking the response of type 'ANY' for {qname} with all known fake records")

                    response = DNSRecord(DNSHeader(id=d.header.id, bitmap=d.header.bitmap,qr=1, aa=1, ra=1), q=d.q)

                    for qtype,fake_record in list(fake_records.items()):
                        if fake_record:

                            # NOTE: RDMAP is a dictionary map of qtype strings to handling classses
                            # IPv6 needs additional work before inclusion:
                            if qtype == "AAAA":
                                fake_record = list(map(int, ip_address(fake_record).packed))

                            elif qtype == "SOA":
                                mname,rname,t1,t2,t3,t4,t5 = fake_record.split(" ")
                                times = tuple([int(t) for t in [t1,t2,t3,t4,t5]])

                                # dnslib doesn't like trailing dots
                                if mname[-1] == ".": mname = mname[:-1]
                                if rname[-1] == ".": rname = rname[:-1]

                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](mname,rname,times)))

                            elif qtype == "NAPTR":
                                order,preference,flags,service,regexp,replacement = fake_record.split(" ")
                                order = int(order)
                                preference = int(preference)

                                # dnslib doesn't like trailing dots
                                if replacement and replacement[-1] == ".": replacement = replacement[:-1]

                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](order,preference,flags,service,regexp,replacement)))

                            elif qtype == "SRV":
                                priority, weight, port, target = fake_record.split(" ")
                                priority = int(priority)
                                weight = int(weight)
                                port = int(port)
                                if target[-1] == ".": target = target[:-1]

                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](priority, weight, port, target) ))

                            elif qtype == "DNSKEY":
                                flags, protocol, algorithm, key = fake_record.split(" ")
                                flags = int(flags)
                                protocol = int(protocol)
                                algorithm = int(algorithm)
                                key = base64.b64decode(("".join(key)).encode('ascii'))

                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](flags, protocol, algorithm, key) ))

                            elif qtype == "RRSIG":
                                covered, algorithm, labels, orig_ttl, sig_exp, sig_inc, key_tag, name, sig = fake_record.split(" ")
                                covered = getattr(QTYPE,covered) # NOTE: Covered QTYPE
                                algorithm = int(algorithm)
                                labels = int(labels)
                                orig_ttl = int(orig_ttl)
                                sig_exp = int(time.mktime(time.strptime(sig_exp +'GMT',"%Y%m%d%H%M%S%Z")))
                                sig_inc = int(time.mktime(time.strptime(sig_inc +'GMT',"%Y%m%d%H%M%S%Z")))
                                key_tag = int(key_tag)
                                if name[-1] == '.': name = name[:-1]
                                sig = base64.b64decode(("".join(sig)).encode('ascii'))

                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](covered, algorithm, labels,orig_ttl, sig_exp, sig_inc, key_tag, name, sig) ))

                            else:
                                # dnslib doesn't like trailing dots
                                if fake_record[-1] == ".": fake_record = fake_record[:-1]
                                response.add_answer(RR(qname, getattr(QTYPE,qtype), rdata=RDMAP[qtype](fake_record)))

                    response = response.pack()

                # Proxy the request
                else:
                    log.info(f"{self.client_address[0]}: proxying the response of type '{qtype}' for {qname}")

                    nameserver_tuple = random.choice(self.server.nameservers).split('#')
                    response = self.proxyrequest(data, *nameserver_tuple)

        return response


    # Find appropriate ip address to use for a queried name. The function can
    def findnametodns(self,qname,nametodns):

        # Make qname case insensitive
        qname = qname.lower()

        # Split and reverse qname into components for matching.
        qnamelist = qname.split('.')
        qnamelist.reverse()

        # HACK: It is important to search the nametodns dictionary before iterating it so that
        # global matching ['*.*.*.*.*.*.*.*.*.*'] will match last. Use sorting for that.
        for domain,host in sorted(iter(nametodns.items()), key=operator.itemgetter(1)):

            # NOTE: It is assumed that domain name was already lowercased
            #       when it was loaded through --file, --fakedomains or --truedomains
            #       don't want to waste time lowercasing domains on every request.

            # Split and reverse domain into components for matching
            domain = domain.split('.')
            domain.reverse()

            # Compare domains in reverse.
            for a, b in zip(qnamelist, domain):
                if a != b and b != "*":
                    break
            else:
                # Could be a real IP or False if we are doing reverse matching with 'truedomains'
                return host
        else:
            return False

    # Obtain a response from a real DNS server.
    def proxyrequest(self, request, host, port="53", protocol="udp"):
        reply = None
        try:
            if self.server.ipv6:

                if protocol == "udp":
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                elif protocol == "tcp":
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

            else:
                if protocol == "udp":
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                elif protocol == "tcp":
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            sock.settimeout(3.0)

            # Send the proxy request to a randomly chosen DNS server

            if protocol == "udp":
                sock.sendto(request, (host, int(port)))
                reply = sock.recv(1024)
                sock.close()

            elif protocol == "tcp":
                sock.connect((host, int(port)))

                # Add length for the TCP request
                length = binascii.unhexlify("%04x" % len(request))
                sock.sendall(length+request)

                # Strip length from the response
                reply = sock.recv(1024)
                reply = reply[2:]

                sock.close()

        except Exception as e:
            log.error(f"[!] Could not proxy request: {e}")
        else:
            return reply

# UDP DNS Handler for incoming requests
class UDPHandler(DNSHandler, socketserver.BaseRequestHandler):

    def handle(self):
        (data, socket) = self.request
        response = self.parse(data)

        if response:
            socket.sendto(response, self.client_address)

# TCP DNS Handler for incoming requests
class TCPHandler(DNSHandler, socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024)

        # Remove the addition "length" parameter used in the
        # TCP DNS protocol
        data = data[2:]
        response = self.parse(data)

        if response:
            # Calculate and add the additional "length" parameter
            # used in TCP DNS protocol 
            length = binascii.unhexlify("%04x" % len(response))
            self.request.sendall(length + response)

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):

    # Override SocketServer.UDPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6, log,lock):
        self.nametodns  = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        self.log = log
        self.lock = lock  # type: threading.Lock

        socketserver.UDPServer.__init__(self, server_address, RequestHandlerClass)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    # Override default value
    allow_reuse_address = True

    # Override SocketServer.TCPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6, log):
        self.nametodns   = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        self.log = log

        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)

# Initialize and start the DNS Server
def start_cooking(interface, nametodns, nameservers, tcp=False, ipv6=False, port="53", logfile=None,lock=None):
    try:

        if logfile:
            fh = logging.FileHandler(logfile, encoding='UTF-8')
            fh.setLevel(logging.INFO)
            fh.setFormatter(DNSChefFormatter(datefmt="%d/%b/%Y:%H:%M:%S %z"))
            log.addHandler(fh)

            log.info("DNSChef is active.")

        if tcp:
            log.info("DNSChef is running in TCP mode")
            server = ThreadedTCPServer((interface, int(port)), TCPHandler, nametodns, nameservers, ipv6, log)
        else:
            server = ThreadedUDPServer((interface, int(port)), UDPHandler, nametodns, nameservers, ipv6, log,lock)

        #print("nametodns in start_cooking id : {}".format(id(nametodns)))

        # Start a thread with the server -- that thread will then start
        # more threads for each request
        server_thread = threading.Thread(target=server.serve_forever)

        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

        # Loop in the main thread
        while True: time.sleep(100)

    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        log.info("DNSChef is shutting down.")
        sys.exit()

    except Exception as e:
        log.error(f"Failed to start the server: {e}")

def start_dns_server(interface_to_bind, blocked_urls, nameservers=['8.8.8.8'], tcp=False, ipv6=False, port="53", logfile=None, lock_dns=None):
    nametodns = dict()
    global dns_lock
    dns_lock = lock_dns

    for qtype in list(RDMAP.keys()):
        nametodns[qtype] = dict()
        if qtype == 'A':
            nametodns[qtype] = blocked_urls

    thread = threading.Thread(name="dns server",target=start_cooking, args= (interface_to_bind, nametodns, nameservers, tcp, ipv6, port, logfile))
    thread.daemon = True
    thread.start()
    print ("dns started")
    return nametodns

if __name__ == "__main__":
    # Launch DNSChef
    start_cooking(interface=options.interface, nametodns=nametodns, nameservers=nameservers, tcp=options.tcp, ipv6=options.ipv6, port=options.port, logfile=options.logfile)