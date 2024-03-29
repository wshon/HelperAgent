#!/usr/bin/python
# Filename s5.py
# Python Dynamic Socks5 Proxy
# Usage: python s5.py 1080
# Background Run: nohup python s5.py 1080 &
import asyncio
import logging
import select
import socket
import socketserver
import struct
import sys
from optparse import OptionParser

VER = 5


class METHOD:
    NONE = 0  # 无验证需求


class ATYP:
    IPV4 = 1
    DOMAIN = 3
    IPV6 = 4


CMD_CONNECT = 1
CMD_BIND = 2
CMD_UDP_ASSOCIATE = 3
CMD_REG_SURVIVOR = 250

RSP_SOCKET5_VERSION = b'\x05\x00'
RSP_SUCCESS = b'\x05\x00\x00\x01'
RSP_CONNECTION_REFUSED = b'\x05\x05\x00\x01'
RSP_COMMAND_NOT_SUPPORTED = b'\x05\x07\x00\x01'
RSP_ADDRESS_TYPE_NOT_SUPPORTED = b'\x05\x08\x00\x01'


class REP:
    SUCCESS = 0  # 成功
    GENERAL_FAILURE = 1  # 普通的SOCKS服务器请求失败
    NOT_ALLOWED = 2  # 现有的规则不允许的连接
    NETWORK_UNREACHABLE = 3  # 网络不可达
    HOST_UNREACHABLE = 4  # 主机不可达
    CONNECTION_REFUSED = 5  # 连接被拒
    TTL_TIMEOUT = 6  # TTL超时
    COMMAND_NOT_SUPPORTED = 7  # 不支持的命令
    ADDRESS_TYPE_NOT_SUPPORTED = 8  # 不支持的地址类型
    UNDEFINED = 9  # – NAME=FF # 未定义


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class SurvivorServer(socketserver.StreamRequestHandler):
    survivor = []
    close = False

    def handle_tcp(self, sock, remote):
        f_d_set = [sock, remote]
        while not self.close:
            r, w, e = select.select(f_d_set, [], [])
            if sock in r:
                if remote.send(sock.recv(4096)) <= 0:
                    break
            if remote in r:
                if sock.send(remote.recv(4096)) <= 0:
                    break

    def handle(self):
        try:
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send(b'\x05\x00')
            # 2. Request
            data = self.rfile.read(4)
            atyp = data[3]
            cmd = data[1]
            if cmd == CMD_CONNECT:  # 1. Tcp connect
                survivor_sock = self.survivor.pop()
                survivor_sock.send(data)
                self.handle_tcp(sock, survivor_sock)
            elif cmd == CMD_REG_SURVIVOR:
                self.survivor.append(sock)
            else:
                logging.error('unknown command %d', cmd)
                # Command not supported
                return sock.send(RSP_COMMAND_NOT_SUPPORTED)
            # # 3. Transferring
            # if reply[1] == REP.SUCCESS:  # Success
            #     if mode == CMD_CONNECT:  # 1. Tcp connect
            #         self.handle_tcp(sock, remote)
        except socket.error:
            pass  # print 'error' nothing to do .
        except IndexError:
            pass


class RescuersClient:
    survivor = []
    close = False

    survivor_host = None
    survivor_port = None
    survivor_socket = None

    def __init__(self, host, port):
        self.survivor_host = host
        self.survivor_port = port
        self.rescures()

    def rescures(self):
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((self.survivor_host, self.survivor_port))
        self.survivor_socket = remote
        # local = remote.getsockname()

    def handle_tcp(self, sock, remote):
        f_d_set = [sock, remote]
        while not self.close:
            r, w, e = select.select(f_d_set, [], [])
            if sock in r:
                if remote.send(sock.recv(4096)) <= 0:
                    break
            if remote in r:
                if sock.send(remote.recv(4096)) <= 0:
                    break

    def handle(self):
        try:
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send(RSP_SOCKET5_VERSION)
            # 2. Request
            data = self.rfile.read(4)
            mode = data[1]
            if mode == CMD_CONNECT:  # 1. Tcp connect
                atyp = data[3]
                if atyp == ATYP.IPV4:  # IPv4
                    addr = socket.inet_ntoa(self.rfile.read(4))
                elif atyp == ATYP.DOMAIN:  # Domain name
                    addr = self.rfile.read(sock.recv(1)[0])
                else:
                    # Addr type not supported
                    return sock.send(RSP_ADDRESS_TYPE_NOT_SUPPORTED)
                port = struct.unpack('>H', self.rfile.read(2))
                try:
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.connect((addr, port[0]))
                    local = remote.getsockname()
                except socket.error:
                    # Connection refused
                    return sock.send(RSP_CONNECTION_REFUSED)
                    # return sock.send(b'\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00')
                reply = RSP_SUCCESS + socket.inet_aton(local[0]) + struct.pack('>H', local[1])
                sock.send(reply)
            elif mode == CMD_REG_SURVIVOR:
                self.survivor.append(sock)
                return
            else:
                # Command not supported
                return sock.send(RSP_COMMAND_NOT_SUPPORTED)
            # 3. Transferring
            if reply[1] == REP.SUCCESS:  # Success
                if mode == CMD_CONNECT:  # 1. Tcp connect
                    self.handle_tcp(sock, remote)
        except socket.error:
            pass  # print 'error' nothing to do .
        except IndexError:
            pass


def survivor(port):
    server = ThreadingTCPServer(('', port), SurvivorServer)
    print('survivor bind port: %d' % port + ' ok!')
    server.serve_forever()
    server.serve_forever()


def rescuers(target, port):
    filename = sys.argv[0]
    if len(sys.argv) < 2:
        print('usage: ' + filename + ' port')
        sys.exit()
    socks_port = int(sys.argv[1])
    server = ThreadingTCPServer(('', socks_port), SurvivorServer)
    print('rescuers %d: %d' % target, port + ' ok!')
    server.serve_forever()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-s", "--survivor", action="store_true",
                      dest="survivor",
                      default=False,
                      help="Access its network resources by connecting to local rescuers")
    parser.add_option("-r", "--rescuers", action="store_true",
                      dest="rescuers",
                      default=False,
                      help="Help target computers access the Internet")
    parser.add_option("-t", "--target", action="store", type="string",
                      dest="target",
                      default='0.0.0.0',
                      help="target host")
    parser.add_option("-p", "--port", action="store", type="int",
                      dest="port",
                      default='1080',
                      help="target/listen port")

    (options, args) = parser.parse_args()
    if options.survivor:
        survivor(options.port)
    if options.rescuers:
        rescuers(options.target, options.port)

    # 获取EventLoop:
    loop = asyncio.get_event_loop()
    # 执行coroutine
    loop.run_until_complete(hello())
    loop.close()
