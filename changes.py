# Compare two APKs or directories and print the changes (assuming that they are related to Winlator.apk)

import os
import re
import sys
import zlib
from functools import cache


def write_path_token(original_path, output_dir):
    # Write the original path token to a file
    with open(f"{output_dir}/__path__.txt", "w") as f:
        f.write(original_path)


def jadx_apk(apk_file, output_dir):
    # Check if the output directory exists
    print(f"  $ jadx -d {output_dir} -e {apk_file}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the jadx command from __file__ directory/jadx-1.5.1/bin/jadx
        os.system(f"jadx -d {output_dir} -e {apk_file}")
        write_path_token(apk_file, output_dir)


def jd_jar(jar_file, output_dir):
    # Check if the output directory exists
    print(f"  $ jd-cli -od {output_dir} {jar_file}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the jadx command from __file__ directory/jadx-1.5.1/bin/jadx
        os.system(f"jd-cli -od {output_dir} {jar_file}")
        write_path_token(jar_file, output_dir)


def tar_xf(tar_file, output_dir):
    # Check if the output directory exists
    print(f"  $ tar -xf {tar_file} -C {output_dir}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the tar command
        os.system(f"tar -xf {tar_file} -C {output_dir}")
        write_path_token(tar_file, output_dir)


def unzip(zip_file, output_dir):
    # Check if the output directory exists
    print(f"  $ unzip -o {zip_file} -d {output_dir}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the unzip command
        os.system(f"unzip -o {zip_file} -d {output_dir}")
        write_path_token(zip_file, output_dir)
        # If there's only one directory in the output directory, move its contents to the output directory
        if len(os.listdir(output_dir)) == 1:
            target = os.path.join(output_dir, os.listdir(output_dir)[0])
            os.system(f"mv {target}/* {output_dir}/")


@cache
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
            if os.path.isdir(full_path):
                continue
            if ".git/" in full_path:
                continue
            files[os.path.join(root, filename).replace(dir + "/", "")] = os.path.getsize(full_path)
    return files


def get_changes(old_dir, new_dir):
    old_files_dict = get_all_files(old_dir) if old_dir else {}
    new_files_dict = get_all_files(new_dir) if new_dir else {}
    # Changes is a list of tuples (filename, type [changed (aka size differs), added, deleted])
    changes = []
    for file in old_files_dict:
        if file not in new_files_dict:
            changes.append((file, 'deleted'))
        elif old_files_dict[file] != new_files_dict[file]:
            changes.append((file, 'changed'))
    for file in new_files_dict:
        if file not in old_files_dict:
            changes.append((file, 'added'))
    
    return changes


@cache
def is_readable_file(file):
    # Check if the file is readable
    try:
        with open(file, 'r') as f:
            f.read()
            return True
    except:
        return False


def skip_file(file):
    # Check if the file is a known file to skip
    if file.endswith(".java") and "com/winlator" not in file:
        return True
    if file.endswith(".xml") and "src/main/res" in file:
        return True
    if "src/main" in file:
        if "/Shaders/" in file:
            return True
    if "META-INF" in file:
        return True
    if "locales" in file:
        return True
    if "fontconfig" in file:
        return True
    if "R.java" in file:
        return True
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
            if skip_file(file):
                continue
            if "usr/share" in file:
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
            if skip_file(file):
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
        
        if file.endswith(".tzst") or file.endswith(".txz") or file.endswith(".apk") or file.endswith(".zip"):
            # Add the file to the next_files list
            next_files.append(file)
    return next_files


def compare_files(old_file, new_file):
    # Get the checksum of the old and new files
    try:
        old_dir = get_staging_dir(old_file)
    except:
        # if old_file ends with rootfs.txz, then try rootfs.txz instead
        if old_file and old_file.endswith("rootfs.txz"):
            old_file = old_file.replace("rootfs.txz", "imagefs.txz")
            if os.path.exists(old_file):
                old_dir = get_staging_dir(old_file)
        # Same for rootfs_patches.tzst
        elif old_file and old_file.endswith("rootfs_patches.tzst"):
            old_file = old_file.replace("rootfs_patches.tzst", "imagefs_patches.tzst")
            if os.path.exists(old_file):
                old_dir = get_staging_dir(old_file)
        else:
            old_dir = None
    try:
        new_dir = get_staging_dir(new_file)
    except:
        new_dir = None
    print(f"# Processing files: {old_file if old_dir else "N/A"} vs {new_file if new_dir else "N/A"}")
    print(f"  Staging directories: {old_dir if old_dir else 'N/A'} vs {new_dir if new_dir else 'N/A'}")

    # Uncompress the files
    if old_file and os.path.isdir(old_file):
        # symlink the directory to the staging dir
        os.system(f"ln -s {old_file} {old_dir}")
    elif old_dir and old_file.endswith(".apk"):
        jadx_apk(old_file, old_dir)
    elif old_dir and old_file.endswith(".zip"):
        unzip(old_file, old_dir)
    elif old_dir and old_file.endswith(".jar"):
        jd_jar(old_file, old_dir)
    elif old_dir:
        tar_xf(old_file, old_dir)


    if new_file and os.path.isdir(new_file):
        # symlink the directory to the staging dir
        os.system(f"ln -s {new_file} {new_dir}")
    elif new_dir and new_file.endswith(".apk"):
        jadx_apk(new_file, new_dir)
    elif new_dir and new_file.endswith(".zip"):
        unzip(new_file, new_dir)
    elif new_dir and new_file.endswith(".jar"):
        jd_jar(new_file, new_dir)
    elif new_dir:
        tar_xf(new_file, new_dir)
    
    # Get the changes
    next_files = print_changes(old_dir, new_dir)
    for file in next_files:
        print(f"  Processing file: {file}")
        compare_files(old_dir + "/" + file if old_dir else None, new_dir + "/" + file if new_dir else None)


if __name__ == "__main__":
    old_apk = os.path.abspath(sys.argv[1])
    new_apk = os.path.abspath(sys.argv[2])

    staging_dir = os.path.dirname(os.path.realpath(__file__)) + "/compare_changes"
    if not os.path.exists(staging_dir):
        os.makedirs(staging_dir)
    os.chdir(staging_dir)

    compare_files(old_apk, new_apk)