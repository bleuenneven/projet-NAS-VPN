from ipaddress import IPv4Address, IPv4Network

class SubNetwork:
    def __init__(self, network_address:IPv4Network, number_of_routers:int = 0, last_router_id:int = 0):
        self.network_address = network_address
        self.number_of_routers = number_of_routers
        self.assigned_router_ids = last_router_id
        self.assigned_sub_networks = 0
        self.list_ip, self.start_of_free_spots = str_network_into_list(network_address)
        
    def __str__(self):
        return self.network_address.__str__()

    def get_next_router_id(self) -> int:
        """
        Renvoie le prochain router id unique à assigner sur ce sous-réseau

        entrée : self (méthode)
        sortie : un entier positif
        """
        self.assigned_router_ids += 1
        return self.assigned_router_ids
    def get_ip_address_with_router_id(self, router_id:int) -> IPv4Address:
        """
        Renvoie l'addresse IPv6 lien global unicast à assigner au routeur d'id router_id

        entrée : self (méthode) et un entier positif de router id
        sortie : une addresse IPv6 unicast lien global valide
        """
        list_copy = [self.list_ip[i] for i in range(len(self.list_ip))]
        list_copy[-1] = router_id
        return list_of_ints_into_ipv4_address(list_copy)
    def next_subnetwork_with_n_routers(self, routers:int):
        """
        Returns a new subnetwork with an address inside the network this is executed on

        input : self (method) and a positive integer representing the expected number of routers in that new sub-network
        output : new SubNetwork object with the right address
        """
        self.assigned_sub_networks += 1
        list_copy = [self.list_ip[i] for i in range(len(self.list_ip))]
        list_copy[self.start_of_free_spots] = self.assigned_sub_networks
        return SubNetwork(list_of_ints_and_mask_to_ipv4_network(list_copy, self.start_of_free_spots + 1), routers)
    def get_subnet_mask(self):
        """
        Returns string of subnet mask

        input : self (method)
        output : string of format w.x.y.z with each being an 8-bit integer, and the whole a valid subnet mask
        """
        list_copy = [255 if i <= self.start_of_free_spots else 0 for i in range(len(self.list_ip))]
        new_string = ""
        for i in range(len(list_copy) - 1):
            new_string += f"{list_copy[i]}."
        new_string += f"{list_copy[-1]}"
        return new_string

def list_of_ints_and_mask_to_ipv4_network(ints:list[int], mask:int) -> IPv4Network:
    """
    transforme une liste de 8 entiers positifs représentables sur 16 bits et un masque de 1 à 8 en une addresse

    entrée : liste de 8 entiers en question et un masque réseau qui représente le vrai masque divisé par 16
    sortie : addresse de réseau IPv6
    """
    actual_mask = str(mask * 8)
    new_string = ""
    for i in range(len(ints) - 1):
        new_string += f"{ints[i]}."
    new_string += f"{ints[-1]}/{actual_mask}"
    return IPv4Network(new_string)


def list_of_ints_into_ipv4_address(ints:list[int]) -> IPv4Address:
    """
    transforme une liste de 8 entiers positifs représentables sur 16 bits en une addresse IPv6 unicast

    entrée : liste de 8 entiers en question
    sortie : address IPv6 unicast
    """
    final_string = ""
    for i in range(len(ints) - 1):
        final_string += f"{ints[i]}."
    final_string += f"{ints[-1]}"
    print(final_string)
    return IPv4Address(final_string)

def str_network_into_list(network_address:IPv4Network) -> tuple[list[int], int]:
    """
    transforme une adresse de réseau IPv6 en une liste d'entiers 16 bits et l'index du premier entier après le masque
    2001:5:3:0:9:3::/96
    entrée : adresse de réseau IPv6
    sortie : tuple(liste de 8 entiers 16 bits, index du premier entier dans la liste pouvant être changé après le masque)
    """
    string = str(network_address)
    mask = int(string.split("/")[1])
    free_slots_start = mask//8
    studied_number = ""
    already_one_semicolon = False
    numbers = [0 for i in range(4)]
    numbers_past_2_semicol = []
    past_2_semicol = False
    current_slot = 0
    for cara in string.split("/")[0]:
        if cara == ".":
                numbers[current_slot] = int(studied_number)
                current_slot += 1
                studied_number = ""
        else:
            studied_number += cara
    if studied_number != "":
        if past_2_semicol:
            numbers_past_2_semicol.append(int(studied_number))
        else:
            numbers[current_slot] = int(studied_number)
    for i in range(len(numbers_past_2_semicol)):
        numbers[-(i + len(numbers_past_2_semicol))] = numbers_past_2_semicol[i]
    return (numbers, free_slots_start)

print(SubNetwork(IPv4Network("112.0.0.0/8"), 10, 0).get_ip_address_with_router_id(2))
print(SubNetwork(IPv4Network("112.0.0.0/8"), 10, 0).next_subnetwork_with_n_routers(10))
