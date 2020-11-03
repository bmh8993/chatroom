#!/usr/bin/env python3

import threading
import socket
import argparse
import os


class Server(threading.Thread):

    def __init__(self, host, port):
        super().__init__()
        self.connections = []
        self.host = host
        self.port = port

    def run(self):
        # create socket
        # first arg = address family, AF_INET = IP networking
        # second arg = socket_type, SOCK_STREAM = TCP
        # 주소 체계(address family)는 IPv4, 소켓 타입으로 TCP 사용합니다.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 포트 사용중이라 연결할 수 없다는 WinError 10048 에러 해결를 위해 필요합니다.
        # SO_REUSEADDR을 사용하면 이전 연결이 닫힌 후 서버가 동일한 포트를 사용할 수
        # 있다.(일반적으로 몇 분 기다려야함)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((self.host, self.port))
        sock.listen(1)  # listening socket임을 나타냄
        print('Listening at', sock.getsockname())

        while True:
            # 새로운 클라이언트 연결을 수신하기 위한 무한 루프
            # accept를 호출하면 새로운 클라이언트가 연결될때까지 기다리고,
            # 연결이 되면 연결된 새로운 소켓을 return
            # Accept new connection
            sc, sockname = sock.accept()
            print('Accepted a new connection from {} to {}'.format(sc.getpeername(), sc.getsockname()))
            # getpeername - returns the socket address on the other end of the connection (in this case, the client)
            # getsockname - returns the socket address to which the socket object is bound.

            # create new thread
            # 개별 클라이언트와 통신할 방법뿐만 아니라
            # 잠재적 클라이언트로부터 새로운 연결을 listening 해야한다 그러기 위해서
            # 새로운 유저가 연결되는 매 번 ServerSocket을 만들어야한다. 그리고 이
            # 쓰레드는 Server Thread와 나란히 있어야한다.
            # server 또한 모든 활성 클라이언트 커넥션을 관리할 방법이 필요한데 그래서
            # 활성상태인 ServerSocket을 self.connections에 저장한다.
            server_socket = ServerSocket(sc, sockname, self)

            # Start new thread
            server_socket.start()

            # Add thread to active connections
            self.connections.append(server_socket)
            print('Ready to receive message from', sc.getpeername())

    def broadcast(self, message, source):
        # 서버가 수신한 메세지를 연결된 다른 모든 클라이언트에게 메세지를 보내기 위함

        for connection in self.connections:
            # send to all connected clients except the source client
            if connection.sockname != source:
                connection.send(message)

    def remove_connection(self, connection):
        """
        Removes a ServerSocket thread from the connections attribute.
        Args:
            connection (ServerSocket): The ServerSocket thread to remove.
        """
        self.connections.remove(connection)


class ServerSocket(threading.Thread):

    def __init__(self, sc, sockname, server):
        super().__init__()
        self.sc = sc
        self.sockname = sockname
        self.server = server

    def run(self):

        while True:
            message = self.sc.recv(1024).decode("ascii")
            if message:
                print('{} says {!r}'.format(self.sockname, message))
                self.server.broadcast(message, self.sockname)
            else:
                # Client has closed the socket, exit the thread
                print('{} has closed the connection'.format(self.sockname))
                self.sc.close()
                self.server.remove_connection(self)
                return

    def send(self, message):
        self.sc.sendall(message.encode("ascii"))


def exit(server):

    while True:
        ipt = input('')
        if ipt == 'q':
            print('Closing all connections...')
            for connection in server.connections:
                connection.sc.close()
            print('Shutting down the server...')
            os._exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chatroom Server')
    parser.add_argument('host', help='Interface the server listens at')
    parser.add_argument('-p', metavar='PORT', type=int, default=1060,
                        help='TCP port (default 1060)')
    args = parser.parse_args()
    # Create and start server thread
    server = Server(args.host, args.p)
    server.start()

    exit = threading.Thread(target=exit, args=(server,))
    exit.start()
