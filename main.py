# main.py
from src import startup
import Spot

def main():
    # Call the startup function from startup.py
    startup.startup()

    # Call functions from Spot.py
    Spot.some_function()

if __name__ == "__main__":
    main()