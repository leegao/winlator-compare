# Example of what changes.txt looks like:
# 3c3
# < │   ├── [        837]  ./app/build.gradle
# ---
# > │   ├── [        835]  ./app/build.gradle
# 6c6
# < │           ├── [       2801]  ./app/src/main/AndroidManifest.xml
# ---
# > │           ├── [       2799]  ./app/src/main/AndroidManifest.xml
# ...

# This script will read the changes.txt file and print out the files that have changed

import os
import re
import sys
import zlib

staging_dir = os.path.dirname(os.path.realpath(__file__)) + "/workdir"
if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)

def jadx_apk(apk_file, output_dir):
    # Check if the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the jadx command from __file__ directory/jadx-1.5.1/bin/jadx
        os.system(f"{os.path.dirname(os.path.realpath(__file__))}/jadx-1.5.1/bin/jadx -d {output_dir} -e {apk_file}")


def tar_xf(tar_file, output_dir):
    # Check if the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Run the tar command
        os.system(f"tar -xf {tar_file} -C {output_dir}")


def get_checksum(file):
    # Get the crc32 checksum of the file and the file name without the extension
    with open(file, 'rb') as f:
        return str(zlib.crc32(f.read())) + "_" + os.path.splitext(os.path.basename(file))[0]


def get_staging_dir(file):
    checksum_name = get_checksum(file)
    return staging_dir + "/" + checksum_name


def get_changes(old_dir, new_dir):
    # Use tree -fs to get the list of files in the old and new directories
    old_files = os.popen(f"tree -fs {old_dir}").read().splitlines()
    new_files = os.popen(f"tree -fs {new_dir}").read().splitlines()
    
    old_files_dict = {}
    new_files_dict = {}
    for line in old_files:
        if not (line.startswith('│') or line.startswith('├') or line.startswith('└')):
            continue
        # Get the size and file name
        file = line.split(' ')[-1].strip()
        # Remove the first part of the file name (the directory)
        file = file.replace(old_dir + "/", "")
        # Get the size of the file using re.sub to find the pattern [   \d+]
        size = re.sub(r'.+\[ *(\d+)\].+', r'\1', line)
        old_files_dict[file] = size
    
    for line in new_files:
        if not (line.startswith('│') or line.startswith('├') or line.startswith('└')):
            continue
        # Get the size and file name
        file = line.split(' ')[-1].strip()
        file = file.replace(new_dir + "/", "")
        # Get the size of the file using re.sub to find the pattern [   \d+]
        size = re.sub(r'.+\[ *(\d+)\].+', r'\1', line)
        new_files_dict[file] = size
    
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

def print_changes(old_dir, new_dir):
    changes = get_changes(old_dir, new_dir)
    next_files = []
    for (file, change) in changes:
        # print(f"{file}: {change}")
        if change == 'changed':
            # Now exec the command to get the diff
            # Old will be bruno/{file} and new will be omod/{file}
            print(f"~ {file}: {change}, diffing...")
            os.system(f"diff -C 3 {old_dir}/{file} {new_dir}/{file}")
        elif change == 'added':
            print(f"+ {file}: {change} (added in {new_dir})")
            try:
                with open(f'{new_dir}/{file}', "r") as f:
                    for i, l in enumerate(f):
                        if i > 100:
                            print("    ", "...")
                            break
                        print("    ", l.rstrip())
            except:
                pass # Fond non-text data
        elif change == 'deleted':
            print(f"- {file}: {change} (deleted from {old_dir})")
        
        if (change == 'changed') and (file.endswith(".tzst") or file.endswith(".txz")):
            # Add the file to the next_files list
            next_files.append(file)
    return next_files


def compare_files(old_file, new_file):
    print(f"\nProcessing files: {old_file} and {new_file}")
    # Get the checksum of the old and new files
    old_dir = get_staging_dir(old_file)
    new_dir = get_staging_dir(new_file)
    print(f"Staging dirs: {old_dir} and {new_dir}")

    # Uncompress the files
    if old_file.endswith(".apk"):
        jadx_apk(old_file, old_dir)
    else:
        tar_xf(old_file, old_dir)
    if new_file.endswith(".apk"):
        jadx_apk(new_file, new_dir)
    else:
        tar_xf(new_file, new_dir)
    
    # Get the changes
    next_files = print_changes(old_dir, new_dir)
    for file in next_files:
        compare_files(old_dir + "/" + file, new_dir + "/" + file)



if __name__ == "__main__":
    old_apk = sys.argv[1]
    new_apk = sys.argv[2]

    compare_files(old_apk, new_apk)