import yaml
import json
import pynetbox


class NetBoxTools():

    def __init__(self, yaml_file):
        self.yaml_file = yaml_file

    def connect(self):
        with open(self.yaml_file, "r") as nb_connect:
            try:
                params = yaml.safe_load(nb_connect)

            except yaml.YAMLError as e:
                print(e)

        self.nb = pynetbox.api(params["url"], params["token"])

    def load_json(self, json_file):
        self.data = json.load(open(json_file))

    def import_data(self, model, endpoint):

        # Generate API call based off of model and endpoint
        api_call = "self.nb." + model + endpoint + ".create(**item)"

        for index, item in enumerate(self.data):

            try:
                output = eval(api_call)

                print(
                    "\n{}. {} '{}' WAS imported:".format(
                        index + 1, endpoint[:-1].title(), self.data[index]
                    )
                )

                print("    {} created".format(output))

            except pynetbox.lib.query.RequestError as e:

                print(
                    "\n{}. {} '{}' NOT imported:".format(
                        index + 1, endpoint[:-1].title(), self.data[index]
                    )
                )

                print("    {}".format(e.error))
