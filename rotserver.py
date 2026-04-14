import sys
from core.multiplayer.server import start_dedicated_server

def main():
    # Allow passing an optional server name via the command line
    # Example: python run_server.py MyAwesomeServer
    server_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        start_dedicated_server(server_name)
    except KeyboardInterrupt:
        print("\n[System] Server shutdown initiated by user. Goodbye!")
        sys.exit(0)

if __name__ == '__main__':
    main()