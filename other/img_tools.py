from PIL import Image, ImageDraw, ImageFont

from other.config_reader import start_path


def create_image_with_text(text, font_path='DejaVuSansMono.ttf', font_size=30, image_size=(550, 400)):
    """
    Создание картинки с заданным текстом
    """
    # Создание пустого изображения
    image = Image.new('RGB', image_size, color='white')
    draw = ImageDraw.Draw(image)

    # Загрузка шрифта
    font = ImageFont.truetype(font_path, font_size)

    # Расчет позиции для размещения текста по центру с использованием textbbox
    textbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = textbox[2] - textbox[0], textbox[3] - textbox[1]
    x = (image_size[0] - text_width) / 2
    y = (image_size[1] - text_height) / 2

    draw.text((x, y), text, font=font, fill='black')

    # Сохранение или отображение изображения
    image.save(start_path + 'data/output_image.png')
