from websocket_server.WebSocketServer import WebSocketServer

PORT = 9001
server = WebSocketServer(PORT)
server.run()
