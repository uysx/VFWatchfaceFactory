#!/usr/bin/env python3
"""
createiwffromfolder.py - Create IWF files from folder structure

Creates .iwf files from a folder structure containing images and configuration.
Reads iwf.json for background/preview and font.json for bank order.
"""

import json
import struct
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Callable, Any
from dataclasses import dataclass

# Import the image converter
from png2raw import PngToVeryfitRaw

# ==========================================================================
# DATA STRUCTURES
# ==========================================================================

@dataclass
class ImageInfo:
    """Information about an image file."""
    file_name: str
    base_name: str
    parent_name: str
    abs_path: str
    width: int = 0
    height: int = 0
    has_alpha: bool = False


@dataclass
class EntryToPack:
    """Entry to be packed into the IWF file."""
    logical_name: str
    abs_path: str
    is_image: bool = True
    force_opaque_preview: bool = False


@dataclass
class IwfJsonInfo:
    """Information parsed from iwf.json."""
    background_file: str = ""
    preview_file: str = ""
    valid: bool = False


@dataclass
class BankInfo:
    """Information about a bank of glyphs."""
    bank_name: str
    glyphs: Dict[int, int]  # glyph_id -> image_index


# ==========================================================================
# 1. SCAN ALL IMAGES
# ==========================================================================

def scan_all_images(src_dir: Path) -> List[ImageInfo]:
    """
    Scan all PNG and BMP images in the directory tree.
    
    Args:
        src_dir: Source directory to scan
    
    Returns:
        List of ImageInfo objects
    """
    out = []
    
    for ext in ['*.png', '*.bmp']:
        for path in src_dir.rglob(ext):
            try:
                result = PngToVeryfitRaw.probe_image(str(path))
                if result is None:
                    continue
                
                w, h, has_alpha = result
                
                info = ImageInfo(
                    file_name=path.name,
                    base_name=path.stem,
                    parent_name=path.parent.name,
                    abs_path=str(path),
                    width=w,
                    height=h,
                    has_alpha=has_alpha
                )
                out.append(info)
            except Exception:
                continue
    
    return out


def find_first_image_index(all_images: List[ImageInfo], 
                          pred: Callable[[ImageInfo], bool]) -> int:
    """
    Find the first image matching a predicate.
    
    Args:
        all_images: List of ImageInfo objects
        pred: Predicate function
    
    Returns:
        Index of first matching image, or -1 if not found
    """
    for i, img in enumerate(all_images):
        if pred(img):
            return i
    return -1


def find_by_prefix(all_images: List[ImageInfo], prefix_lower: str) -> int:
    """
    Find image by filename prefix.
    
    Args:
        all_images: List of ImageInfo objects
        prefix_lower: Prefix to match (case-insensitive)
    
    Returns:
        Index of first matching image, or -1 if not found
    """
    for i, img in enumerate(all_images):
        if img.file_name.lower().startswith(prefix_lower):
            return i
    return -1


# ==========================================================================
# 2. PARSE IWF.JSON
# ==========================================================================

