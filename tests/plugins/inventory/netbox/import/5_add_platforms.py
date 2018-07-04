#!/usr/bin/env python3

import json, pynetbox
from nb_connect import *

definitions = ["platform", "name"]
data_file = "json/platforms.json"


def load_json(file):
    return json.load(open(file))


def add_data(data):
    try:
        output = nb.dcim.platforms.create(**data)
        return output
    except pynetbox.lib.query.RequestError as e:
        return e.error


if __name__ == "__main__":
    data = load_json(data_file)

    for index, item in enumerate(data):
        output = add_data(data[index])

        if type(output) is dict:
            print(
                "\n{}. {} '{}' WAS imported:".format(
                    index + 1, definitions[0].title(), data[index][definitions[1]]
                )
            )
            print("    {} created".format(output))
        else:
            print(
                "\n{}. {} '{}' NOT imported:".format(
                    index + 1, definitions[0].title(), data[index][definitions[1]]
                )
            )
            print("    {}".format(output))
