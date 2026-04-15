"""MXW01 thermal printer module for BBS."""

import asyncio
from PIL import Image, ImageDraw, ImageFont

# Only import bleak when needed (printer might not be available)
PRINTER_ADDRESS = "84261105-6CF8-0C5A-6CC4-847490B66763"
CONTROL_CHAR = "0000ae01-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000ae02-0000-1000-8000-00805f9b34fb"
DATA_CHAR = "0000ae03-0000-1000-8000-00805f9b34fb"

CMD_GET_STATUS = 0xA1
CMD_SET_INTENSITY = 0xA2
CMD_PRINT_REQUEST = 0xA9
CMD_FLUSH_DATA = 0xAD
CMD_PRINT_COMPLETE = 0xAA

PRINTER_WIDTH = 384  # pixels


def crc8(data: bytes) -> int:
    """Calculate CRC8 checksum."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def make_command(cmd: int, payload: bytes = b"") -> bytes:
    """Build MXW01 command packet."""
    packet = bytearray()
    packet.extend([0x22, 0x21])
    packet.append(cmd)
    packet.append(0x00)
    length = len(payload)
    packet.append(length & 0xFF)
    packet.append((length >> 8) & 0xFF)
    packet.extend(payload)
    packet.append(crc8(payload) if payload else 0x00)
    packet.append(0xFF)
    return bytes(packet)


def text_to_bitmap(text: str, font_size: int = 20) -> list[bytes]:
    """Convert text to bitmap rows for printing."""
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except OSError:
        font = ImageFont.load_default()

    # Try to load emoji font for emoji characters
    try:
        emoji_font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", font_size)
    except OSError:
        emoji_font = None

    # Handle multi-line text by wrapping
    lines = wrap_text(text, font, PRINTER_WIDTH - 20)

    # Calculate total height needed (minimal spacing)
    line_height = font_size
    total_height = len(lines) * line_height + 2

    # Create RGBA image to support emoji (white background)
    img = Image.new("RGBA", (PRINTER_WIDTH, total_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw each line, handling emoji separately
    y = 1
    for line in lines:
        x = 10
        for char in line:
            # Check if character is emoji (outside basic ASCII/Latin)
            if ord(char) > 0x1F00 and emoji_font:
                try:
                    draw.text((x, y), char, font=emoji_font, fill=(0, 0, 0, 255), embedded_color=True)
                    bbox = draw.textbbox((x, y), char, font=emoji_font)
                except Exception:
                    draw.text((x, y), char, font=font, fill=(0, 0, 0, 255))
                    bbox = draw.textbbox((x, y), char, font=font)
            else:
                draw.text((x, y), char, font=font, fill=(0, 0, 0, 255))
                bbox = draw.textbbox((x, y), char, font=font)
            x = bbox[2]  # Move to end of character
        y += line_height

    # Convert to 1-bit bitmap (black pixels where any color is dark)
    img = img.convert("L").point(lambda p: 0 if p < 200 else 255, "1")

    # Convert to bitmap rows (LSB first)
    rows = []
    for y in range(img.height):
        row_bytes = bytearray(48)
        for x in range(PRINTER_WIDTH):
            pixel = img.getpixel((x, y))
            if pixel == 0:  # Black pixel
                byte_idx = x // 8
                bit_idx = x % 8  # LSB first
                row_bytes[byte_idx] |= (1 << bit_idx)
        rows.append(bytes(row_bytes))

    return rows


def wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels, respecting newlines."""
    dummy_img = Image.new("1", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    all_lines = []
    # First split by explicit newlines
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            all_lines.append("")
            continue

        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    all_lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            all_lines.append(" ".join(current_line))

    return all_lines if all_lines else [""]


async def _print_bitmap(rows: list[bytes]):
    """Send bitmap rows to printer."""
    from bleak import BleakClient

    async with BleakClient(PRINTER_ADDRESS, timeout=10.0) as client:
        # Set up notifications (required for protocol)
        await client.start_notify(NOTIFY_CHAR, lambda s, d: None)

        # Get status
        await client.write_gatt_char(CONTROL_CHAR, make_command(CMD_GET_STATUS))
        await asyncio.sleep(0.3)

        # Set intensity
        await client.write_gatt_char(CONTROL_CHAR, make_command(CMD_SET_INTENSITY, bytes([0x60])))
        await asyncio.sleep(0.1)

        # Send print request
        num_lines = len(rows)
        await client.write_gatt_char(
            CONTROL_CHAR,
            make_command(CMD_PRINT_REQUEST, bytes([num_lines & 0xFF, (num_lines >> 8) & 0xFF]))
        )
        await asyncio.sleep(0.1)

        # Send bitmap data (slower for QR codes to prevent squishing)
        for i, row in enumerate(rows):
            await client.write_gatt_char(DATA_CHAR, row)
            await asyncio.sleep(0.01)
            # Extra pause every 50 rows to let printer catch up
            if i % 50 == 49:
                await asyncio.sleep(0.1)

        # Flush and complete
        await client.write_gatt_char(CONTROL_CHAR, make_command(CMD_FLUSH_DATA))
        await asyncio.sleep(0.2)
        await client.write_gatt_char(CONTROL_CHAR, make_command(CMD_PRINT_COMPLETE))
        await asyncio.sleep(0.3)


def print_post(username: str, message: str, timestamp: str) -> bool:
    """
    Print a BBS post to the thermal printer.
    Returns True if successful, False if printer unavailable.
    """
    try:
        # Format the post for printing
        header = f"{username} @ {timestamp}"
        text = f"{header}\n{message}"

        rows = text_to_bitmap(text)
        asyncio.run(_print_bitmap(rows))
        return True
    except Exception as e:
        # Printer not available or other error
        print(f"(Printer unavailable: {e})")
        return False
