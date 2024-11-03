#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

from typing import List, Dict
from enum import Enum



class PortState(Enum):
    BLOCKING_PORT = "blocked port"
    DESIGNATED_PORT = "designated port"
    ROOT_PORT = "root port"


class SwitchPort:
    def __init__(self, port_id: int, port_name: str):
        self.port_id: int = port_id
        self.port_name: str = port_name



class Trunk(SwitchPort):
    def __init__(self, port_id: int, port_name: str):
        super().__init__(port_id, port_name)
        self.isTrunk: bool = True
        self.port_state: PortState = PortState.DESIGNATED_PORT
    
    def __str__(self):
        """
        Returns a pretty-formatted JSON string
        """
        string = ""
        string += "{\n"
        string += f"\tPort ID: {self.port_id},\n"
        string += f"\tPort Name: {self.port_name},\n"
        string += f"\tPort Type: TRUNK,\n"
        
        if self.port_state == PortState.BLOCKING_PORT:
            string = f"\tPort State: BLOCKING\n"
        elif self.port_state == PortState.ROOT_PORT:
            string = f"\tPort State: ROOT PORT (is also Listening)\n"
        elif self.port_state == PortState.DESIGNATED_PORT:
            string = f"\tPort State: DESIGNATED PORT (is also Listening)\n"

        string = "}\n"
        return string


class Access(SwitchPort):
    def __init__(self, port_id: int, port_name: str, vlan_id: int):
        super().__init__(port_id, port_name)
        self.vlan_id: int = vlan_id

    def __str__(self):
        """
        Returns a pretty-formatted JSON string
        """
        string = ""
        string += "{\n"
        string += f"\tPort ID: {self.port_id},\n"
        string += f"\tPort Name: {self.port_name},\n"
        string += f"\tPort Type: ACCESS (vlan_id={self.vlan_id})\n"
        string += "}\n"
        return string





class SwitchConfig:
    def __init__(self, switch_id: int, switch_priority: int, interfaces: List[SwitchPort] = None):
        """
        Configuratia switch-ului.
        """
        self.switch_id: int = switch_id
        self.switch_priority: int = switch_priority
        self.interfaces: List[SwitchPort] = interfaces

        # Variabile pentru STP (setate la valorile implicite la crearea switch-ului)
        self.own_bridge_id: int = switch_priority
        self.root_bridge_id: int = self.own_bridge_id
        self.root_path_cost: int = 0
        self.all_trunk_ports: List[Trunk] = []

        # La initializare, switch-ul este ROOT BRIDGE
        self.is_root_bridge: bool = True

    def __str__(self):
        """
        Returns a pretty-formatted JSON string
        """
        string = ""
        string += "{\n"
        string += f"\t\"SwitchID\": {self.switch_id},\n"
        string += f"\t\"Switch Priority\": {self.switch_priority},\n"

        if len(self.interfaces) == 0:
            string += "\t\"Switch Interfaces\": []\n"
            return string

        string += "\t\"Switch Interfaces\":\n"
        string += "\t[\n"

        iter = 0

        # Iterating all KEYS (interface names) and VALUES (interface values "T"/number)
        for port in self.interfaces:
            string += "\t\t{\n"
            string += f"\t\t\tPort name: {port.port_name},\n"
            string += f"\t\t\tPort ID: {port.port_id},\n"

            if isinstance(port, Trunk):
                string += "\t{\n"
                string += f"\t\tPort ID: {port.port_id},\n"
                string += f"\t\tPort Name: {port.port_name},\n"
                string += f"\t\tPort Type: TRUNK,\n"
                
                if port.port_state == PortState.BLOCKING_PORT:
                    string += f"\t\tPort State: BLOCKING\n"
                elif port.port_state == PortState.ROOT_PORT:
                    string += f"\t\tPort State: ROOT PORT (is also Listening)\n"
                elif port.port_state == PortState.DESIGNATED_PORT:
                    string += f"\t\tPort State: DESIGNATED PORT (is also Listening)\n"

                string += "\t}\n"
            elif isinstance(port, Access):
                string += "\t{\n"
                string += f"\t\tPort ID: {port.port_id},\n"
                string += f"\t\tPort Name: {port.port_name},\n"
                string += f"\t\tPort Type: ACCESS (vlan_id={port.vlan_id})\n"
                string += "}\n"


            iter = iter + 1
            string += "\t\t},\n" if iter != len(self.interfaces) else "\t\t}\n"

        string += "\t]\n"
        string += "}\n"
        return string
    
    def get_switch_port_by_name(self, name: str) -> SwitchPort:
        for port in self.interfaces:
            if name == port.port_name:
                return port
        return None
    

    def compute_finding_all_trunk_ports(self) -> None:
        self.all_trunk_ports: List[Trunk] = []
        
        for port in self.interfaces:
            if isinstance(port, Trunk):
                self.all_trunk_ports.append(port)
        return


