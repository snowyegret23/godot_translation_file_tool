import struct
import os
import os.path
import sys
from enum import IntEnum
from dataclasses import dataclass
from io import BufferedReader, BufferedWriter
import csv
from dotenv import load_dotenv
import smaz
import argparse
import subprocess
import shutil

def chunks(lst: list, n: int) -> list[list]:
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

@dataclass
class Writer:
    file: BufferedWriter
    big_endian = False
    real_is_double = False

    def write(self, x: bytes):
        return self.file.write(x)

    def store_i32(self, x: int):
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}i", x))

    def store_i64(self, x: int):
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}q", x))

    def store_u64(self, x: int):
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}Q", x))

    def store_u8(self, x: bytes):
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}B", x[0]))

    def store_u32(self, x: int) -> int:
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}I", x))

    def store_f32(self, x: float) -> float:
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}f", x))

    def store_f64(self, x: float) -> float:
        endian = ">" if self.big_endian else "<"
        self.file.write(struct.pack(f"{endian}d", x))

    def store_unicode(self, x: str):
        encoded = x.encode() + b"\0"
        self.store_u32(len(encoded))
        self.file.write(encoded)

@dataclass
class Reader:
    file: BufferedReader
    big_endian = False
    real_is_double = False

    def read(self, length: int) -> bytes:
        return self.file.read(length)

    def skip(self, length: int):
        self.file.read(length)

    def seek(self, offset: int):
        self.file.seek(offset)

    def get_i32(self) -> int:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}i", self.file.read(4))[0]

    def get_i64(self) -> int:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}l", self.file.read(8))[0]

    def get_u64(self) -> int:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}L", self.file.read(8))[0]

    def get_u8(self) -> bytes:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}B", self.file.read(1))[0].to_bytes(1, "little")

    def get_u32(self) -> int:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}I", self.file.read(4))[0]

    def get_f32(self) -> float:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}f", self.file.read(4))[0]

    def get_f64(self) -> float:
        endian = ">" if self.big_endian else "<"
        return struct.unpack_from(f"{endian}d", self.file.read(8))[0]

    def get_unicode(self) -> str:
        length = self.get_u32()
        return self.file.read(length)[:-1].decode()

class Flag(IntEnum):
    FORMAT_FLAG_NAMED_SCENE_IDS = 1
    FORMAT_FLAG_UIDS = 2
    FORMAT_FLAG_REAL_T_IS_DOUBLE = 4
    FORMAT_FLAG_HAS_SCRIPT_CLASS = 8
    RESERVED_FIELDS = 11

class PropType(IntEnum):
    VARIANT_NIL = 1
    VARIANT_BOOL = 2
    VARIANT_INT = 3
    VARIANT_FLOAT = 4
    VARIANT_STRING = 5
    VARIANT_VECTOR2 = 10
    VARIANT_RECT2 = 11
    VARIANT_VECTOR3 = 12
    VARIANT_PLANE = 13
    VARIANT_QUATERNION = 14
    VARIANT_AABB = 15
    VARIANT_BASIS = 16
    VARIANT_TRANSFORM3D = 17
    VARIANT_TRANSFORM2D = 18
    VARIANT_COLOR = 20
    VARIANT_NODE_PATH = 22
    VARIANT_RID = 23
    VARIANT_OBJECT = 24
    VARIANT_INPUT_EVENT = 25
    VARIANT_DICTIONARY = 26
    VARIANT_ARRAY = 30
    VARIANT_PACKED_BYTE_ARRAY = 31
    VARIANT_PACKED_INT32_ARRAY = 32
    VARIANT_PACKED_FLOAT32_ARRAY = 33
    VARIANT_PACKED_STRING_ARRAY = 34
    VARIANT_PACKED_VECTOR3_ARRAY = 35
    VARIANT_PACKED_COLOR_ARRAY = 36
    VARIANT_PACKED_VECTOR2_ARRAY = 37
    VARIANT_INT64 = 40
    VARIANT_DOUBLE = 41
    VARIANT_CALLABLE = 42
    VARIANT_SIGNAL = 43
    VARIANT_STRING_NAME = 44
    VARIANT_VECTOR2I = 45
    VARIANT_RECT2I = 46
    VARIANT_VECTOR3I = 47
    VARIANT_PACKED_INT64_ARRAY = 48
    VARIANT_PACKED_FLOAT64_ARRAY = 49
    VARIANT_VECTOR4 = 50
    VARIANT_VECTOR4I = 51
    VARIANT_PROJECTION = 52
    OBJECT_EMPTY = 0
    OBJECT_EXTERNAL_RESOURCE = 1
    OBJECT_INTERNAL_RESOURCE = 2
    OBJECT_EXTERNAL_RESOURCE_INDEX = 3
    FORMAT_VERSION = 5
    FORMAT_VERSION_CAN_RENAME_DEPS = 1
    FORMAT_VERSION_NO_NODEPATH_PROPERTY = 3

