from extract import extract
from transform import transform
from load import load


if __name__ == "__main__":
    print("── Step 1: Extract")
    extract()

    print("\n── Step 2: Transform")
    transform()

    print("\n── Step 3: Load")
    load()

    print("\nPipeline complete ✓")
