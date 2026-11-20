from pathlib import Path

folder_path = Path("./data/policy_handbook")
extension = "*.md"  # Change to your target file type, e.g., '*.csv', '*.png'

def print_folders_names():
    for file_path in folder_path.glob(extension):
        if file_path.is_file():
            print(f"File Name: {file_path.name}")
        
def print_file_content(file_name: str ):
    for item in folder_path.iterdir():
        if item.name + ".md" == file_name:
            print(item.read_text())






entered_name = input("Enter File name: ")
print_file_content(entered_name)