def read_config_file(switch_id: int, filepath: str) -> SwitchConfig:
    try:
        with open(filepath, 'r') as file:
            switch_priority = int(file.readline().strip())
            interfaces: List[SwitchPort] = []

            global map_interface_names_with_ids

            for line in file:
                line_parts = line.strip().split()
                interface_name: str = line_parts[0]
                interface_id: int = map_interface_names_with_ids[interface_name]
                
                if line_parts[1] == "T":
                    interfaces.append(Trunk(interface_id, interface_name))
                else:
                    vlan_id = int(line_parts[1])
                    interfaces.append(Access(interface_id, interface_name, vlan_id))
            
            return SwitchConfig(switch_id, switch_priority, interfaces)
    except Exception as err:
        print(f"[ERROR] Eroare la citirea fisierului {filepath}: {err}")
        sys.exit(255)





def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)




def is_unicast(mac: bytes) -> bool:
    """
    Functia primeste o adresa MAC si returneaza daca este adresa UNICAST sau nu.

    O adresa MAC este considerata UNICAST
    daca primul bit din primul octet este setat la 0
    """
    return (mac[0] & 1) == 0


def mac_addr_to_string(mac: bytes) -> str:
    """
    Converteste o adresa MAC (primita sub forma de bytes) la un string human-readable
    """
    formatted_mac = ":".join(f"{byte:02x}" for byte in mac)
    return formatted_mac
    


def is_bpdu(dest_mac: bytes) -> bool:
    """
    Functia primeste o adresa MAC (adresa MAC destinatie a pachetului)
    si returneaza daca este adresa de BPDU sau nu

    Cadrele BPDU sunt identificate prin adresa multicast MAC destinatie,
    01:80:C2:00:00:00

    Adresa MAC este primita sub forma de bytes
    """
    return mac_addr_to_string(dest_mac) == "01:80:c2:00:00:00"




def enable_VLAN_sending(vlan_id_packet: int, src_interface_id: int, dst_interface_id: int, length: int, data: bytes) -> None:
    """
    Function 'wrapped' on send_to_link
    Additional logic for VLAN tag   -> Implements VLAN support
    """

    global network_switch

    if network_switch is None:
        # Switch is not in the list of switches
        send_to_link(dst_interface, length, data)
        return
    


    src_interface_name: str = get_interface_name(src_interface_id)
    dst_interface_name: str = get_interface_name(dst_interface_id)

    src_port: SwitchPort = network_switch.get_switch_port_by_name(src_interface_name)
    dst_port: SwitchPort = network_switch.get_switch_port_by_name(dst_interface_name)



    if isinstance(dst_port, Trunk) and dst_port.port_state == PortState.BLOCKING_PORT:
        # Nu trimitem NIMIC pe porturile Trunk BLOCATE (este legat de STP)
        return

    if isinstance(src_port, Access) and isinstance(dst_port, Access):
        # Access -> Trunk
        if src_port.vlan_id != dst_port.vlan_id:
            # Nu trimitem intre VLAN-uri diferite
            return
        send_to_link(dst_interface_id, length, data)
        return
    if isinstance(src_port, Trunk) and isinstance(dst_port, Trunk):
        # Trunk -> Trunk
        send_to_link(dst_interface_id, length, data)
        return
    if isinstance(src_port, Access) and isinstance(dst_port, Trunk):
        # Access -> Trunk
        new_data = data[0:12] + create_vlan_tag(src_port.vlan_id) + data[12:]
        new_length = length + 4       # The size of VLAN TAG is 4 bits
        send_to_link(dst_interface_id, new_length, new_data)
        return
    if isinstance(src_port, Trunk) and isinstance(dst_port, Access):
        # Trunk -> Access
        if dst_port.vlan_id != int(vlan_id_packet):
            # Nu facem transmisia intre doua VLAN-uri diferite
            return
        new_data = data[0:12] + data[16:]
        new_length = length - 4       # Removing 4 bits (size of VLAN)
        send_to_link(dst_interface_id, new_length, new_data)
        return
    
    
    send_to_link(dst_interface_id, length, data)
    return
    






