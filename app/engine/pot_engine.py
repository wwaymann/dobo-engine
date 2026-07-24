from config import POT_DIAMETER, POT_HEIGHT, WALL_THICKNESS


def generate_pot():
    print("Generating DOBO Pot v0.1")
    print(f"Diameter: {POT_DIAMETER} mm")
    print(f"Height: {POT_HEIGHT} mm")
    print(f"Wall thickness: {WALL_THICKNESS} mm")


if __name__ == "__main__":
    generate_pot()