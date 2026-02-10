import ast
import os

def map_python_file(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        node = ast.parse(f.read())

    print(f"=== Structure Map for {filename} ===\n")
    
    for item in node.body:
        # Check for Classes (like QwenTTSApp)
        if isinstance(item, ast.ClassDef):
            print(f"Class: {item.name} (Line {item.lineno})")
            for sub_item in item.body:
                if isinstance(sub_item, ast.FunctionDef):
                    # Check if it's a normal method or a nested one
                    print(f"  ├── Method: {sub_item.name} (Line {sub_item.lineno})")
                elif isinstance(sub_item, ast.AsyncFunctionDef):
                    print(f"  ├── Async Method: {sub_item.name} (Line {sub_item.lineno})")
        
        # Check for standalone Functions
        elif isinstance(item, ast.FunctionDef):
            print(f"Function: {item.name} (Line {item.lineno})")

if __name__ == "__main__":
    # Change this if your main file has a different name
    target_file = "app_main.py"
    map_python_file(target_file)