def send_bpdu_to_link(trunk_port: SwitchPort, root_bridge_id: int, sender_bridge_id: int, sender_path_cost: int) -> None:
    dest = "01:80:c2:00:00:00"
    dst = bytes.fromhex(dest.replace(":", ""))
    # source MAC is switch MAC
    src = get_switch_mac()            
    # packet length
    bpdu_length = 44
    llc_length = bpdu_length.to_bytes(2, byteorder='big')
    dsap = 0x42
    ssap = 0x42
    control = 0x03
    llc_header = dsap.to_bytes(1, byteorder='big') + ssap.to_bytes(1, byteorder='big') + control.to_bytes(1, byteorder='big')
    # bpdu header length
    bpdu_header = 23
    bpdu_header = bpdu_header.to_bytes(4, byteorder='big')
    # uint8_t root_bridge_id[8]
    root_bridge_bytes = root_bridge_id.to_bytes(8, byteorder='big')
    # uint32_t root_path_cost
    root_path_bytes = sender_path_cost.to_bytes(4, byteorder='big')
    # uint8_t bridge_id[8]
    sender_bridge_bytes = sender_bridge_id.to_bytes(8, byteorder='big')
    # uint16_t port_id
    port_id = trunk_port.port_id.to_bytes(2, byteorder='big')

    # get data to send
    bpdu_data = dst + src + llc_length + llc_header + bpdu_header + bytes([0]) + root_bridge_bytes + root_path_bytes + sender_bridge_bytes + port_id
    # send acket to trunk port
    send_to_link(trunk_port.port_id, len(bpdu_data), bpdu_data)

def send_bpdu_every_sec() -> None:
    global network_switch

    while True:
        # TODO Send BPDU every second if necessary
        
        if network_switch.is_root_bridge == True:
            for trunk_port in network_switch.all_trunk_ports:
                root_bridge_id: int = network_switch.own_bridge_id
                sender_bridge_id: int = network_switch.own_bridge_id
                sender_path_cost: int = 0
                
                send_bpdu_to_link(trunk_port, root_bridge_id, sender_bridge_id, sender_path_cost)
        


        time.sleep(1)



def on_receiving_bpdu(src_interface: int, data: bytes) -> None:
    global network_switch

    src_switch_port: SwitchPort = network_switch.get_switch_port_by_name(get_interface_name(src_interface))


    bpdu_root_bridge_id: int = int.from_bytes(data[22:30], byteorder='big')
    bpdu_sender_path_cost: int = int.from_bytes(data[30:34], byteorder='big')
    bpdu_sender_bridge_id: int = int.from_bytes(data[34:42], byteorder='big')

    if bpdu_root_bridge_id < network_switch.root_bridge_id:
        network_switch.root_bridge_id = bpdu_root_bridge_id
        network_switch.root_path_cost = bpdu_sender_path_cost + 10
        
        src_switch_port.port_state = PortState.ROOT_PORT # Root Port-Il este port-ul de unde BPDU-ul a fost primit
        # Un RootPort este mereu in starea Listening

        # if we were the root bridge
        if network_switch.is_root_bridge == True:
            # set all interfaces not to hosts to blocking except the root port 
            for trunk_port in network_switch.all_trunk_ports:
                if trunk_port.port_state != PortState.ROOT_PORT:
                    trunk_port.port_state = PortState.BLOCKING_PORT

        # Acum nu mai suntem root bridge
        network_switch.is_root_bridge = False


        # Update and forward this BPDU to all other trunk ports with:
        #  sender_bridge_ID = own_bridge_ID
        #  sender_path_cost = root_path_cost
        for trunk_port in network_switch.all_trunk_ports:
            if trunk_port.port_state == PortState.ROOT_PORT:
                continue
            root_bridge_id = network_switch.own_bridge_id
            sender_bridge_id = network_switch.own_bridge_id
            sender_path_cost = network_switch.root_path_cost
            send_bpdu_to_link(trunk_port, root_bridge_id, sender_bridge_id, sender_path_cost)

    elif bpdu_root_bridge_id == network_switch.root_bridge_id:
        """
        Primim pachete BPDU de la acelasi ROOT BRIDGE
        Ceea ce inseamna ca SWITCH-ul curent este NON-ROOT BRIDGE
        """
        network_switch.is_root_bridge = False

        if src_switch_port.port_state != PortState.ROOT_PORT and bpdu_sender_path_cost + 10 < network_switch.root_path_cost:
            network_switch.root_path_cost = bpdu_sender_path_cost + 10
        elif src_switch_port.port_state != PortState.ROOT_PORT:
            if bpdu_sender_path_cost > network_switch.root_path_cost:
                if src_switch_port.port_state != PortState.DESIGNATED_PORT:
                    # Orice port DESIGNATED este si LISTENING
                    src_switch_port.port_state = PortState.DESIGNATED_PORT

    elif bpdu_sender_bridge_id == network_switch.own_bridge_id:
        src_switch_port.port_state = PortState.BLOCKING_PORT
    else:
        pass

    if network_switch.own_bridge_id == network_switch.root_bridge_id:
        # Switch-ul devine ROOT BRIDGE
        network_switch.is_root_bridge = True

        for trunk_port in network_switch.all_trunk_ports:
            trunk_port.port_state = PortState.DESIGNATED_PORT


