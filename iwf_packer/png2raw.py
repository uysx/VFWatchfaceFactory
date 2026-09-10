#!/usr/bin/env python3
"""
pngtoveryfitraw.py - Convert PNG images to VeryFit RAW format

Converts PNG/BMP images to the RAW format used by VeryFit watch faces.
Format: "RAW\0" + uint16_le(width) + uint16_le(height) + RGB565 data + A4 alpha
"""

import struct
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np


class PngToVeryfitRaw:
    """Convert images to VeryFit RAW format."""
    
    @staticmethod
    def pack_rgb565(r: int, g: int, b: int) -> int:
        """
        Pack RGB888 values to RGB565 (big-endian for VeryFit).
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        
        Returns:
            RGB565 packed value (big-endian)
        """
        r5 = (r >> 3) & 0x1F
        g6 = (g >> 2) & 0x3F
        b5 = (b >> 3) & 0x1F
        return (r5 << 11) | (g6 << 5) | b5
    
    @staticmethod
    def probe_image(path: str) -> Optional[Tuple[int, int, bool]]:
        """
        Probe an image to get width, height, and alpha presence.
        
        Args:
            path: Path to the image file
        
        Returns:
            Tuple of (width, height, has_alpha) or None if error
        """
        try:
            img = Image.open(path)
            w, h = img.size
            
            # Check for alpha
            has_alpha = False
            if img.mode in ('RGBA', 'LA', 'PA'):
                img_rgba = img.convert('RGBA')
                data = np.array(img_rgba, dtype=np.uint8)
                has_alpha = np.any(data[:, :, 3] < 255)
            elif img.mode == 'P':
                # Palette mode - check if transparency is used
                if 'transparency' in img.info:
                    has_alpha = True
            
            return w, h, has_alpha
        except Exception as e:
            print(f"Probe error for {path}: {e}")
            return None
    
    @staticmethod
    def convert_auto(path: str, force_opaque_preview: bool = False) -> bytes:
        """
        Convert image to VeryFit RAW format.
        
        Args:
            path: Path to the image file
            force_opaque_preview: If True, force opaque flags (0x0085)
        
        Returns:
            RAW data bytes or empty bytes on error
        """
        try:
            img = Image.open(path)
            
            # Convert to RGBA
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            w, h = img.size
            
            # Convert to numpy array with explicit dtype
            data = np.array(img, dtype=np.uint8)
            
            # Validate dimensions
            if w <= 0 or h <= 0:
                print(f"Invalid dimensions for {path}: {w}x{h}")
                return b''
            
            # Detect alpha (unless forced opaque)
            has_alpha = False
            if not force_opaque_preview:
                has_alpha = np.any(data[:, :, 3] < 255)
            
            # Generate RGB565 data (big-endian)
            rgb565 = bytearray(w * h * 2)
            idx = 0
            
            for y in range(h):
                for x in range(w):
                    # Get pixel values as Python ints to avoid overflow
                    r = int(data[y, x, 0])
                    g = int(data[y, x, 1])
                    b = int(data[y, x, 2])
                    a = int(data[y, x, 3])
                    
                    # Premultiply alpha if not fully opaque
                    if a < 255 and a > 0:
                        r = (r * a) // 255
                        g = (g * a) // 255
                        b = (b * a) // 255
                    elif a == 0:
                        r = g = b = 0
                    
                    px = PngToVeryfitRaw.pack_rgb565(r, g, b)
                    # Big-endian: high byte first
                    rgb565[idx] = (px >> 8) & 0xFF
                    rgb565[idx + 1] = px & 0xFF
                    idx += 2
            
            # Generate A4 alpha channel (4 bits/pixel, 2 pixels/byte)
            alpha_a4 = bytearray()
            if has_alpha and not force_opaque_preview:
                # Calculate exactly how many bytes we need
                # Each byte stores 2 pixels, so we need ceil(w/2) bytes per row
                bytes_per_row = (w + 1) // 2
                total_bytes = bytes_per_row * h
                alpha_a4 = bytearray(total_bytes)
                
                idx = 0
                for y in range(h):
                    for x in range(0, w, 2):
                        # Get alpha values as Python ints
                        a0 = int(data[y, x, 3])
                        a0_4 = (a0 * 15) // 255
                        
                        a1_4 = 0
                        if x + 1 < w:
                            a1 = int(data[y, x + 1, 3])
                            a1_4 = (a1 * 15) // 255
                        
                        # Make sure we don't go out of bounds
                        if idx < total_bytes:
                            alpha_a4[idx] = (a0_4 << 4) | (a1_4 & 0x0F)
                            idx += 1
                        else:
                            print(f"Warning: Alpha buffer overflow at {idx} >= {total_bytes}")
                            break
                    if idx >= total_bytes:
                        break
            
            # Build header (16 bytes)
            header = bytearray(16)
            # "RAW\0"
            header[0:4] = b'RAW\x00'
            # width, height (little-endian)
            struct.pack_into('<H', header, 4, w)
            struct.pack_into('<H', header, 6, h)
            
            # flags
            if has_alpha and not force_opaque_preview:
                header[8:10] = b'\x85\x66'
            else:
                header[8:10] = b'\x85\x00'
            
            # [10..11] 0x0000
            # [12..13] RGB565 size if alpha present
            if has_alpha and not force_opaque_preview:
                rgb_size = w * h * 2
                struct.pack_into('<H', header, 12, rgb_size)
            # [14..15] 0x0000
            
            # Build final output
            output = bytes(header) + bytes(rgb565)
            if has_alpha and not force_opaque_preview:
                output += bytes(alpha_a4)
            
            return output
            
        except Exception as e:
            print(f"Error converting {path}: {e}")
            import traceback
            traceback.print_exc()
            return b''
    
    @staticmethod
    def convert_with_canvas(path: str, canvas_w: int, canvas_h: int) -> bytes:
        """
        Convert image with canvas support.
        
        Args:
            path: Path to the image file
            canvas_w: Canvas width
            canvas_h: Canvas height
        
        Returns:
            RAW data bytes or empty bytes on error
        """
        try:
            src = Image.open(path)
            if src.mode != 'RGBA':
                src = src.convert('RGBA')
            
            w_src, h_src = src.size
            
            # Validate dimensions
            if canvas_w <= 0 or canvas_h <= 0:
                print(f"Invalid canvas dimensions: {canvas_w}x{canvas_h}")
                return b''
            
            # Create canvas
            canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
            canvas.paste(src, (0, 0))
            
            # Convert to data with explicit dtype
            data = np.array(canvas, dtype=np.uint8)
            
            # Check for alpha
            need_a4 = np.any(data[:, :, 3] < 255)
            
            # Generate RGB565
            rgb565 = bytearray(canvas_w * canvas_h * 2)
            idx = 0
            
            for y in range(canvas_h):
                for x in range(canvas_w):
                    # Get pixel values as Python ints
                    r = int(data[y, x, 0])
                    g = int(data[y, x, 1])
                    b = int(data[y, x, 2])
                    a = int(data[y, x, 3])
                    
                    # Premultiply
                    if a < 255 and a > 0:
                        r = (r * a) // 255
                        g = (g * a) // 255
                        b = (b * a) // 255
                    elif a == 0:
                        r = g = b = 0
                    
                    px = PngToVeryfitRaw.pack_rgb565(r, g, b)
                    rgb565[idx] = (px >> 8) & 0xFF
                    rgb565[idx + 1] = px & 0xFF
                    idx += 2
            
            # Generate A4 alpha
            a4 = bytearray()
            if need_a4:
                a4_row_bytes = (canvas_w + 1) // 2
                a4 = bytearray(a4_row_bytes * canvas_h)
                
                idx = 0
                for y in range(canvas_h):
                    for x in range(0, canvas_w, 2):
                        a0 = int(data[y, x, 3])
                        a0_4 = (a0 + 8) // 17  # 0..255 -> 0..15
                        
                        a1_4 = 0
                        if x + 1 < canvas_w:
                            a1 = int(data[y, x + 1, 3])
                            a1_4 = (a1 + 8) // 17
                        
                        if idx < len(a4):
                            a4[idx] = (a0_4 << 4) | (a1_4 & 0x0F)
                            idx += 1
            
            # Build header
            header = bytearray(16)
            header[0:4] = b'RAW\x00'
            struct.pack_into('<H', header, 4, canvas_w)
            struct.pack_into('<H', header, 6, canvas_h)
            
            flags = 0x6685 if need_a4 else 0x0085
            struct.pack_into('<H', header, 8, flags)
            
            if need_a4:
                struct.pack_into('<H', header, 12, canvas_w * canvas_h * 2)
            
            return bytes(header) + bytes(rgb565) + bytes(a4)
            
        except Exception as e:
            print(f"Error converting with canvas: {e}")
            import traceback
            traceback.print_exc()
            return b''
    
    @staticmethod
    def convert_auto_safe(path: str, force_opaque_preview: bool = False) -> bytes:
        """
        Safely convert image with additional error checking.
        
        This method validates image dimensions and handles edge cases.
        
        Args:
            path: Path to the image file
            force_opaque_preview: If True, force opaque flags (0x0085)
        
        Returns:
            RAW data bytes or empty bytes on error
        """
        try:
            # First check if image exists and is valid
            if not Path(path).exists():
                print(f"File not found: {path}")
                return b''
            
            # Open and validate image
            img = Image.open(path)
            w, h = img.size
            
            # VeryFit typically uses 74x80 or similar small sizes
            if w <= 0 or h <= 0:
                print(f"Invalid image dimensions for {path}: {w}x{h}")
                return b''
            
            # Convert using the main method
            return PngToVeryfitRaw.convert_auto(path, force_opaque_preview)
            
        except Exception as e:
            print(f"Safe conversion failed for {path}: {e}")
            return b''
    
    @staticmethod
    def convert_auto_with_debug(path: str, force_opaque_preview: bool = False) -> Tuple[bytes, dict]:
        """
        Convert image with debug information.
        
        Returns:
            Tuple of (raw_data, debug_info)
        """
        debug = {
            'path': path,
            'width': 0,
            'height': 0,
            'has_alpha': False,
            'rgb565_size': 0,
            'alpha_size': 0,
            'total_size': 0,
            'success': False
        }
        
        try:
            img = Image.open(path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            w, h = img.size
            debug['width'] = w
            debug['height'] = h
            
            data = np.array(img, dtype=np.uint8)
            
            has_alpha = False
            if not force_opaque_preview:
                has_alpha = np.any(data[:, :, 3] < 255)
            debug['has_alpha'] = has_alpha
            
            # Generate RGB565
            rgb565 = bytearray(w * h * 2)
            idx = 0
            
            for y in range(h):
                for x in range(w):
                    r = int(data[y, x, 0])
                    g = int(data[y, x, 1])
                    b = int(data[y, x, 2])
                    a = int(data[y, x, 3])
                    
                    if a < 255 and a > 0:
                        r = (r * a) // 255
                        g = (g * a) // 255
                        b = (b * a) // 255
                    elif a == 0:
                        r = g = b = 0
                    
                    px = PngToVeryfitRaw.pack_rgb565(r, g, b)
                    rgb565[idx] = (px >> 8) & 0xFF
                    rgb565[idx + 1] = px & 0xFF
                    idx += 2
            
            debug['rgb565_size'] = len(rgb565)
            
            # Generate A4 alpha
            alpha_a4 = bytearray()
            if has_alpha and not force_opaque_preview:
                bytes_per_row = (w + 1) // 2
                total_bytes = bytes_per_row * h
                alpha_a4 = bytearray(total_bytes)
                debug['alpha_size'] = total_bytes
                
                idx = 0
                for y in range(h):
                    for x in range(0, w, 2):
                        a0 = int(data[y, x, 3])
                        a0_4 = (a0 * 15) // 255
                        
                        a1_4 = 0
                        if x + 1 < w:
                            a1 = int(data[y, x + 1, 3])
                            a1_4 = (a1 * 15) // 255
                        
                        if idx < total_bytes:
                            alpha_a4[idx] = (a0_4 << 4) | (a1_4 & 0x0F)
                            idx += 1
            
            # Build header
            header = bytearray(16)
            header[0:4] = b'RAW\x00'
            struct.pack_into('<H', header, 4, w)
            struct.pack_into('<H', header, 6, h)
            
            if has_alpha and not force_opaque_preview:
                header[8:10] = b'\x85\x66'
                struct.pack_into('<H', header, 12, w * h * 2)
            else:
                header[8:10] = b'\x85\x00'
            
            output = bytes(header) + bytes(rgb565)
            if has_alpha and not force_opaque_preview:
                output += bytes(alpha_a4)
            
            debug['total_size'] = len(output)
            debug['success'] = True
            
            return output, debug
            
        except Exception as e:
            debug['error'] = str(e)
            return b'', debug