@dataclass
class Resource:
    version_major: int
    version_minor: int
    format_version: int
    importmd_ofs: int
    class_name: str
    flags: int
    string_map: list[str]
    properties: dict[str, any]

def parse_resource(path: str) -> Resource:
    with open(path, "rb") as f:
        r = Reader(f)
        assert b"RSRC" == r.read(4)
        big_endian = r.get_i32() == 1
        use_real64 = r.get_i32() == 1
        r.big_endian = big_endian
        version_major = r.get_i32()
        version_minor = r.get_i32()
        format_version = r.get_i32()
        class_name = r.get_unicode()
        importmd_ofs = r.get_i64()
        flags = r.get_u32()

        using_named_scene_ids = bool(flags & Flag.FORMAT_FLAG_NAMED_SCENE_IDS)
        using_uids = bool(flags & Flag.FORMAT_FLAG_UIDS)
        r.real_is_double = bool(flags & Flag.FORMAT_FLAG_REAL_T_IS_DOUBLE)

        if using_uids:
            uid = r.get_u64()
        else:
            r.skip(8)

        script_class = None
        if flags & Flag.FORMAT_FLAG_HAS_SCRIPT_CLASS:
            script_class = r.get_unicode()

        for _ in range(Flag.RESERVED_FIELDS):
            r.skip(4)

        string_map = []
        string_table_size = r.get_u32()
        for _ in range(string_table_size):
            string_map.append(r.get_unicode())

        def _parse_name() -> str:
            id = r.get_u32()
            if id & 0x80000000:
                length = id & 0x7FFFFFFF
                return str(r.read(length)[:-1].decode())
            else:
                return string_map[id]

        def _parse_value():
            prop_type = r.get_u32()
            if prop_type == PropType.VARIANT_NIL:
                return None
            elif prop_type == PropType.VARIANT_BOOL:
                return r.get_i32() != 0
            elif prop_type == PropType.VARIANT_INT:
                return r.get_i32()
            elif prop_type == PropType.VARIANT_INT64:
                return r.get_i64()
            elif prop_type == PropType.VARIANT_FLOAT:
                return r.get_f32()
            elif prop_type == PropType.VARIANT_DOUBLE:
                return r.get_f64()
            elif prop_type == PropType.VARIANT_STRING:
                return r.get_unicode()
            elif prop_type == PropType.VARIANT_PACKED_BYTE_ARRAY:
                length = r.get_u32()
                res = b"".join(r.get_u8() for _ in range(length))
                extra = 4 - (length % 4)
                if extra < 4:
                    for _ in range(extra):
                        r.get_u8()
                return res
            elif prop_type == PropType.VARIANT_PACKED_INT32_ARRAY:
                length = r.get_u32()
                return [r.get_i32() for _ in range(length)]
            else:
                return None

        external_resources = []
        ext_resources_size = r.get_u32()
        for _ in range(ext_resources_size):
            ty = r.get_unicode()
            path = r.get_unicode()
            uid = r.get_u64() if using_uids else None
            external_resources.append((ty, path, uid))

        int_resources_size = r.get_u32()
        internal_resources = []
        for _ in range(int_resources_size):
            path = r.get_unicode()
            offset = r.get_u64()
            internal_resources.append((path, offset))

        main_resource = None
        for i, (path, offset) in enumerate(internal_resources):
            r.seek(offset)
            class_name = r.get_unicode()
            properties = {}
            properties_count = r.get_i32()
            for j in range(properties_count):
                name = _parse_name()
                value = _parse_value()
                properties[name] = value

            if "_skip_save_" in properties.get("__meta__", {}):
                continue

            if i == len(internal_resources) - 1:
                main_resource = Resource(version_major, version_minor, format_version, importmd_ofs, class_name, flags, string_map, properties)

        return main_resource

def hash(d: int, b: bytes) -> int:
    if d == 0:
        d = 0x1000193
    for c in b:
        d = (d * 0x1000193) ^ c
    return d

@dataclass
class Elem:
    key: int
    str_offset: int
    comp_size: int
    uncomp_size: int

@dataclass
class Bucket:
    size: int
    func: int
    elem: list[Elem]

