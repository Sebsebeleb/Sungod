import os

from PIL import Image, ImageDraw, ImageFont

BORDER = (100, 100)


def preview(text):
    """Generate a picture of the provided text

    Arguments:
    text -- The text that will be drawn on the image

    """
    font_fp = os.path.abspath(os.path.join("/", "COUR.TTF"))
    font = ImageFont.truetype(font_fp, 40)
    text_size = font.getsize(text)
    size = (BORDER[0] + text_size[0], BORDER[1] + text_size[1])
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    colour = random_colour()
    draw.text((BORDER[0] / 2, BORDER[1] / 2), text, colour)
    

    fname = text[:10]+".png"  # Temp name giving
    fp = os.path.abspath(os.path.join(
        "/", "home", "seb", "www", "bbg.terminator.net", "media", "previews", fname))
    img.save(fp)
    return fname


def random_colour():
    """Returns a random colour that is not too hard to read on the background"""
    while True:
        colour = random.randint(0, 255), random.randint(
            0, 255), random.randint(0, 255)
        # Require a 15% difference from pure white
        if (float(255 * 3) / sum(colour)) - 1 > 0.15:
            return colour