def parse_iwf_json(src_dir: Path) -> IwfJsonInfo:
    """
    Parse iwf.json to extract bkground and preview fields.
    
    Args:
        src_dir: Source directory containing iwf.json
    
    Returns:
        IwfJsonInfo object
    """
    info = IwfJsonInfo()
    
    iwf_path = src_dir / 'iwf.json'
    if not iwf_path.exists():
        return info
    
    try:
        with open(iwf_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            if 'bkground' in data and isinstance(data['bkground'], str):
                info.background_file = data['bkground']
            if 'preview' in data and isinstance(data['preview'], str):
                info.preview_file = data['preview']
        
        info.valid = bool(info.background_file or info.preview_file)
    except Exception:
        pass
    
    return info


def extract_referenced_images(src_dir: Path) -> Set[str]:
    """
    Extract all image filenames referenced in iwf.json.
    
    Args:
        src_dir: Source directory containing iwf.json
    
    Returns:
        Set of image filenames
    """
    referenced = set()
    iwf_path = src_dir / 'iwf.json'
    
    if not iwf_path.exists():
        return referenced
    
    try:
        with open(iwf_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            return referenced
        
        # Root-level keys
        for key in ['bkground', 'preview']:
            if key in data and isinstance(data[key], str) and data[key]:
                referenced.add(data[key])
        
        # Item-level keys
        if 'item' in data and isinstance(data['item'], list):
            item_keys = ['hour', 'minute', 'second', 'bg', 'animaicon', 'progress']
            for item in data['item']:
                if isinstance(item, dict):
                    for key in item_keys:
                        if key in item and isinstance(item[key], str) and item[key]:
                            referenced.add(item[key])
    except Exception:
        pass
    
    return referenced


# ==========================================================================
# 3. READ FONT.JSON
# ==========================================================================

def read_font_order(src_dir: Path) -> List[str]:
    """
    Read the order of banks from font.json.
    
    Args:
        src_dir: Source directory containing font.json
    
    Returns:
        List of bank names in order
    """
    font_path = src_dir / 'font.json'
    if not font_path.exists():
        return []
    
    try:
        with open(font_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            return []
        
        items = data.get('item', [])
        if not isinstance(items, list):
            return []
        
        order = []
        for item in items:
            if isinstance(item, dict):
                name = item.get('name', '')
                if isinstance(name, str) and name.strip():
                    order.append(name.strip())
        
        return order
    except Exception:
        return []


# ==========================================================================
# 4. BUILD BANKS
# ==========================================================================

def try_parse_numeric(s: str) -> Optional[int]:
    """
    Try to parse a string as an integer.
    
    Args:
        s: String to parse
    
    Returns:
        Integer value or None if parsing fails
    """
    try:
        return int(s)
    except ValueError:
        return None


def build_banks(all_images: List[ImageInfo], src_dir: Path) -> Dict[str, BankInfo]:
    """
    Build bank structures from images in subdirectories.
    
    Args:
        all_images: List of all ImageInfo objects
        src_dir: Source directory
    
    Returns:
        Dictionary mapping bank name to BankInfo
    """
    banks = {}
    root_name = src_dir.name
    
    for i, img in enumerate(all_images):
        # Skip root-level images
        if not img.parent_name or img.parent_name == root_name or img.parent_name == '.':
            continue
        
        # Try to parse base name as integer
        glyph_id = try_parse_numeric(img.base_name)
        if glyph_id is None:
            continue
        
        # Register in bank
        if img.parent_name not in banks:
            banks[img.parent_name] = BankInfo(bank_name=img.parent_name, glyphs={})
        banks[img.parent_name].glyphs[glyph_id] = i
    
    return banks


# ==========================================================================
# 5. GENERAL ORDER FOR GLYPHS
# ==========================================================================

# General order of glyphs (0-40)
GENERAL_ORDER = [
    26, 24, 2, 11, 37, 6, 38, 15, 21, 28, 36, 29, 16, 3, 10, 40,
    4, 33, 39, 35, 18, 34, 22, 31, 27, 9, 7, 1, 19, 25, 32, 20,
    14, 0, 23, 12, 30, 5, 17, 13, 8
]

# Week order (observed from VeryFit dumps)
WEEK_ORDER = ['tue', 'fri', 'sat', 'sun', 'thur', 'wed', 'mon']

# Month order (observed from VeryFit dumps)
MONTH_ORDER = ['nov', 'oct', 'dec', 'may', 'june', 'apr', 'jan', 
               'feb', 'sept', 'july', 'mar', 'aug']


# ==========================================================================
# 6. EMIT BANK / WEEK / MONTH
# ==========================================================================

def emit_bank_in_order(bank_name: str, bank: BankInfo, 
                       all_images: List[ImageInfo],
                       result: List[EntryToPack]) -> None:
    """
    Emit bank glyphs in the general order.
    
    Args:
        bank_name: Name of the bank
        bank: BankInfo object
        all_images: List of all ImageInfo objects
        result: List to append entries to
    """
    for glyph_id in GENERAL_ORDER:
        if glyph_id not in bank.glyphs:
            continue
        
        img_idx = bank.glyphs[glyph_id]
        logical = f"{bank_name}_{glyph_id}"
        
        if 0 <= img_idx < len(all_images):
            entry = EntryToPack(
                logical_name=logical,
                abs_path=all_images[img_idx].abs_path,
                is_image=True,
                force_opaque_preview=False
            )
            result.append(entry)


def emit_week_bank(all_images: List[ImageInfo], result: List[EntryToPack]) -> None:
    """
    Emit week bank in the observed order.
    
    Args:
        all_images: List of all ImageInfo objects
        result: List to append entries to
    """
    for day in WEEK_ORDER:
        want_file = f"en_{day}.png".lower()
        logical = f"week_en_{day}"
        
        found_idx = -1
        for i, img in enumerate(all_images):
            if img.parent_name.lower() == 'week' and img.file_name.lower() == want_file:
                found_idx = i
                break
        
        if found_idx >= 0:
            entry = EntryToPack(
                logical_name=logical,
                abs_path=all_images[found_idx].abs_path,
                is_image=True,
                force_opaque_preview=False
            )
            result.append(entry)


def emit_month_bank(all_images: List[ImageInfo], result: List[EntryToPack]) -> None:
    """
    Emit month bank in the observed order.
    
    Args:
        all_images: List of all ImageInfo objects
        result: List to append entries to
    """
    for month in MONTH_ORDER:
        want_file = f"en_{month}.png".lower()
        logical = f"month_en_{month}"
        
        found_idx = -1
        for i, img in enumerate(all_images):
            if img.parent_name.lower() == 'month' and img.file_name.lower() == want_file:
                found_idx = i
                break
        
        if found_idx >= 0:
            entry = EntryToPack(
                logical_name=logical,
                abs_path=all_images[found_idx].abs_path,
                is_image=True,
                force_opaque_preview=False
            )
            result.append(entry)


# ==========================================================================
# 7. BUILD ORDERED ENTRY LIST
# ==========================================================================

def build_ordered_entry_list(src_dir: Path) -> List[EntryToPack]:
    """
    Build the final ordered list of entries for IWF.
    
    Order:
    1. iwf.json
    2. font.json
    3. background (from iwf.json "bkground")
    4. preview (from iwf.json "preview")
    5. All other root-level referenced images
    6. Banks in font.json order
    
    Args:
        src_dir: Source directory
    
    Returns:
        List of EntryToPack objects in order
    """
    result = []
    
    # (A) Scan all images
    all_images = scan_all_images(src_dir)
    
    # (B) Parse iwf.json
    iwf_info = parse_iwf_json(src_dir)
    referenced_images = extract_referenced_images(src_dir)
    
    # (C) Read font order
    font_order = read_font_order(src_dir)
    
    # ========== 1. iwf.json + font.json at beginning ==========
    for fname in ['iwf.json', 'font.json']:
        fpath = src_dir / fname
        if fpath.exists():
            entry = EntryToPack(
                logical_name=fname,
                abs_path=str(fpath),
                is_image=False,
                force_opaque_preview=False
            )
            result.append(entry)
    
    # ========== Add referenced images: background, preview, then others ==========
    
    # Background first
    if iwf_info.background_file and iwf_info.background_file in referenced_images:
        idx_bg = find_first_image_index(all_images, 
            lambda im: im.file_name.lower() == iwf_info.background_file.lower())
        
        if idx_bg >= 0:
            entry = EntryToPack(
                logical_name=all_images[idx_bg].file_name,
                abs_path=all_images[idx_bg].abs_path,
                is_image=True,
                force_opaque_preview=False
            )
            result.append(entry)
            referenced_images.discard(iwf_info.background_file)
    
    # Preview next
    if iwf_info.preview_file and iwf_info.preview_file in referenced_images:
        idx_prev = find_first_image_index(all_images,
            lambda im: im.file_name.lower() == iwf_info.preview_file.lower())
        
        if idx_prev >= 0:
            entry = EntryToPack(
                logical_name=all_images[idx_prev].file_name,
                abs_path=all_images[idx_prev].abs_path,
                is_image=True,
                force_opaque_preview=True
            )
            result.append(entry)
            referenced_images.discard(iwf_info.preview_file)
    
    # All other referenced root-level images
    for img_name in list(referenced_images):
        idx = find_first_image_index(all_images,
            lambda im: (not im.parent_name or im.parent_name == '.' or im.parent_name == src_dir.name)
            and im.file_name.lower() == img_name.lower())
        
        if idx >= 0:
            entry = EntryToPack(
                logical_name=all_images[idx].file_name,
                abs_path=all_images[idx].abs_path,
                is_image=True,
                force_opaque_preview=False
            )
            result.append(entry)
    
    # ========== Banks in font.json order ==========
    banks = build_banks(all_images, src_dir)
    
    for bank_name in font_order:
        if bank_name.lower() == 'week':
            emit_week_bank(all_images, result)
            continue
        if bank_name.lower() == 'month':
            emit_month_bank(all_images, result)
            continue
        
        if bank_name in banks:
            emit_bank_in_order(bank_name, banks[bank_name], all_images, result)
    
    return result


# ==========================================================================
# 8. WRITE IWF FILE
# ==========================================================================

def write_name32(name: str) -> bytes:
    """
    Write a 32-byte null-terminated name.
    
    Args:
        name: Name string
    
    Returns:
        32-byte padded name
    """
    b = name.encode('latin-1')[:31]
    return b + b'\x00' * (32 - len(b))


def create_iwf_from_folder(src_dir: Path, out_path: Path) -> bool:
    """
    Create an IWF file from a folder.
    
    Args:
        src_dir: Source directory
        out_path: Output file path
    
    Returns:
        True on success, False on failure
    """
    try:
        src_dir = Path(src_dir)
        out_path = Path(out_path)
        
        # 1. Build ordered entry list
        entries = build_ordered_entry_list(src_dir)
        entry_count = len(entries)
        
        # 2. Convert each entry to blob
        built_entries = []
        running_offset = 0
        
        for entry in entries:
            data = b''
            if entry.is_image:
                data = PngToVeryfitRaw.convert_auto(entry.abs_path, entry.force_opaque_preview)
            else:
                try:
                    with open(entry.abs_path, 'rb') as f:
                        data = f.read()
                except Exception:
                    data = b''
            
            built = {
                'meta': entry,
                'data': data,
                'size': len(data),
                'local_offset': running_offset
            }
            built_entries.append(built)
            running_offset += len(data)
        
        # 3. Build header + index table
        header_size = 8
        index_size = entry_count * 40
        base_offset = header_size + index_size
        
        # Build header and index
        header_index = bytearray(base_offset)
        
        # Magic: "iwf\0"
        header_index[0:4] = b'iwf\x00'
        # Version 1
        header_index[4:6] = b'\x01\x00'
        # Entry count (little-endian)
        struct.pack_into('<H', header_index, 6, entry_count)
        
        # Index table
        idx_ptr = 8
        for i, built in enumerate(built_entries):
            # Name (32 bytes)
            name_bytes = write_name32(built['meta'].logical_name)
            header_index[idx_ptr:idx_ptr + 32] = name_bytes
            idx_ptr += 32
            
            # Absolute offset
            abs_off = base_offset + built['local_offset']
            struct.pack_into('<I', header_index, idx_ptr, abs_off)
            idx_ptr += 4
            
            # Size
            struct.pack_into('<I', header_index, idx_ptr, built['size'])
            idx_ptr += 4
        
        # 4. Concatenate header+index + data
        final_iwf = bytes(header_index)
        for built in built_entries:
            final_iwf += built['data']
        
        # 5. Write to disk
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(final_iwf)
        
        return True
        
    except Exception as e:
        print(f"Error creating IWF: {e}")
        return False
    
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Create IWF file from folder structure.")
    parser.add_argument("src_dir", type=str, help="Source directory containing images and configuration.")
    parser.add_argument("out_file", type=str, help="Output IWF file path.")
    
    args = parser.parse_args()
    
    success = create_iwf_from_folder(Path(args.src_dir), Path(args.out_file))
    if success:
        print(f"Successfully created IWF file: {args.out_file}")
    else:
        print("Failed to create IWF file.")
        

if __name__ == "__main__":
    main()