class BinaryTranslate:
    def __init__(self, path: str):
        res = parse_resource(path)
        if res.class_name not in ["PHashTranslation", "Translation", "OptimizedTranslation"]:
            raise Exception(f"{path}|{res.class_name} is not a PHashTranslation Resource")
        self.hash_table = res.properties["hash_table"]
        self.bucket_table = res.properties["bucket_table"]
        self.strings = res.properties["strings"]
        self.locale = res.properties.get("locale", "en")
        self.resource = res

    def save(self, path: str):
        r = self.resource
        with open(path, "wb") as f:
            w = Writer(f)
            w.write(b"RSRC")
            big_endian = False
            use_real64 = False
            w.store_i32(1 if big_endian else 0)
            w.store_i32(1 if use_real64 else 0)
            w.big_endian = big_endian

            w.store_i32(r.version_major)
            w.store_i32(r.version_minor)
            w.store_i32(r.format_version)
            w.store_unicode(r.class_name)
            w.store_i64(r.importmd_ofs)
            flags = r.flags
            if w.real_is_double:
                flags |= Flag.FORMAT_FLAG_REAL_T_IS_DOUBLE
            w.store_u32(flags)
            w.store_u64(0)

            for _ in range(Flag.RESERVED_FIELDS):
                w.store_i32(0)

            w.store_u32(len(r.string_map))
            for s in r.string_map:
                w.store_unicode(s)

            w.store_u32(0)
            w.store_u32(1)
            w.store_unicode("local://0")
            offset = f.tell() + 8
            w.store_u64(offset)

            w.store_unicode(r.class_name)
            w.store_i32(4)

            w.store_u32(r.string_map.index("locale"))
            w.store_u32(PropType.VARIANT_STRING)
            w.store_unicode(self.locale)

            w.store_u32(r.string_map.index("hash_table"))
            w.store_u32(PropType.VARIANT_PACKED_INT32_ARRAY)
            w.store_u32(len(self.hash_table))
            for v in self.hash_table:
                w.store_i32(v)

            w.store_u32(r.string_map.index("bucket_table"))
            w.store_u32(PropType.VARIANT_PACKED_INT32_ARRAY)
            w.store_u32(len(self.bucket_table))
            for v in self.bucket_table:
                w.store_i32(v)

            w.store_u32(r.string_map.index("strings"))
            w.store_u32(PropType.VARIANT_PACKED_BYTE_ARRAY)
            w.store_u32(len(self.strings))
            w.write(self.strings)
            extra = 4 - (len(self.strings) % 4)
            if extra < 4:
                w.write(b"\0" * extra)

            w.write(b"RSRC")

    def get_messages(self) -> list[str]:
        msgs = []
        for p, bucket_idx in enumerate(self.hash_table):
            if bucket_idx == -1:
                continue
            size = self.bucket_table[bucket_idx]
            bucket = Bucket(
                size=size,
                func=self.bucket_table[bucket_idx + 1],
                elem=[
                    Elem(
                        self.bucket_table[bucket_idx + 2 + 4 * i],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 1],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 2],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 3],
                    )
                    for i in range(size)
                ],
            )
            for e in bucket.elem:
                buf = self.strings[e.str_offset : e.str_offset + e.comp_size]
                if e.comp_size == e.uncomp_size:
                    msgs.append(buf.decode().strip("\0"))
                else:
                    msgs.append(smaz.decompress(buf).strip("\0"))
        return msgs

    def replace(self, messages: list[str]):
        old_strings = self.strings
        new_strings = b""
        new_str_offsets = []
        new_bucket_table = [0] * len(self.bucket_table)

        l = 0
        for m in messages:
            encoded = m.encode() + b"\0"
            new_strings += encoded
            new_str_offsets.append(l)
            l += len(encoded)

        n = 0
        for p, bucket_idx in enumerate(self.hash_table):
            if bucket_idx == -1:
                continue
            size = self.bucket_table[bucket_idx]
            bucket = Bucket(
                size=size,
                func=self.bucket_table[bucket_idx + 1],
                elem=[
                    Elem(
                        self.bucket_table[bucket_idx + 2 + 4 * i],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 1],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 2],
                        self.bucket_table[bucket_idx + 2 + 4 * i + 3],
                    )
                    for i in range(size)
                ],
            )
            for e in bucket.elem:
                buf = old_strings[e.str_offset : e.str_offset + e.comp_size]
                new_msg = messages[n].encode() + b"\0"
                e.comp_size = len(new_msg)
                e.uncomp_size = len(new_msg)
                e.str_offset = new_str_offsets[n]
                n += 1

                new_bucket_table[bucket_idx] = bucket.size
                new_bucket_table[bucket_idx + 1] = bucket.func
                for i, el in enumerate(bucket.elem):
                    new_bucket_table[bucket_idx + 2 + 4 * i] = el.key
                    new_bucket_table[bucket_idx + 2 + 4 * i + 1] = el.str_offset
                    new_bucket_table[bucket_idx + 2 + 4 * i + 2] = el.comp_size
                    new_bucket_table[bucket_idx + 2 + 4 * i + 3] = el.uncomp_size

        self.bucket_table = new_bucket_table
        self.strings = new_strings

