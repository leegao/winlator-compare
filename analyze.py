# Compare two APKs or directories and print the changes (assuming that they are related to Winlator.apk)

import os
import re
import sys
import zlib
import argparse
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


def get_files(old_dir):
    old_files_dict = get_all_files(old_dir) if old_dir else {}
    # Changes is a list of tuples (filename, type [changed (aka size differs), added, deleted])
    files = []
    for file in old_files_dict:
        files.append(file)
    return sorted(files)


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
    if file.endswith(".java") and ("androidx/" in file or "com/google/" in file or "com/android/" in file or "org/apache/" in file or "org/tukaani/" in file):
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


def is_src_file(file):
    return file.endswith(".java") or file.endswith(".c") or file.endswith(".cpp") or file.endswith(".h") or file.endswith(".hpp")


def print_files(old_dir, args):
    files = get_files(old_dir)
    if not files:
        print("    No files found")
        return []
    next_files = []
    for file in files:
        print(f"  + {file}")

        if file.endswith(".tzst") or file.endswith(".txz") or file.endswith(".apk") or file.endswith(".zip") or file.endswith(".jar"):
            # Add the file to the next_files list
            next_files.append(file)
        if skip_file(file):
            continue
        
        if not is_readable_file(f'{old_dir}/{file}'):
            if args.nm and (file.endswith(".so") or file.endswith(".a") or file.endswith(".o")):
                # Use nm to get the symbols
                popen = os.popen(f"nm -gDCU {old_dir}/{file}")
                for line in popen.readlines():
                    print("    " + line.rstrip())
            if args.objdump and (file.endswith(".so") or file.endswith(".a") or file.endswith(".o")):
                # Use objdump to get the symbols
                popen = os.popen(f"objdump -x {old_dir}/{file}")
                for line in popen.readlines():
                    print("    " + line.rstrip())
            if args.disassemble and (file.endswith(".so") or file.endswith(".a") or file.endswith(".o")):
                # Check to see if objdump is installed
                has_objdump = os.system("which objdump > /dev/null") == 0
                has_aarch64_objdump = os.system("which aarch64-linux-gnu-objdump > /dev/null") == 0 or os.system("which aarch64-w64-mingw32-objdump > /dev/null") == 0
                # Check if the file is a x86_64 or aarch64 file
                is_x86_64 = os.system(f"file {old_dir}/{file} | grep -q 'x86-64' > /dev/null") == 0
                # Use objdump to get the symbols
                if has_objdump and is_x86_64:
                    popen = os.popen(f"objdump -D -j .text {old_dir}/{file}")
                elif has_aarch64_objdump:
                    popen = os.popen(f"aarch64-linux-gnu-objdump -D -j .text {old_dir}/{file}")
                
                for line in popen.readlines():
                    print("    " + line.rstrip())
            continue

        try:
            file_limit = args.limit
            if is_src_file(file):
                file_limit = 5000 # Keep a higher limit for source files by default
            with open(f'{old_dir}/{file}', "r") as f:
                for i, l in enumerate(f):
                    if i > file_limit:
                        print("    ", "... (truncated) ...")
                        break
                    print("    " + l.rstrip())
        except:
            pass # Found non-text data
        
    return next_files


def analyze_files(old_file, args):
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
    
    print(f"# Processing files: {old_file if old_dir else "N/A"}")
    print(f"  Staging directories: {old_dir if old_dir else 'N/A'}")

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

    # Get the changes
    next_files = print_files(old_dir, args)
    for file in next_files:
        print(f"  Processing file: {file}")
        analyze_files(old_dir + "/" + file if old_dir else None, args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze APKs or directories.')
    parser.add_argument('apk_file', help='The APK file or directory to analyze.')
    parser.add_argument('--nm', action='store_true', help='Enable nm for .so files.')
    parser.add_argument('--objdump', action='store_true', help='Enable objdump -x for .so files.')
    parser.add_argument('--disassemble', action='store_true', help='Enable disassembly for .so files.')
    parser.add_argument('-l', '--limit', type=int, default=20, help='Limit the number of lines printed per file.')
    parser.add_argument('-w', '--working-dir', type=str, default=None, help='Disable verbose output.')
    args = parser.parse_args()

    apk_file = os.path.abspath(args.apk_file)

    if args.working_dir:
        working_dir = os.path.abspath(args.working_dir)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
    else:
        working_dir = os.path.dirname(os.path.realpath(__file__)) + "/analyze_winlator"
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

    os.chdir(working_dir)

    analyze_files(apk_file, args)
