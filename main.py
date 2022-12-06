import re
import yaml
import pyzabbix

def check_device_type(name) -> str:
    switcher = {
        'TOR': 'leaf',
        'SPN': 'spine',
        'BLF': 'border-leaf',
        'ESR': 'ARCTURUS',
        'OER': 'ORION',
        'MBR': 'BBNG',
        'BTR': 'SIRIUS',
        'BSR': 'SIRIUS',
        'F': 'firewall'
    }

    match = re.search("(^(?P<prefix>\D+)\d+\-.*$|^(?P<firewall>F)\d\D{3}\w+-.*$)", name)

    if match:
        if match["firewall"]:
            return switcher.get(match["firewall"])
        return switcher.get(match["prefix"])
    else:
        return "NA"

class zabbixConnector:
    def __init__(self, server: str = "http://127.0.0.1:8080", user: str = "Admin", password: str = "zabbix"):
        self.server = server
        self._user = user
        self._password = password
        self.zapi = pyzabbix.ZabbixAPI(self.server)
        self.zapi.login(user=self._user, password=self._password)
        print("Successfully logged in")

    def logout(self) -> None:
        self.zapi.do_request("user.logout")
        print(f"Successfully logged out from server {self.server}")

    def login(self) -> None:
        self.zapi.login(user=self._user, password=self._password)
        print(f"Successfully logged in on server {self.server}")

    def request(self, method: str = "", params: dict = {}) -> dict:
        if method:
            response = self.zapi.do_request(method, params)
            return response
        else:
            print("No method provided")