load_dotenv()

def get_godotpcktool_path():
    current_dir_tool = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "godotpcktool.exe")
    if os.path.exists(current_dir_tool):
        return current_dir_tool
    
    path_tool = shutil.which("godotpcktool")
    if path_tool:
        return path_tool
        
    return None

def run_godotpcktool(pck_path: str, action: str, file_filter: str = None, output_path: str = None, extra_args: list = None):
    tool_path = get_godotpcktool_path()
    if tool_path is None:
        print("Error: 'godotpcktool.exe' not found.")
        print("Please download the latest version from https://github.com/hhyyrylainen/GodotPckTool/releases and place it in the same folder as this script.")
        sys.exit(1)

    cmd = [tool_path, pck_path, "--action", action]
    if file_filter:
        cmd.extend(["--include-regex-filter", file_filter])
    if output_path:
        cmd.extend(["--output", output_path])
    if extra_args:
        cmd.extend(extra_args)
        
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Godot Translation file Tool")
    parser.add_argument("--pck", help="Path to the .pck file (Optional)")
    parser.add_argument("--export", dest="export_file", help="Name of the .translation file to extract/convert (e.g., text.en.translation)")
    parser.add_argument("--import", dest="import_file", help="Path to the .csv file to import/apply")
    parser.add_argument("--locale", default="en", help="Locale code (default: en)")

    args = parser.parse_args()
    
    print("Godot Translation file Tool v1.2 by Snowyegret, Original by eunchuldev")
    current_directory = os.path.dirname(os.path.abspath(sys.argv[0])) 
    
    if args.export_file:
        target_file = args.export_file
        if args.pck:
            print(f"Extracting {args.export_file} from {args.pck}...")
            run_godotpcktool(args.pck, "extract", args.export_file, current_directory)
            
            found = False
            for root, dirs, files in os.walk(current_directory):
                if args.export_file in files:
                    target_file = os.path.join(root, args.export_file)
                    found = True
                    break
            if not found:
                 print(f"Error: Extracted {args.export_file} but could not find it.")
                 sys.exit(1)
        else:
             print(f"Single File Mode: Processing local file {target_file}...")
             if not os.path.exists(target_file):
                 print(f"Error: File '{target_file}' not found. Use --pck option or check the file path.")
                 sys.exit(1)

        print(f"Converting {target_file} to CSV...")
        try:
            messages = BinaryTranslate(target_file).get_messages()
            csv_filename = f"{args.export_file}.csv"
            with open(csv_filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow(["index", "original", "translated"])
                for i, m in enumerate(messages):
                    writer.writerow([str(i), m, ""])
            print(f"Successfully exported to {csv_filename}")
        except Exception as e:
            print(f"Error processing file: {e}")

    elif args.import_file:
        print(f"Importing {args.import_file}...")
        
        base_name = os.path.basename(args.import_file)
        if base_name.lower().endswith(".csv"):
            target_translation_name = base_name[:-4] 
        else:
            target_translation_name = base_name
        
        print(f"Target resource: {target_translation_name}")
        
        target_file = target_translation_name
        
        if args.pck:
            print(f"Extracting base file {target_translation_name} from {args.pck}...")
            run_godotpcktool(args.pck, "extract", target_translation_name, current_directory)
            found = False
            for root, dirs, files in os.walk(current_directory):
                if target_translation_name in files:
                    target_file = os.path.join(root, target_translation_name)
                    found = True
                    break
            if not found:
                print(f"Error: Could not find {target_translation_name} in PCK.")
                sys.exit(1)
        else:
             print(f"Single File Mode: Patching local file {target_file}...")
             if not os.path.exists(target_file):
                 print(f"Error: Target file '{target_file}' not found. Use --pck option to extract original or check file path.")
                 sys.exit(1)

        print(f"Patching {target_file} with {args.import_file}...")
        try:
            resource = BinaryTranslate(target_file)
            messages = []
            with open(args.import_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0: continue
                    messages.append(row[1] if row[2] == "" else row[2])
            
            resource.replace(messages)
            resource.locale = args.locale
            resource.save(target_file)
            print(f"Applied translation to {target_file}")

            if args.pck:
                print(f"Repacking {target_file} into {args.pck}...")
                
                rel_path = os.path.relpath(target_file, current_directory)
                
                run_godotpcktool(args.pck, "add", file_filter=None, output_path=None, extra_args=[rel_path])
                print("Repack complete.")

        except Exception as e:
            print(f"Error applying translation: {e}")
            sys.exit(1)
    else:
        parser.print_help()

    print("Done!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
