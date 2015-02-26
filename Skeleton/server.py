'''
KTN-project 2013 / 2014
Very simple server implementation that should serve as a basis
for implementing the chat server
'''
import SocketServer
import json
import re

'''
The RequestHandler class for our server.

It is instantiated once per connection to the server, and must
override the handle() method to implement communication to the
client.
'''


class ClientHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        # Get a reference to the socket object
        self.connection = self.request
        # Get the remote ip adress of the socket
        self.ip = self.client_address[0]
        # Get the remote port number of the socket
        self.port = self.client_address[1]
        print 'Client connected @' + self.ip + ':' + str(self.port)
        self.listening = True

        # New client set to not logged in
        self.logged_in = False
        while self.listening:
            data = self.connection.recv(4096).strip()
            if data:
                decoded_data = json.loads(data) # Decode data from JSON
                request = decoded_data["request"] # Check user action
                if self.logged_in:
                    if request == "login":
                        error_message = {'response':'login', 'error':'Already logged in'}
                        self.send_message(json.dumps(error_message))
                    elif request == "logout":
                        self.logout()
                    elif request == "message":
                        self.server.broadcast_message(decoded_data, self)
                else:
                    if request == "login":
                        attemptedUsername = decoded_data["username"]
                        if attemptedUsername in server.get_connected_user_names(): # Check if username already taken
                            error_message = {"response":"login", 'error':'Name already taken.', 'username':attemptedUsername}
                            self.send_message(json.dumps(error_message))
                        else:
                            if re.match("^[0-9A-Za-z_]{3,10}$", attemptedUsername):
                                # Username must be 3-10 chars long and consist of only alphanumeric characters
                                self.username = decoded_data["username"]
                                self.logged_in = True
                                self.server.add_logged_in_client(self) # Add client to server list of logged in clients
                                previous_messages = self.server.get_message_backlog() # Get backlog
                                login_message = {"response":"login", "username":self.username, "messages":previous_messages}
                                self.send_message(json.dumps(login_message))
                            else:
                                error_message = {'response':'login', 'error':'Invalid username.\nMust be 3-10 characters long, alphanumeric with "_" or "-".', 'username':attemptedUsername}
                                self.send_message(json.dumps(error_message))
                    elif request == "logout":
                        error_message = {"response":"logout", "error":"Not logged in!"}
                        self.send_message(json.dumps(error_message))
                    elif request == "message":
                        error_message = {"response":"message", "error":"You have to log in before sending a message."}
                        self.send_message(json.dumps(error_message))
            else:
                print 'Client disconnected!'
                if self.logged_in:
                    self.logout()
                break

    def send_message(self, message):
        # Sends a string to the connected client
        self.connection.sendall(message)

    def logout(self):
        self.logged_in = False
        self.server.remove_logged_in_client(self)
        logout_message = {"response":"logout", "username":self.username}
        self.send_message(json.dumps(logout_message))
        #self.listening = False

'''
This will make all Request handlers being called in its own thread.
Very important, otherwise only one client will be served at a time
'''


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)
        self.log = []
        self.connected_clients = []

    def get_connected_user_names(self):
        name_list = []
        for client in self.connected_clients:
            name_list.append(client.username)
        return name_list

    def broadcast_message(self, message, client_handler):
        # Pushes a message to the log and sends it to all logged in clients
        message.pop("request", None)
        message["response"] = "message"  # Adds a server response header
        message["username"] = client_handler.username  # Stamps it with the current username
        self.log.append(message)
        json_dump = json.dumps(message)  # Generates a json dump to send to all logged in clients
        for client in self.connected_clients:
            client.send_message(json_dump)

    def add_logged_in_client(self, client_handler):
        # Adds a ClientHandler to the current list of logged in clients
        self.connected_clients.append(client_handler)
        # TODO: Send a notification to all logged in clients
        notification = client_handler.username + " has logged in."
        message_dict = {'response': "notification", 'message': notification}
        for client in self.connected_clients:
            client.send_message(json.dumps(message_dict))

    def remove_logged_in_client(self, client_handler):
        # Removes the current client handler from the list of logged in clients.
        # Used to clean up after logout
        self.connected_clients.remove(client_handler)
        notification = client_handler.username + " has logged out."
        message_dict = {"response": "notification", "message": notification}
        for client in self.connected_clients:
            client.send_message(json.dumps(message_dict))

    def get_message_backlog(self):
        # Returns the last messages; max 20
        return self.log[-20:]

if __name__ == "__main__":
    # Create the server, binding it to the specified host and port
    HOST = 'localhost'
    PORT = 24601

    server = ThreadedTCPServer((HOST, PORT), ClientHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print