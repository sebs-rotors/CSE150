import socket
import select
import argparse
import sys
import ipaddress

# Send REGISTER request
def register(client_socket, client_id, client_ip, client_port):
    """Send a REGISTER request to the server."""
    register_request = (
        f"REGISTER\r\n"
        f"clientID: {client_id}\r\n"
        f"IP: {client_ip}\r\n"
        f"Port: {client_port}\r\n\r\n"
    )
    client_socket.sendall(register_request.encode())
    response = client_socket.recv(1024).decode().strip()
    print("Server response:", response)
    return response

# Send BRIDGE request
def bridge(client_socket, client_id):
    """Send a BRIDGE request to the server."""
    bridge_request = (
        f"BRIDGE\r\n"
        f"clientID: {client_id}\r\n\r\n"
    )
    client_socket.sendall(bridge_request.encode())
    response = client_socket.recv(1024).decode().strip()
    print("Server response:", response)
    return response

# Send QUIT message
def quit_to_peer(client_socket):
    """Send a QUIT message to the peer."""
    quit_message = "QUIT\r\nGoodbye!\r\n\r\n"
    client_socket.sendall(quit_message.encode())
    print("QUIT message sent: Goodbye!")

parser = argparse.ArgumentParser(description="TCP Client for Chat Application")
parser.add_argument("--id", required=True, help="Client ID")
parser.add_argument("--port", type=int, required=True, help="Client Port")
parser.add_argument("--server", required=True, help="Server IP and Port (e.g., 127.0.0.1:5000)")
args = parser.parse_args()

client_state = "Zero"
client_registered = False
client_socket = None
client_id = args.id
client_port = args.port
peer_id = None
peer_ip = None
peer_port = None
server_address = args.server
server_ip, server_port = server_address.split(":")

# Validating server port and address
try:
    ipaddress.ip_address(server_ip)
    server_port = int(server_port)
except ValueError:
    print("Error: Invalid server address format. Use <IP>:<Port>.")
    sys.exit(1)

while True:
    if client_state == "Zero":
        # Wait for user input to register, bridge, chat, or quit
        user_input = sys.stdin.readline().strip()
        if user_input == "/register":
            # Connect to the server
            if not client_socket:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((server_ip, server_port))
                    print(f"Connected to server at {server_ip}:{server_port}")
                except Exception as e:
                    print(f"Error connecting to server: {e}")
                    sys.exit(1)
                # Register with the server
                register(client_socket, client_id, "127.0.0.1", client_port)
                client_registered = True
            else:
                print("Error: Client already connected to server.")
                continue
        elif user_input == "/bridge":
            if client_registered:
                server_response = bridge(client_socket, client_id)
                for line in server_response.split("\r\n"):
                    if line.startswith("clientID:"):
                        peer_id = line.split(":")[1].strip()
                        if peer_id == None:
                            client_state = "Wait"
                        else:
                            client_state = "Chat"
                            client_socket.close()
                            client_socket = None
                    elif line.startswith("IP:"):
                        peer_ip = line.split(":")[1].strip()
                    elif line.startswith("Port:"):
                        peer_port = line.split(":")[1].strip()
                    else:
                        print(line)
            else:
                print("Error: Client not registered.")
                continue
        else:
            print("Error: Invalid command.")
    elif client_state == "Wait":
        print("Waiting for peer connection...")
    elif client_state == "Chat":
        print("Chatting with peer...")

    # try:
    #     while True:
    #         # Monitor both stdin and the server socket
    #         sockets = [client_socket, sys.stdin]
    #         readable, _, _ = select.select(sockets, [], [])

    #         for sock in readable:
    #             if sock == client_socket:  # Handle server messages
    #                 message = client_socket.recv(1024).decode().strip()
    #                 if not message:
    #                     print("Server disconnected.")
    #                     sys.exit(0)
    #                 print(f"Server: {message}")

    #             elif sock == sys.stdin:  # Handle user input
    #                 user_input = sys.stdin.readline().strip()
    #                 if user_input == "/register":
    #                     register(client_socket, client_id, "127.0.0.1", client_port)
    #                 elif user_input == "/bridge":
    #                     bridge(client_socket, client_id)
    #                 elif user_input == "/id":
    #                     print(f"Client ID: {client_id}")

    #                 elif user_input == "/quit":
    #                     quit_to_peer(client_socket)
    #                     client_socket.close()
    #                     sys.exit(0)
    #                 else:
    #                     print("Error: Invalid command.")

