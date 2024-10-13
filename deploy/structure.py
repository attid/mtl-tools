import os
import shutil


# 27/07/24

def generate_tree(startpath, exclude_dirs=None, exclude_files=None):
    if exclude_dirs is None:
        exclude_dirs = set()
    if exclude_files is None:
        exclude_files = set()

    tree = []
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * level
        tree.append(f'{indent}├── {os.path.basename(root)}/')
        subindent = '│   ' * (level + 1)
        for f in sorted(files):
            if f not in exclude_files and not f.startswith('.'):
                tree.append(f'{subindent}├── {f}')
    return '\n'.join(tree)


def update_structure_file(project_root, output_file):
    exclude_dirs = {'venv', '__pycache__', 'node_modules', 'files'}
    exclude_files = {'structure.txt'}

    tree = generate_tree(project_root, exclude_dirs, exclude_files)

    with open(output_file, 'w') as f:
        f.write(tree)


def clear_and_copy_py_files(src_directory, dest_directory, exclude_dirs=None, exclude_files=None):
    if exclude_dirs is None:
        exclude_dirs = set()
    if exclude_files is None:
        exclude_files = set()

    if not os.path.exists(dest_directory):
        os.makedirs(dest_directory)

    # Очистить директорию назначения
    for root, dirs, files in os.walk(dest_directory):
        for file in files:
            os.remove(os.path.join(root, file))

    # Копировать файлы .py, исключая определенные директории и файлы
    for root, dirs, files in os.walk(src_directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        if os.path.abspath(root) == os.path.abspath(dest_directory):
            continue
        for file in files:
            if file.endswith('.py') and file not in exclude_files and not file.startswith('.'):
                shutil.copy(os.path.join(root, file), dest_directory)


if __name__ == '__main__':
    project_root = '..'  # Текущая директория
    output_file = '../.files/structure.txt'
    files_directory = '../.files'
    exclude_dirs = {'venv', '__pycache__', 'node_modules', 'files'}
    exclude_files = {'structure.txt'}

    # Очистить и скопировать файлы .py в директорию files
    clear_and_copy_py_files(project_root, files_directory, exclude_dirs, exclude_files)
    print(f"Все файлы .py скопированы в директорию {files_directory}")

    # Обновить структуру проекта
    update_structure_file(project_root, output_file)
    print(f"Структура проекта обновлена в файле {output_file}")
