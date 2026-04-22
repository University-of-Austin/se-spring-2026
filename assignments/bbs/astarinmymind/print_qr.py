"""Generate and print a QR code for the BBS URL."""

import asyncio
import qrcode
from PIL import Image, ImageDraw, ImageFont
from printer import PRINTER_WIDTH, _print_bitmap

def generate_qr_bitmap(url: str, label: str = "Scan to post") -> list[bytes]:
    """Generate QR code bitmap rows for printing."""
    # Generate QR code with high error correction and large modules
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% error tolerance
        box_size=10,
        border=6
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.convert("L").point(lambda x: 0 if x < 128 else 255, "1")

    # Load font for label
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except OSError:
        font = ImageFont.load_default()

    # Calculate sizes (extra padding at bottom to prevent cutoff)
    qr_size = qr_img.size[0]
    label_height = 24
    bottom_padding = 40
    total_height = qr_size + label_height + 10 + bottom_padding

    # Create final image
    img = Image.new("1", (PRINTER_WIDTH, total_height), 1)

    # Center and paste QR code
    qr_x = (PRINTER_WIDTH - qr_size) // 2
    img.paste(qr_img, (qr_x, 5))

    # Add label below
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), label, font=font)
    label_width = bbox[2] - bbox[0]
    label_x = (PRINTER_WIDTH - label_width) // 2
    draw.text((label_x, qr_size + 8), label, font=font, fill=0)

    # Convert to bitmap rows (LSB first)
    rows = []
    for y in range(img.height):
        row_bytes = bytearray(48)
        for x in range(PRINTER_WIDTH):
            pixel = img.getpixel((x, y))
            if pixel == 0:  # Black pixel
                byte_idx = x // 8
                bit_idx = x % 8
                row_bytes[byte_idx] |= (1 << bit_idx)
        rows.append(bytes(row_bytes))

    return rows


def print_qr(url: str, label: str = "Scan to post"):
    """Print QR code to thermal printer."""
    print(f"Generating QR code for: {url}")
    rows = generate_qr_bitmap(url, label)
    print(f"Printing {len(rows)} rows...")
    try:
        asyncio.run(_print_bitmap(rows))
        print("Done!")
    except Exception as e:
        print(f"Printer unavailable: {e}")


if __name__ == "__main__":
    import sys
    # Get local IP
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()

    url = f"http://{local_ip}:8080"
    print_qr(url, "Angela's BBS")
