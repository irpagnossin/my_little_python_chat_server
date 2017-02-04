from WebSocketAction import WebSocketAction
from WebSocketHandler import WebSocketHandler
import json
import logging

from SocketServer import ThreadingMixIn, TCPServer  # Python 2.7
# from socketserver import ThreadingMixIn, TCPServer  # Python 3


logger = logging.getLogger(__name__)


class WebSocketServer(ThreadingMixIn, TCPServer):

    allow_reuse_address = True
    daemon_threads = True  # comment to keep threads alive until finished

    '''
    clients is a list of dict:
        {
         'address'  : (address, port),
         'handler'  : handler,
         'id'       : id,
         'room'     : room,
         'username' : username
        }
    '''
    clients = []

    id_counter = 0

    def __init__(self, port, host='127.0.0.1'):
        """
        A websocket server
        :param port: which port listen to.
        :param host: IP address of server.
        """
        self.port = port
        TCPServer.__init__(self, (host, port), WebSocketHandler)

    def _client_left_(self, handler):
        """
        Websocket handler calls this method whenever a client disconnects
        :param handler: Websocket handler
        :return:
        """
        client = self.handler_to_client(handler)
        if client in self.clients:
            self.clients.remove(client)

    def _message_received_(self, handler, message):
        """
        Websocket handler calls this method whenever a new message arrives
        :param handler: Websocket handler
        :param msg: Message received
        :return:
        """
        client = self.handler_to_client(handler)
        msg = json.loads(message)
        incoming_room = str(msg['room'])

        incoming_action = str(msg['action'])

        if incoming_action == WebSocketAction.USER_SAYS:
            self._multicast_(message, incoming_room)

        elif incoming_action == WebSocketAction.SIGN_IN:

            # At sign-in, username and chat-room is known. So, append them to client
            for c in self.clients:
                if c['id'] == client['id']:
                    c['room'] = str(msg['room'])
                    c['username'] = str(msg['user'])
                    break

            outgoing_socket_message = {
                'action': WebSocketAction.USER_IN,
                'message': '',
                'room': client['room'],
                'user': client['username']
            }

            self._multicast_(json.dumps(outgoing_socket_message), incoming_room)

        elif incoming_action == WebSocketAction.SIGN_OUT:

            outgoing_socket_message = {
                'action': WebSocketAction.USER_OUT,
                'message': '',
                'room': msg['room'],
                'user': msg['user']
            }

            self._multicast_(json.dumps(outgoing_socket_message), incoming_room)
            # TODO: como desconectar o usuario?

            print json.dumps(outgoing_socket_message)

        elif incoming_action == WebSocketAction.REQUEST_USERS:

            usernames = []
            for c in self.clients:
                if ('username' in c) and ('room' in c) and (c['room'] == incoming_room):
                    usernames.append(c['username'])

            outgoing_socket_message = json.dumps({
                'action': WebSocketAction.ALL_USERS,
                'message': ','.join(usernames),
                'room': "",
                'user': ""
            })

            self._unicast_(client, outgoing_socket_message)

        else:
            print "I don't know what you mean!"

        if len(message) > 200:
            message = message[:200] + '..'
        print("Client(%d) said: %s" % (client['id'], message))

    def _new_client_(self, handler):
        """
        Websocket handler calls this method whenever a new client arrives
        :param handler: Websocket handler
        :return:
        """
        self.id_counter += 1
        client = {
            'id': self.id_counter,
            'handler': handler,
            'address': handler.client_address
        }
        self.clients.append(client)

        print("New client connected and was given id %d" % client['id'])

    def _unicast_(self, to_client, msg):
        """
        Websocket handler calls this method whenever a private message shall be send
        :param to_client: the message receiver.
        :param msg: the message to send.
        :return:
        """
        to_client['handler'].send_message(msg)

    def _multicast_(self, msg, room=None):
        """
        Websocket handler calls this method whenever a public message shall be sent
        :param msg: the message to be sent.
        :return:
        """
        for client in self.clients:
            if (not room) or (('room' in client) and (client['room'] == room)):
                self._unicast_(client, msg)

    def handler_to_client(self, handler):
        """
        Maps a handler to its client
        :param handler: the websocket handler.
        :return: the client.
        """
        for client in self.clients:
            if client['handler'] == handler:
                return client

    def run(self):
        """
        Starts server
        :return: instance of the websocket server.
        """
        try:
            logger.info("Listening on port %d for clients.." % self.port)
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()
            logger.info("Server terminated.")
        except Exception as e:
            logger.error("ERROR: WebSocketsServer: " + str(e), exc_info=True)
            exit(1)
