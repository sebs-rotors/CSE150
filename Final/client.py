import socket
import select
import argparse
import sys
import ipaddress

READ = -1
WRITE = 1

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

def chat(client_socket, message):
    """Send a CHAT message to the peer."""
    try:
        chat_message = f"CHAT\r\nMESSAGE:{message}\r\n\r\n"
        client_socket.sendall(chat_message.encode())
    except (BrokenPipeError, ConnectionResetError):
        print("Failed to send: peer disconnected")
        client_socket.close()
        raise  # Re-raise to handle in main loop

def quit_to_peer(client_socket):
    """Send a QUIT message to the peer."""
    try:
        if client_socket:
            quit_message = "QUIT\r\nGoodbye!\r\n\r\n"
            client_socket.sendall(quit_message.encode())
            print("\nQUIT message sent: Goodbye!")
    except (BrokenPipeError, ConnectionResetError):
        print("Failed to send: peer disconnected")
        client_socket.close()
        raise

def handle_peer_message(client_socket, response):
    """Handle incoming peer messages."""
    if not response:
        print("Peer disconnected")
        return "Quit"
    elif response.startswith("CHAT"):
        message = response.split("\r\n")[1].split(":")[1].strip()
        print(message)
        return "Chat"
    elif response.startswith("QUIT"):
        print("Peer quit")
        client_socket.close()
        return "Quit"
    else:
        print("Error: Invalid response from peer:", response)
        return "Chat"

# Parse command line arguments
parser = argparse.ArgumentParser(description="TCP Client for Chat Application")
parser.add_argument("--id", required=True, help="Client ID")
parser.add_argument("--port", type=int, required=True, help="Client Port")
parser.add_argument("--server", required=True, help="Server IP and Port (e.g., 127.0.0.1:5000)")
args = parser.parse_args()

# Initialize client variables
client_port = args.port if 1024 < args.port < 65536 else 5001
if client_port != args.port:
    print("Error: Invalid client port. Using default port 5001.")

client_state = "Zero"
client_registered = False
client_socket = None
client_id = args.id
peer_id = peer_ip = None
peer_port = None
server_ip, server_port = args.server.split(":")
read_write = 0

# Validate addresses
try:
    client_port = int(client_port)
    ipaddress.ip_address(server_ip)
    server_port = int(server_port)
except ValueError:
    print("Error: Invalid client or server address format. Use --port=<Port> --server='<IP>:<Port>'.")
    sys.exit(1)

while True:
    # Get user input except during special states
    if client_state not in ["Quit", "Wait", "Chat"]:
        user_input = sys.stdin.readline().strip()
    else:
        user_input = None

    # Handle common commands
    if user_input == "/id":
        print(f"Client ID: {client_id}")
    elif user_input == "/quit":
        client_state = "Quit"
        continue

    # State machine
    if client_state == "Zero":
        if user_input == "/register":
            if not client_registered:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((server_ip, server_port))
                    print(f"Connected to server at {server_ip}:{server_port}")
                    register(client_socket, client_id, "127.0.0.1", client_port)
                    client_registered = True
                    client_socket.close()
                    client_socket = None
                except Exception as e:
                    print(f"Error registering to server: {e}")
            else:
                print("Error: Client already registered to server.")

        elif user_input == "/bridge":
            if not client_registered:
                print("Error: Client not registered.")
                continue

            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((server_ip, server_port))
                print(f"Connected to server at {server_ip}:{server_port}")
                
                server_response = bridge(client_socket, client_id)
                for line in server_response.split("\r\n"):
                    if line.startswith("clientID:"):
                        peer_id = line.split(":")[1].strip()
                        if not peer_id:
                            client_state = "Wait"
                            read_write = READ
                            break
                    elif line.startswith("IP:"):
                        peer_ip = line.split(":")[1].strip()
                    elif line.startswith("Port:"):
                        peer_port = int(line.split(":")[1].strip())
                
                client_socket.close()
                client_socket = None
            except Exception as e:
                print(f"Error connecting to server: {e}")

        elif user_input == "/chat":
            if client_registered and peer_id:
                client_state = "Chat"
                read_write = WRITE
            else:
                print("Error: Client not registered or no peer ID.")
        else:
            print("Error: Invalid command.")

    elif client_state == "Wait":
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.bind(('127.0.0.1', client_port))
            peer_socket.listen(1)
            print("Waiting for peer connection...")

            while client_state == "Wait":
                try:
                    readable, _, _ = select.select([peer_socket, sys.stdin], [], [], 1.0)
                    for sock in readable:
                        if sock == peer_socket:
                            client_socket, addr = peer_socket.accept()
                            print(f"Peer connected from {addr[0]}:{addr[1]}")
                            client_state = "Chat"
                            read_write = READ
                            break
                        elif sock == sys.stdin:
                            user_input = sys.stdin.readline().strip()
                            if user_input == "/quit":
                                client_state = "Quit"
                                break
                            print("Can't send message while waiting to connect")
                except KeyboardInterrupt:
                    client_state = "Quit"
                    break

        except Exception as e:
            print(f"Error in wait state: {e}")
            client_state = "Quit"
        finally:
            if peer_socket:
                peer_socket.close()

    elif client_state == "Chat":
        if not client_socket:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((peer_ip, peer_port))
                print(f"Connected to peer at {peer_ip}:{peer_port}")
                read_write = WRITE
            except Exception as e:
                print(f"Error connecting to peer: {e}")
                print(f"Relevant Details: {peer_ip}:{peer_port}")
                continue

        while client_state == "Chat":
            try:
                readable, _, _ = select.select([client_socket, sys.stdin], [], [], None)
                
                if read_write == WRITE:
                    for sock in readable:
                        if sock == client_socket:
                            response = client_socket.recv(1024).decode().strip()
                            if response.startswith("QUIT"):
                                print("Peer quit")
                                client_socket.close()
                                client_socket = None
                                client_state = "Quit"
                                break
                        elif sock == sys.stdin:
                            chat_input = sys.stdin.readline().strip()
                            if chat_input == "/quit":
                                client_state = "Quit"
                                break
                            try:
                                chat(client_socket, chat_input)
                                read_write *= -1
                            except Exception as e:
                                print(f"Error sending to peer: {e}")
                                client_state = "Quit"
                                break

                elif read_write == READ:
                    for sock in readable:
                        if sock == client_socket:
                            response = client_socket.recv(1024).decode().strip()
                            new_state = handle_peer_message(client_socket, response)
                            if new_state == "Quit":
                                client_state = "Quit"
                                break
                            read_write *= -1
                        
                        elif sock == sys.stdin:
                            user_input = sys.stdin.readline().strip()
                            if user_input == "/quit":
                                client_state = "Quit"
                                break
                            print("Can't send message while waiting to receive")
                
                else:
                    print("Error: Invalid read/write state.")
                    client_state = "Quit"
                    break

            except KeyboardInterrupt:
                client_state = "Quit"
                break
            except Exception as e:
                print(f"Error in chat state: {e}")
                client_state = "Quit"
                break

    elif client_state == "Quit":
        try:
            if client_socket:
                quit_to_peer(client_socket)
                client_socket.close()
        except Exception:
            pass
        sys.exit(0)
