#!/usr/bin/python
# Filename s5.py
# Python Dynamic Socks5 Proxy
# Usage: python s5.py 1080
# Background Run: nohup python s5.py 1080 &

import select
import socket
import socketserver
import struct
import sys

VER = 5


class METHOD:
    NONE = 0  # 无验证需求


class ATYP:
    IPV4 = 1
    DOMAIN = 3
    IPV6 = 4


class CMD:
    CONNECT = 1
    BIND = 2
    UDP_ASSOCIATE = 3


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


class Socks5Server(socketserver.StreamRequestHandler):
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
            pass  # print 'from ', self.client_address nothing to do.
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send(b'\x05\x00')
            # 2. Request
            data = self.rfile.read(4)
            mode = data[1]
            atyp = data[3]
            if atyp == ATYP.IPV4:  # IPv4
                addr = socket.inet_ntoa(self.rfile.read(4))
            elif atyp == ATYP.DOMAIN:  # Domain name
                addr = self.rfile.read(sock.recv(1)[0])
            else:
                # Addr type not supported
                return sock.send(b'\x05\x08\x00\x01')
            port = struct.unpack('>H', self.rfile.read(2))
            reply = b'\x05\x00\x00\x01'
            try:
                if mode == CMD.CONNECT:  # 1. Tcp connect
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.connect((addr, port[0]))
                    local = remote.getsockname()
                    reply += socket.inet_aton(local[0]) + struct.pack('>H', local[1])
                else:
                    return sock.send(b'\x05\x07\x00\x01')  # Command not supported
            except socket.error:
                # Connection refused
                return sock.send(b'\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00')
            sock.send(reply)
            # 3. Transferring
            if reply[1] == REP.SUCCESS:  # Success
                if mode == CMD.CONNECT:  # 1. Tcp connect
                    self.handle_tcp(sock, remote)
        except socket.error:
            pass  # print 'error' nothing to do .
        except IndexError:
            pass


def main():
    filename = sys.argv[0]
    if len(sys.argv) < 2:
        print('usage: ' + filename + ' port')
        sys.exit()
    socks_port = int(sys.argv[1])
    server = ThreadingTCPServer(('', socks_port), Socks5Server)
    print('bind port: %d' % socks_port + ' ok!')
    server.serve_forever()


if __name__ == '__main__':
    main()
