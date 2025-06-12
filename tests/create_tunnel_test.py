from ngrok_manager import NgrokManager

manager = NgrokManager()
print(manager.start_tunnels_in_tmux())
connection_details = manager.get_connection_details()
print('conn details: ', connection_details)
