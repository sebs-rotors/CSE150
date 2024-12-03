import socket
import select
import sys
import argparse
# Store registered clients: {clientID: (IP, Port)}
registered_clients = {}

# Handle REGISTER requests
def handle_register(client_socket, client_address, message):
    """Process REGISTER request and respond with REGACK."""
    headers = parse_headers(message)
    client_id = headers.get("clientID")
    client_ip = headers.get("IP", client_address[0])
    client_port = headers.get("Port")

    if not client_id or not client_ip or not client_port:
        print("Error: Invalid REGISTER message format.")
        return

    # Store client information
    registered_clients[client_id] = (client_ip, client_port)
    print(f"REGISTER: {client_id} from {client_ip}:{client_port} received")

    # Respond with REGACK
    regack_message = (
        f"REGACK\r\n"
        f"clientID: {client_id}\r\n"
        f"IP: {client_ip}\r\n"
        f"Port: {client_port}\r\n"
        f"Status: registered\r\n\r\n"
    )
    client_socket.sendall(regack_message.encode())

# Handle BRIDGE requests
def handle_bridge(client_socket, client_id):
    """Process BRIDGE request and respond with BRIDGEACK."""
    if client_id not in registered_clients:
        print(f"Error: Client {client_id} not registered.")
        return

    # Get the peer client (if exists)
    peer_id, peer_info = None, ("", "")
    for registered_id, info in registered_clients.items():
        if registered_id != client_id:
            peer_id, peer_info = registered_id, info
            break

    # Get client's own info from registered_clients
    client_ip, client_port = registered_clients[client_id]
    peer_ip, peer_port = peer_info

    # Print in requested format
    if peer_id:
        print(f"BRIDGE: {client_id} {client_ip}:{client_port} {peer_id} {peer_ip}:{peer_port}")
    else:
        print(f"BRIDGE: {client_id} {client_ip}:{client_port}")

    # Respond with BRIDGEACK
    bridgeack_message = (
        f"BRIDGEACK\r\n"
        f"clientID: {peer_id or ''}\r\n"
        f"IP: {peer_ip or ''}\r\n"
        f"Port: {peer_port or ''}\r\n\r\n"
    )
    client_socket.sendall(bridgeack_message.encode())

# Parse headers from a message
def parse_headers(message):
    """Extract headers from the message."""
    lines = message.split("\r\n")
    headers = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers

# Handle incoming client connections
def handle_client(client_socket, client_address):
    """Receive and process client messages."""
    try:
        message = client_socket.recv(1024).decode().strip()
        if not message:
            return False

        if message.startswith("REGISTER"):
            handle_register(client_socket, client_address, message)
        elif message.startswith("BRIDGE"):
            headers = parse_headers(message)
            client_id = headers.get("clientID")
            if client_id:
                handle_bridge(client_socket, client_id)
            else:
                print("Error: BRIDGE message missing clientID.")
        else:
            print("Error: Unknown request type.")
        return True
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
        return False

# Handle server commands from stdin
def handle_server_command(command):
    """Process server commands entered via stdin."""
    if command == "/info":
        print("Registered clients:")
        for client_id, (ip, port) in registered_clients.items():
            print(f"{client_id} {ip}:{port}")
    else:
        print("Error: Unknown command.")

parser = argparse.ArgumentParser(description="Server for Chat Application")
parser.add_argument("--port", type=int, required=True, help="Server Port")
args = parser.parse_args()

server_port = args.port if 1024 < args.port < 65536 else 8080
if server_port != args.port:
    print("Error: Invalid server port. Using default port 8080.")
server_ip = "127.0.0.1"
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((server_ip, server_port))
server_socket.listen(3)

print(f"Server listening on {server_ip}:{server_port}")
sockets_list = [server_socket, sys.stdin]

try:
    while True:
        readable, _, _ = select.select(sockets_list, [], [], 0.2)
        for notified_socket in readable:
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                print(f"New connection from {client_address}")
                sockets_list.append(client_socket)
            elif notified_socket == sys.stdin:
                command = sys.stdin.readline().strip()
                handle_server_command(command)
            else:
                if not handle_client(notified_socket, notified_socket.getpeername()):
                    sockets_list.remove(notified_socket)
                    notified_socket.close()
except KeyboardInterrupt:
    print("\nShutting down server.")
    sys.exit(0)
finally:
    for sock in sockets_list:
        sock.close()
    sys.exit(0)