def initialize_STP():
    global network_switch

    for trunk_port in network_switch.all_trunk_ports:
        # Set port state to BLOCKING
        trunk_port.port_state = PortState.DESIGNATED_PORT


    network_switch.own_bridge_id = network_switch.switch_priority
    network_switch.root_bridge_id = network_switch.own_bridge_id
    network_switch.root_path_cost = 0



    # If this switch is the root bridge, set all ports to DESIGNATED_PORT
    if network_switch.own_bridge_id == network_switch.root_bridge_id:
        network_switch.is_root_bridge = True
        for trunk_port in network_switch.all_trunk_ports:
            trunk_port.port_state = PortState.DESIGNATED_PORT


network_switch: SwitchConfig = None
map_interface_names_with_ids: Dict[str, int] = {}


def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    # Casting to int
    switch_id: int = int(switch_id)


    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)


    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))



    
    global map_interface_names_with_ids
    for interface_id in interfaces:
        map_interface_names_with_ids[get_interface_name(interface_id)] = int(interface_id)
    

    # Initializarea tabelei CAM ()
    # Tabela CAM retine asocieri intre adrese MAC si numarul interfetelor (MAC -> interface_id)
    CAM_table_dict: Dict[bytes, int] = dict()     # Dictionar vid

    
    global network_switch
    network_switch = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")
    network_switch.compute_finding_all_trunk_ports()
    

    print(network_switch)
    print()

    for port in network_switch.interfaces:
        print()
        print(port)
        print()
    
    initialize_STP()


    # Create and start a new thread that deals with sending BPDU
    t = threading.Thread(target=send_bpdu_every_sec)
    t.start()



    while True:
        
        interface: int
        data: bytes
        length: int
        dest_mac: bytes
        src_mac: bytes
        vlan_id: int

        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)


        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]


        # TODO: Implement forwarding with learning

        # Updatez interfata pe care a venit pachetul cu adresa MAC sursa a pachetului
        CAM_table_dict[src_mac] = interface
        
        src_interface_id: int = interface
            


        # Trimiterea cadrului
        if is_unicast(dest_mac):
            # Unicast

            if dest_mac in CAM_table_dict:
                dst_interface_id: int = CAM_table_dict[dest_mac]

                if dst_interface_id == src_interface_id:
                    continue
                enable_VLAN_sending(vlan_id, src_interface_id, dst_interface_id, length, data)

            else:
                # Broadcast
                for dst_interface_id in interfaces:
                    if dst_interface_id == src_interface_id:
                        continue
                    enable_VLAN_sending(vlan_id, src_interface_id, dst_interface_id, length, data)
        else:
            if is_bpdu(dest_mac):
                on_receiving_bpdu(src_interface_id, data)
                continue
            
            # Broadcast
            for dst_interface_id in interfaces:
                if dst_interface_id == src_interface_id:
                    continue
                enable_VLAN_sending(vlan_id, src_interface_id, dst_interface_id, length, data)





        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
