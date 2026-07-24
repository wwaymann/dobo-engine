import json
import os


def load_config():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config",
        "pot_config.json"
    )

    with open(config_path, "r") as file:
        return json.load(file)


def generate_pot():
    config = load_config()

    diameter = config["diameter"]
    height = config["height"]
    wall = config["wall_thickness"]
    bottom = config["bottom_thickness"]

    print("DOBO Hollow Pot generated!")
    print(f"Diameter: {diameter} mm")
    print(f"Height: {height} mm")
    print(f"Wall thickness: {wall} mm")
    print(f"Bottom thickness: {bottom} mm")


if __name__ == "__main__":
    generate_pot()