class Device:
    def __init__(self, host: str = "", connector: zabbixConnector = None, server: str = "http://127.0.0.1:8080",
                 user: str = "Admin", password: str = "zabbix"):
        self.links = {}
        if not connector:
            self.connector = zabbixConnector(server, user, password)
        else:
            self.connector = connector
        payload = {"filter": {"host": host}}
        response = self.connector.request("host.get", payload)

        if response.get("result"):
            self.host = response["result"][0].get("host")
            self.hostid = response["result"][0].get("hostid")
            self.type = check_device_type(self.host)
            self.role = "main"

            self.check_role()

            # for key in response["result"][0]:
            #    setattr(self, key, response["result"][0].get(key))

            self.get_image_id()
            # self.get_cpu_graph_id()
            print(f"Device '{host}' retrieved with hostId {self.hostid}")
        else:
            print(f"Device '{host}' not found")

    def add_link(self, peer_device: str = "", link: dict = {}) -> None:
        if not self.links.get(peer_device):
            self.links[peer_device] = link

    def check_role(self):
        if hasattr(self, "y"):
            if self.type == "spine" and int(self.y) > int("600"):
                self.role = "satellite"
            if self.type == "leaf" and int(self.y) > int("900"):
                self.role = "satellite"

    def set_role(self, role: str = "main") -> None:
        self.role = role
        print("done")

    def get_image_id(self) -> None:
        if self.type in ["leaf", "spine", "border-leaf"]:
            self.image_name = "9k_bleu"
        elif self.type in ["ARCTURUS", "SIRIUS", "ORION", "BBNG"]:
            self.image_name = "Router_Symbol_(128)"
        elif self.type in ["firewall"]:
            self.image_name = "Firewall_(128)"

        payload = {
            "search": {
                "name": self.image_name
            }
        }

        response = self.connector.request("image.get", payload)
        if response.get('result'):
            self.image_id = response['result'][0].get("imageid")

    def get_cpu_graph_id(self) -> None:
        payload = {
            "search": {
                "name": "CPU"
            },
            "output":
                ["graphid"],
            "hostids": self.hostid
        }

        response = self.connector.request("graph.get", payload)
        if response.get('result'):
            self.cpu_graph_id = response["result"][0].get("graphid")
            self.cpu_url = f"https://bt1svmxe/zabbix/zabbix.php?view_as=showgraph&action=charts.view&from=now-15m&to=now&filter_hostids%5B%5D={self.hostid}&filter_search_type=0&filter_graphids%5B%5D={self.cpu_graph_id}&filter_set=1"

    def get_hostid(self) -> int:
        return self.hostid

    def get_host(self) -> str:
        return self.host

    def get_type(self) -> str:
        return self.type

    def set_type(self, devicetype: str = "") -> None:
        self.type = devicetype

    def set_selementid(self, selementid: int = 0) -> None:
        self.selementid = selementid

    def set_x_y(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y

class zabbixMap:
    def __init__(self, name: str = "", connector: zabbixConnector = None, server: str = "http://127.0.0.1:8080",
                 user: str = "Admin", password: str = "zabbix"):
        self.name = name
        self.img_width = 128
        self.devices = {}
        if not connector:
            self.connector = zabbixConnector(server, user, password)
        else:
            self.connector = connector

    def retrieve_map(self) -> None:
        payload_checkmap = {
            "search": {
                "name": self.name
            },
            "output": "extend",
            "selectSelements": "extend",
            "selectLinks": "extend",
            "selectUsers": "extend",
            "selectUserGroups": "extend",
            "selectShapes": "extend",
            "selectLines": "extend"
        }
        payload_createmap = {
            "name": self.name,
            "width": 1600,
            "height": 1200
        }

        response = self.connector.request("map.get", payload_checkmap)

        if response.get("result"):
            self.retrieved_map = response["result"][0]
            self.context = "fabric"
            self.analyze_map()
        else:
            self.retrieved_map = {}
            self.width = 1600
            self.height = 1200
            print(f"No map {self.name} found")

            #response = self.connector.request("map.create", payload_createmap)
            #if response.get("result"):
            #    print("Map successfully created")
           #     response = self.connector.request("map.get", payload_checkmap)
            #    if response.get("result"):
            #        self.retrieved_map = response["result"][0]

    def analyze_map(self) -> None:
        if self.retrieved_map:
            print("Retrieving data from map")
            if self.retrieved_map.get("selements"):
                self.selementsid_devices_mapping = {}
                for selement in self.retrieved_map.get("selements"):
                    # retrieve devicename by hostid
                    payload = {
                        "filter": {
                            "hostid": selement['elements'][0].get('hostid')
                        }
                    }
                    response = self.connector.request("host.get", payload)
                    if response.get("result"):
                        # If device doesn't already exist in device list, add it
                        devicename = response['result'][0].get('host')

                        self.selementsid_devices_mapping[selement.get("selementid")] = devicename
                        if not self.check_device_in_devices_list(devicename, self.devices):
                            self.add_device(devicename)

                    devicetype = check_device_type(devicename)
                    self.devices[devicetype][devicename].set_selementid(selement.get("selementid"))
                    self.devices[devicetype][devicename].set_x_y(selement.get("x"), selement.get("y"))
                    self.devices[devicetype][devicename].check_role()

            if self.retrieved_map.get("links"):
                for link in self.retrieved_map.get("links"):
                    source_device = self.selementsid_devices_mapping.get(link.get("selementid1"))
                    dest_device = self.selementsid_devices_mapping.get(link.get("selementid2"))
                    for group in self.devices:
                        for device in self.devices[group]:
                            if device == source_device:
                                self.devices[group][device].add_link(dest_device, link)
                            if device == dest_device:
                                self.devices[group][device].add_link(source_device, link)
        else:
            print("No map to analyze")

    def analyse_yaml(self, file: str = "") -> None:
        with open(file, 'r') as yaml_file:
            yaml_content = yaml.safe_load(yaml_file)
        self.context = yaml_content["map"].get("context")
        if yaml_content.get("devices"):
            for device in yaml_content["devices"]:
                self.add_device(device.get("name"))
                device_type = check_device_type(device.get("name"))
                if device.get("role"):
                    self.devices[device_type][device.get("name")].set_role(device.get("role"))

                if device.get("links"):
                    for link in device["links"]:
                        self.devices[device_type][device.get("name")].add_link(link)

    def check_device_in_devices_list(self, devicename: str = "", devices: dict = {}) -> bool:
        for group in devices:
            if devicename in devices[group]:
                return True
        return False

    def add_device(self, devicename: str = "") -> None:
        devicetype = check_device_type(devicename)
        if not self.devices.get(devicetype):
            self.devices[devicetype] = {}

        if not self.devices[devicetype].get(devicename):
            self.devices[devicetype][devicename] = Device(devicename, self.connector)
            self.devices[devicetype][devicename].set_type(devicetype)
            print(f"Device {self.devices[devicetype][devicename].get_host()} added")

    def generate_links(self) -> None:
        self.links = []
        # Generate links for fabric context
        if self.context == "fabric":
            backbone_devices = {}

            # add all backbone device into the same dict
            for group in self.devices:
                if group in ["ORION", "BBNG", "SIRIUS", "ARCTURUS"]:
                    for device_name, device_obj in self.devices.get(group).items():
                        backbone_devices[device_name] = device_obj

            # build link from all backbone device (Should be BLF device)
            for device_name, device_obj in backbone_devices.items():
                if device_obj.links:
                    for peer, peer_attribute in device_obj.links.items():
                        if check_device_type(peer) in ["border-leaf"]:
                            link = {
                                "source_elementid": peer_attribute.get("selementid1"),
                                "dest_elementid": peer_attribute.get("selementid2"),
                                "label_host": peer
                            }
                            self.links.append(link)

            # build link from all Border_leaf device (Should be FW or Spine device )
            for borderleaf_device_name, borderleaf_device_attribute in self.devices.get("border-leaf").items():
                if borderleaf_device_attribute.links:
                    for peer, peer_attribute in borderleaf_device_attribute.links.items():
                        if check_device_type(peer) in ["spine", "firewall", "border-leaf"]:
                            link = {
                                "source_elementid": peer_attribute.get("selementid1"),
                                "dest_elementid": peer_attribute.get("selementid2"),
                                "label_host": peer
                            }
                            self.links.append(link)

            # build link from all spine device (Should be leaf or spine device )
            for spine_device_name, spine_device_attribute in self.devices.get("spine").items():
                if spine_device_attribute.links:
                    for peer, peer_attribute in spine_device_attribute.links.items():
                        if check_device_type(peer) in ["spine", "leaf"]:
                            link = {
                                "source_elementid": peer_attribute.get("selementid1"),
                                "dest_elementid": peer_attribute.get("selementid2"),
                                "label_host": peer
                            }
                            self.links.append(link)

    def generate_map_json(self) -> None:
        self.payload = {"selements": [], "links": []}
        if self.retrieved_map:
            self.payload["sysmapid"] = self.retrieved_map.get("sysmapid")
            if self.devices:
                for group_name, group_attribute in self.devices.items():
                    for device_name, device_obj in group_attribute.items():
                        self.payload["selements"].append({
                            "selementid": device_obj.selementid,
                            "x": device_obj.x,
                            "y": device_obj.y,
                            "elements": [
                                {"hostid": device_obj.hostid}
                            ],
                            "label": "{HOSTNAME} ({HOST.IP})\nCPU: {{HOST.HOST}:CPU.last(0)}",
                            "elementtype": 0,
                            "iconid_off": device_obj.image_id
                        })

        if self.links:
            for link in self.links:
                self.payload["links"].append({
                    "label": "In:{" + link.get(
                        "label_host") + ":ifHCInOctets[port-channel100].last()}\nOut:{" + link.get(
                        "label_host") + ":ifHCOutOctets[port-channel100].last()}\n[MAX-BW: {" + link.get(
                        "label_host") + ":ifHighSpeed[369098851].last()}]",
                    "color": "00CC00",
                    "selementid1": link.get("source_elementid"),
                    "selementid2": link.get("dest_elementid")
                })

    def update_map(self) -> None:
        response = self.connector.request("map.update", self.payload)
        if response.get("result"):
            print(f"Map {self.name} updated")

    def position_devices(self) -> None:
        # sort devices that will be in the same level in the dame dict
        mapping = {}
        if self.context == "fabric":
            # order device into layer dependending on there function
            for group in self.devices:
                if group in ["ORION", "BBNG", "SIRIUS", "ARCTURUS"]:
                    if not mapping.get("l1"):
                        mapping["l1"] = {}
                    for devicename, device_obj in self.devices.get(group).items():
                        mapping["l1"][devicename] = device_obj
                if group in ["border-leaf"]:
                    if not mapping.get("l2"):
                        mapping["l2"] = {}
                    for devicename, device_obj in self.devices.get(group).items():
                        # retrieve firewall
                        for peer in device_obj.links:
                            if check_device_type(peer) == "firewall" and not mapping.get("l2"):
                                mapping["l2"][peer] = self.devices["firewall"][peer]
                                mapping["l2"][devicename] = device_obj
                            elif check_device_type(peer) == "firewall" and mapping.get("l2"):
                                mapping["l2"][devicename] = device_obj
                                mapping["l2"][peer] = self.devices["firewall"][peer]

                if group in ["spine", "leaf"]:
                    for devicename, device_obj in self.devices.get(group).items():
                        if group == "spine" and device_obj.role == "main":
                            if not mapping.get("l3"):
                                mapping["l3"] = {}
                            mapping["l3"][devicename] = device_obj
                        elif (group == "spine" and device_obj.role == "satellite") or (
                                group == "leaf" and device_obj.role == "main"):
                            if not mapping.get("l4"):
                                mapping["l4"] = {}
                            mapping["l4"][devicename] = device_obj
                        elif group == "leaf" and device_obj.role == "satellite":
                            if not mapping.get("l5"):
                                mapping["l5"] = {}
                            mapping["l5"][devicename] = device_obj

            # init layer 1 to Y= 50
            devices_y_pos = 50
            for layer in mapping:
                devices_x_pos = self.calculate_x_pos(mapping.get(layer))
                for i, device_obj in enumerate(mapping[layer].values()):
                    device_obj.set_x_y(devices_x_pos[i], devices_y_pos)
                devices_y_pos += 250


    def calculate_x_pos(self, devices_to_map) -> list:
        result = []
        spacing = int((int(self.width) - (self.img_width * len(devices_to_map))) / (len(devices_to_map) + 1))
        pos = spacing

        for i in range(0, len(devices_to_map)):
            result.append(pos)
            pos = pos + self.img_width + spacing

        return result

def main():
    # print("Retrieve and update existing map")
    # Map = zabbixMap("FABRIC")
    # Map.retrieve_map()
    # Map.position_devices()
    # Map.generate_links()
    # Map.generate_map_json()
    # Map.update_map()
    # Map.connector.logout()

    print("Retrieve a new map from scratch (YAML File)")
    Map = zabbixMap("titato")
    Map.retrieve_map()
    Map.analyse_yaml("map.yaml")
    Map.position_devices()
    Map.generate_map_json()
    Map.update_map()



    # Map.update_map()

    # map2 = zabbixMap("mop")
    # map2.retrieve_map()
    # for device in deviceList:
    #    map2.add_device(device)
    # map2.update_map()
    print("end")
    print("end2")

    Map.connector.logout()


if __name__ == "__main__":
    main()
