from escpos.printer import Usb
from PIL import Image

p = Usb(0x28E9, 0x0289)

PRINT_WIDTH_DOTS = 384


def print_image(path):
    img = Image.open(path)

    # Resize image to 58mm width (384 dots)
    img = img.resize(
        (PRINT_WIDTH_DOTS, int(img.height * (PRINT_WIDTH_DOTS / img.width)))
    )
    p.image(img)


print_image("images.jpg")
p.cut()
