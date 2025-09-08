#!/usr/bin/env python3
"""
Launch helper for OntoJSON Web Application.
Automatically finds an available port and handles stuck processes.
"""

import socket
import subprocess
import sys
import os
import time
import signal

def find_available_port(start_port=9090, max_tries=10):
    """Find an available port starting from start_port."""
    for i in range(max_tries):
        port = start_port + i
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def kill_process_on_port(port):
    """Kill any process using the specified port."""
    try:
        # Find processes using the port
        result = subprocess.run(
            f"lsof -ti :{port}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"Killed process {pid} on port {port}")
                    time.sleep(0.5)
                except:
                    pass
            return True
    except:
        pass
    return False

def main():
    """Main launch function."""
    print("=== OntoJSON Web Application Launcher ===\n")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Launch OntoJSON Web Application')
    parser.add_argument('--port', type=int, help='Preferred port (will find alternative if busy)')
    parser.add_argument('--force', action='store_true', help='Force kill processes on desired port')
    args = parser.parse_args()
    
    preferred_ports = []
    
    # Add user-specified port first
    if args.port:
        preferred_ports.append(args.port)
    
    # Add common ports (avoiding 5000 on macOS)
    preferred_ports.extend([9090, 8080, 8000, 3000, 4000])
    
    # Remove port 5000 on macOS (used by AirPlay)
    if sys.platform == 'darwin':
        print("Note: Avoiding port 5000 (used by macOS AirPlay)\n")
        preferred_ports = [p for p in preferred_ports if p != 5000]
    
    selected_port = None
    
    # Try each preferred port
    for port in preferred_ports:
        print(f"Checking port {port}...")
        
        # Check if port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                selected_port = port
                print(f"  ✓ Port {port} is available")
                break
        except OSError:
            print(f"  ✗ Port {port} is in use")
            
            if args.force and port == args.port:
                print(f"  → Attempting to free port {port}...")
                if kill_process_on_port(port):
                    time.sleep(1)
                    # Try again
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.bind(('', port))
                            selected_port = port
                            print(f"  ✓ Port {port} is now available")
                            break
                    except:
                        print(f"  ✗ Failed to free port {port}")
    
    if not selected_port:
        # Find any available port
        print("\nSearching for any available port...")
        selected_port = find_available_port(10000)
        
        if not selected_port:
            print("\n❌ ERROR: Could not find any available port!")
            print("Please manually stop conflicting processes and try again.")
            sys.exit(1)
    
    print(f"\n🚀 Starting OntoJSON Web Application on port {selected_port}")
    print(f"   URL: http://localhost:{selected_port}")
    print("\n   Press Ctrl+C to stop the server\n")
    print("-" * 50)
    
    # Launch the application
    try:
        subprocess.run([
            sys.executable,
            'app.py',
            '--port', str(selected_port)
        ])
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
    except Exception as e:
        print(f"\n❌ Error launching application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()