from ngrok_manager import NgrokManager

manager = NgrokManager()
print(manager.start_endpoints_in_tmux())
connection_details = manager.get_connection_details()
print('connection details: ', connection_details)
