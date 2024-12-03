import socket
import select
import argparse
import sys
import ipaddress

READ = -1
WRITE = 1

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

def chat(client_socket, message):
    """Send a CHAT message to the peer."""
    try:
        chat_message = f"CHAT\r\nMESSAGE:{message}\r\n\r\n"
        client_socket.sendall(chat_message.encode())
    except (BrokenPipeError, ConnectionResetError):
        print("Failed to send: peer disconnected")
        raise  # Re-raise to handle in main loop

# Send QUIT message
def quit_to_peer(client_socket):
    """Send a QUIT message to the peer."""
    quit_message = "QUIT\r\nGoodbye!\r\n\r\n"
    try:
        if client_socket:
            client_socket.sendall(quit_message.encode())
            print("QUIT message sent: Goodbye!")
    except (BrokenPipeError, ConnectionResetError):
        print("Failed to send: peer disconnected")
        raise  # Re-raise to handle in main loop

parser = argparse.ArgumentParser(description="TCP Client for Chat Application")
parser.add_argument("--id", required=True, help="Client ID")
parser.add_argument("--port", type=int, required=True, help="Client Port")
parser.add_argument("--server", required=True, help="Server IP and Port (e.g., 127.0.0.1:5000)")
args = parser.parse_args()

if (args.port > 1024 and args.port < 65536):
    client_port = args.port 
else:
    client_port = 5001
    print("Error: Invalid client port. Using default port 5001.")
client_state = "Zero"
client_registered = False
client_socket = None
client_id = args.id
peer_id = None
peer_ip = None
peer_port = None
server_address = args.server
server_ip, server_port = server_address.split(":")
read_write = 0

# Validating client and server port and address
try:
    client_port = int(client_port)
    ipaddress.ip_address(server_ip)
    server_port = int(server_port)
except ValueError:
    print("Error: Invalid client or server address format. Use --port=<Port> --server='<IP>:<Port>'.")
    sys.exit(1)

while True:
    # Check input first to stall while waiting for commands. Bypassed when quitting and waiting and chatting.
    if client_state != "Quit" and client_state != "Wait" and client_state != "Chat":
        user_input = sys.stdin.readline().strip()
    else: user_input = None

    # Common commands: /id, /quit
    if user_input == "/id":
        print(f"Client ID: {client_id}")
    elif user_input == "/quit":
        client_state = "Quit"
        continue

    # Zero state: handling for /register, /bridge
    if client_state == "Zero":
        if user_input == "/register":
            # Register with the server
            if not client_registered:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((server_ip, server_port))
                    print(f"Connected to server at {server_ip}:{server_port}")
                    # Register with the server
                    register(client_socket, client_id, "127.0.0.1", client_port)
                    client_registered = True
                    client_socket.close()
                    client_socket = None
                except Exception as e:
                    print(f"Error registering to server: {e}")
            else:
                print("Error: Client already registered to server.")
                continue
        elif user_input == "/bridge":
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((server_ip, server_port))
                print(f"Connected to server at {server_ip}:{server_port}")
            except Exception as e:
                print(f"Error connecting to server: {e}")
                continue
            if client_registered:
                server_response = bridge(client_socket, client_id)
                for line in server_response.split("\r\n"):
                    if line.startswith("clientID:"):
                        peer_id = line.split(":")[1].strip()
                        if peer_id == "":
                            client_state = "Wait"
                            read_write = READ
                            break
                    if line.startswith("IP:"):
                        peer_ip = line.split(":")[1].strip()
                    if line.startswith("Port:"):
                        peer_port = int(line.split(":")[1].strip())
            else:
                print("Error: Client not registered.")
                continue
            client_socket.close()
            client_socket = None
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
            # Set up listening socket
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
                            else:
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
        try:
            if not client_socket:
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
                # if read_write == 0:
                #     read_write = WRITE
                readable, _, _ = select.select([client_socket, sys.stdin], [], [], None)
                if read_write == WRITE:
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
                        except Exception as e:
                            print(f"Error sending to peer: {e}")
                            client_state = "Quit"
                            break
                        read_write *= -1
                    else:
                        continue
 
                elif read_write == READ:
                    try:
                        for sock in readable:
                            if sock == client_socket:  # Message from peer
                                response = client_socket.recv(1024).decode().strip()
                                if not response:
                                    print("Peer disconnected")
                                    client_state = "Quit"
                                    break
                                elif response.startswith("CHAT"):
                                    lines = response.split("\r\n")
                                    print(lines[1].split(":")[1].strip())
                                elif response.startswith("QUIT"):
                                    print("Peer quit")
                                    client_socket.close()
                                    client_socket = None
                                    client_state = "Quit"
                                    break
                                else:
                                    print("Error: Invalid response from peer: ", response)
                                read_write *= -1
                            
                            elif sock == sys.stdin:  # User input during READ state
                                user_input = sys.stdin.readline().strip()
                                if user_input == "/quit":
                                    client_state = "Quit"
                                    break
                                else:
                                    print("Can't send message while waiting to receive")
                    
                    except KeyboardInterrupt:
                        client_state = "Quit"
                        break
                    except Exception as e:
                        print(f"Error receiving from peer: {e}")
                        client_state = "Quit"
                        break
                else:
                    print("Error: Invalid read/write state.")
                    client_state = "Quit"
                    break
            except KeyboardInterrupt:
                client_state = "Quit"
                break

    elif client_state == "Quit":
        if client_socket:
            print("\n")
            quit_to_peer(client_socket)
            client_socket.close()
        sys.exit(0)
