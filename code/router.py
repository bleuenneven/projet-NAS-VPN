class Router:
    def __init__(self, hostname, liens, AS_number):
        self.hostname = hostname
        self.liens = liens
        self.AS_number = AS_number
        self.passive_interfaces = {}
        self.router_id = None
        