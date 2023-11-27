with open("requirements.txt", "r") as file:
    packages = [line.strip() for line in file.readlines() if line.strip() and not line.startswith('#')]

for package in packages:
    try:
        package_name = package.split('==')[0]  # Adjust this if you use different specifiers in requirements.txt
        __import__(package_name)
        print(f"Successfully imported {package_name}")
    except ImportError:
        print(f"Failed to import {package_name}")
        raise
