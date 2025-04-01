"""
This module manages the configuration of routers using either configuration files
or Telnet-based commands. It interacts with the GNS3 API through the `Connector`
class and organizes router configuration and network topology setup.

Functions:
- apply_router_configuration: Applies configuration to the router via file or Telnet.
- main: Orchestrates the overall configuration process for the routers.
"""

import sys
import threading

import parser
import writer
from GNS3 import Connector
from saveFile import write_string_to_file


def apply_router_configuration(connector: Connector, router: object, config_data: str, mode: str) -> None:
	"""
		Applies the configuration data to a router based on the specified mode of operation.

		Parameters:
		- connector (Connector): The GNS3 connector instance for communication with GNS3 nodes.
		- router (object): The router object containing hostname and related information.
		- config_data (str): Configuration data to apply to the router.
		- mode (str): Mode of applying configuration - either 'cfg' (file-based) or 'telnet'.

		Raises:
		- ValueError, FileNotFoundError: Errors during configuration in 'cfg' mode.
		- RuntimeError, ConnectionError: Errors during Telnet communication in 'telnet' mode.
		"""
	if mode == 'cfg':
		try:
			router_config_path = connector.get_router_config_path(router.hostname)
			write_string_to_file(router_config_path, config_data)
			print(f"Configuration for {router.hostname} written to {router_config_path}.")
		except (ValueError, FileNotFoundError) as e:
			print(f"Error processing {router.hostname}: {e}")
	elif mode == 'telnet':
		print(config_data)
		try:
			connector.send_commands_to_node(config_data, router.hostname)
			connector.close_telnet_connection(router.hostname)
			print(f"Configuration for {router.hostname} applied via Telnet.")
		except (RuntimeError, ConnectionError) as e:
			print(f"Error applying configuration to {router.hostname}: {e}")
	else:
		print(f"Invalid mode '{mode}' specified. Skipping configuration for {router.hostname}.")


def main(mode: str, file: str) -> None:
	"""
	Orchestrates the overall router configuration process based on the provided mode.

	Parameters:
	- mode (str): The mode of configuration to apply - either 'cfg' (file-based) or 'telnet'.
	- file (str): Path to the infrastructure intent file containing router configurations.

	Steps performed:
	1. Parses intent file to extract autonomous systems and router details.
	2. Sets up routers, updates their positions, and cleans up interfaces.
	3. Configures router interfaces, loopbacks, and BGP settings.
	4. Optionally applies the configurations via Telnet.

	Raises:
	- ValueError, FileNotFoundError: Errors during configuration generation or application.
	"""
	(les_as, les_routers) = parser.parse_intent_file(file)

	connector = Connector()

	as_dico = parser.as_list_into_as_number_dictionary(les_as)
	router_dico = parser.router_list_into_hostname_dictionary(les_routers)

	for router in les_routers:
		router.create_router_if_missing(connector)
		router.update_router_position(connector)
	for router in les_routers:
		router.cleanup_used_interfaces(as_dico, router_dico, connector)
		router.set_interface_configuration_data(as_dico, router_dico, mode)
	for router in les_routers:
		router.set_loopback_configuration_data(as_dico, router_dico, mode)
		router.create_missing_links(as_dico, router_dico, connector)

	if mode == 'telnet':
		threads = {router.hostname: threading.Thread() for router in les_routers}
	config_data = {router.hostname: "" for router in les_routers}
	for router in les_routers:
		router.set_bgp_config_data(as_dico, router_dico, mode)

		try:
			config_data[router.hostname] = writer.get_final_config_string(as_dico[router.AS_number], router, mode, as_dico)

			if mode == 'telnet':
				connector.start_node(router.hostname)
				threads[router.hostname] = threading.Thread(
					target=connector.telnet_connection,
					args=(router.hostname,),
					daemon=True
				)
				threads[router.hostname].start()

		except (ValueError, FileNotFoundError) as e:
			print(f"Error creating configuration for {router.hostname}: {e}")
	for router in les_routers:
		try:
			if mode == 'telnet':
				threads[router.hostname].join()
			apply_router_configuration(connector, router, config_data[router.hostname], mode)
		except (ValueError, FileNotFoundError) as e:
			print(f"Error applying configuration for {router.hostname}: {e}")


if __name__ == "__main__":
	"""
	The entry point of the program. Handles command-line arguments and
	initializes the router configuration process.

	Command-line arguments:
	- Mode (str): `cfg` or `telnet`. Determines the type of configuration application.
	- File (str): Path to the intent JSON file. Defaults to "format/full_infra.json".

	Prompts the user for mode if not provided via arguments. Exits with error if an 
	invalid mode is provided.
	"""
	args_cons = sys.argv
	if len(args_cons) == 2:
		mode = str(args_cons[1])
		file = "format/full_infra.json"
	elif len(args_cons) == 3:
		mode = str(args_cons[1])
		file = str(args_cons[2])
	else:
		mode = input("Enter mode (cfg/telnet): ").strip().lower()
		file = "format/full_infra.json"
	if mode not in ["cfg", "telnet"]:
		print("Invalid mode specified. Please use 'cfg' or 'telnet'.")
		exit(1)
	main(mode, file)
