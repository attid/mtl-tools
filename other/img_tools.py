from PIL import Image, ImageDraw, ImageFont

from other.config_reader import start_path


def create_image_with_text(text, font_path='DejaVuSansMono.ttf', font_size=30, image_size=(550, 400)):
    """
    Create an image with the provided text centred on the canvas.
    Intermediate subtotal rows (lines with digits that start with '=') are rendered in grey.
    """
    image = Image.new('RGB', image_size, color='white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    lines = text.splitlines()
    if not lines:
        lines = ['']

    line_spacing = 4

    line_metrics = []
    max_line_width = 0
    total_text_height = -line_spacing

    for line in lines:
        display_line = line or ' '
        left, top, right, bottom = draw.textbbox((0, 0), display_line, font=font)
        width = right - left
        height = bottom - top
        line_metrics.append((line, width, height))
        max_line_width = max(max_line_width, width)
        total_text_height += height + line_spacing

    x_base = (image_size[0] - max_line_width) / 2
    y = (image_size[1] - total_text_height) / 2

    for line, width, height in line_metrics:
        display_line = line or ' '
        fill = 'gray' if line.startswith('=') and any(char.isdigit() for char in line) else 'black'
        x = (image_size[0] - width) / 2 if width < image_size[0] else x_base
        draw.text((x, y), display_line, font=font, fill=fill)
        y += height + line_spacing

    image.save(start_path + 'data/output_image.png')
