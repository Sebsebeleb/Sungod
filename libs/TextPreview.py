import os
import random
import re

from PIL import Image, ImageDraw, ImageFont

BORDER = (100, 100)


def preview(text):
    """Generate a picture of the provided text

    Arguments:
    text -- The text that will be drawn on the image

    """
    font_fp = os.path.join(os.path.expanduser("~seb"), "COUR.TTF")
    font = ImageFont.truetype(font_fp, 40)
    text_size = font.getsize(text)
    size = (BORDER[0] + text_size[0], BORDER[1] + text_size[1])
    img = Image.new("RGB", size, (230,230,230))
    draw = ImageDraw.Draw(img)
    colour = random_colour()
    draw.text((BORDER[0] / 2, BORDER[1] / 2), text, colour, font=font)


    fname = slugify(text[:18])+".png"  # Temp name giving
    fp = os.path.abspath(os.path.join(
        os.path.expanduser("~seb"), "www", "bbg.terminator.net", "media", "previews", fname))
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

def slugify(s):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    s = unicode(s)
    s = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    s = unicode(re.sub('[-\s]+', '-', value))
    return s