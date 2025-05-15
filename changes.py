# Compare two APKs or directories and print the changes (assuming that they are related to Winlator.apk)

import os
import re
import sys
import zlib


def jadx_apk(apk_file, output_dir):
    # Check if the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the jadx command from __file__ directory/jadx-1.5.1/bin/jadx
        os.system(f"jadx -d {output_dir} -e {apk_file}")


def tar_xf(tar_file, output_dir):
    # Check if the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the tar command
        os.system(f"tar -xf {tar_file} -C {output_dir}")


def get_checksum(file):
    # Get the crc32 checksum of the file and the file name without the extension
    with open(file, 'rb') as f:
        return os.path.basename(file) + '_' + str(zlib.crc32(f.read()))


def get_staging_dir(file):
    if os.path.isdir(file):
        return os.path.basename(file) + "_D_" + str(zlib.crc32(file.encode()))
    checksum_name = get_checksum(file)
    return checksum_name


def get_all_files(dir):
    # Get all files and sizes in the directory and subdirectories
    files = {}
    for root, dirs, filenames in os.walk(dir):
        for filename in filenames:
            full_path = os.path.abspath(os.path.join(root, filename))
            if not os.path.isfile(full_path):
                continue
            if os.path.islink(full_path):
                continue
            files[os.path.join(root, filename).replace(dir + "/", "")] = os.path.getsize(full_path)
    return files


def get_changes(old_dir, new_dir):
    old_files_dict = get_all_files(old_dir) if old_dir else {}
    new_files_dict = get_all_files(new_dir)
    # Changes is a list of tuples (filename, type [changed (aka size differs), added, deleted])
    changes = []
    for file in old_files_dict:
        if os.path.isdir(new_dir + "/" + file):
                continue
        if file not in new_files_dict:
            changes.append((file, 'deleted'))
        elif old_files_dict[file] != new_files_dict[file]:
            changes.append((file, 'changed'))
    for file in new_files_dict:
        if os.path.isdir(new_dir + "/" + file):
                continue
        if file not in old_files_dict:
            changes.append((file, 'added'))
    
    return changes

def is_readable_file(file):
    # Check if the file is readable
    try:
        with open(file, 'r') as f:
            f.read()
            return True
    except:
        return False


def print_changes(old_dir, new_dir):
    changes = get_changes(old_dir, new_dir)
    if not changes:
        print("    No changes found")
        return []
    next_files = []
    for (file, change) in changes:
        if change == 'changed':
            # Now exec the command to get the diff
            # Old will be bruno/{file} and new will be omod/{file}
            print(f"  ~ {file}: {change}")
            if file.endswith(".java") and "com/winlator" not in file:
                continue
            if file.endswith(".xml") and "src/main/res" in file:
                continue
            if "src/main" in file:
                if "/Shaders/" in file:
                    continue
            if "META-INF" in file:
                continue
            if "locales" in file:
                continue
            if "fontconfig" in file:
                continue
            if "usr/share" in file:
                continue
            if "R.java" in file:
                continue
            if is_readable_file(f'{old_dir}/{file}') and is_readable_file(f'{new_dir}/{file}'):
                if file.endswith(".java") or file.endswith(".cpp") or file.endswith(".c") or file.endswith(".h") or file.endswith(".xml"):
                    popen = os.popen(f"diff -u '{old_dir}/{file}' '{new_dir}/{file}'")
                    for line in popen.readlines():
                        print("    " + line.rstrip())
                else:
                    popen = os.popen(f"diff -u '{old_dir}/{file}' '{new_dir}/{file}'")
                    for line in popen.readlines():
                        print("    " + line.rstrip())
        elif change == 'added':
            print(f"  + {file}: {change} (added)")
            if file.endswith(".java") and "com/winlator" not in file:
                continue
            if file.endswith(".xml") and "src/main/res" in file:
                continue
            if "src/main" in file:
                if "/Shaders/" in file:
                    continue
            if "META-INF" in file:
                continue
            if "locales" in file:
                continue
            if "fontconfig" in file:
                continue
            if "R.java" in file:
                continue
            try:
                limit = 5
                if file.endswith(".java"):
                    limit = 100
                with open(f'{new_dir}/{file}', "r") as f:
                    for i, l in enumerate(f):
                        if i > limit:
                            print("    ", "...")
                            break
                        print("    " + l.rstrip())
            except:
                pass # Fond non-text data
        elif change == 'deleted':
            print(f"  - {file}: {change} (deleted)")
        
        if (change == 'changed' or change == 'added') and (file.endswith(".tzst") or file.endswith(".txz")):
            # Add the file to the next_files list
            next_files.append(file)
    return next_files


def compare_files(old_file, new_file):
    # Get the checksum of the old and new files
    try:
        old_dir = get_staging_dir(old_file)
    except:
        # if old_file ends with rootfs.txz, then try rootfs.txz instead
        if old_file.endswith("rootfs.txz"):
            old_file = old_file.replace("rootfs.txz", "imagefs.txz")
            if os.path.exists(old_file):
                old_dir = get_staging_dir(old_file)
        # Same for rootfs_patches.tzst
        elif old_file.endswith("rootfs_patches.tzst"):
            old_file = old_file.replace("rootfs_patches.tzst", "imagefs_patches.tzst")
            if os.path.exists(old_file):
                old_dir = get_staging_dir(old_file)
        else:
            old_dir = None
    new_dir = get_staging_dir(new_file)
    print(f"# Processing files: {old_file if old_dir else "N/A"} vs {new_file}")
    print(f"  Staging directories: {old_dir if old_dir else 'N/A'} vs {new_dir}")

    # Uncompress the files
    if old_dir and old_file.endswith(".apk"):
        jadx_apk(old_file, old_dir)
    elif os.path.isdir(old_file):
        # symlink the directory to the staging dir
        os.system(f"ln -s {old_file} {old_dir}")
    elif old_dir:
        tar_xf(old_file, old_dir)

    if new_dir and new_file.endswith(".apk"):
        jadx_apk(new_file, new_dir)
    elif os.path.isdir(new_file):
        # symlink the directory to the staging dir
        os.system(f"ln -s {new_file} {new_dir}")
    elif new_dir:
        tar_xf(new_file, new_dir)
    
    # Get the changes
    next_files = print_changes(old_dir, new_dir)
    for file in next_files:
        print(f"  Processing file: {file}")
        compare_files(old_dir + "/" + file, new_dir + "/" + file)


if __name__ == "__main__":
    old_apk = os.path.abspath(sys.argv[1])
    new_apk = os.path.abspath(sys.argv[2])

    staging_dir = os.path.dirname(os.path.realpath(__file__)) + "/workdir"
    if not os.path.exists(staging_dir):
        os.makedirs(staging_dir)
    os.chdir(staging_dir)

    compare_files(old_apk, new_apk)