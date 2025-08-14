import os
from module.logger import logger
from datetime import datetime
from PIL import Image, ImageDraw
from random import random

SAVE_DIR = './.captcha'
LAST_IMAGE_FILE = ''

def solve(page, debug=False):
    image_path = grab_captcha(page)
    if not image_path:
        return
    output_image_path = None
    if debug:
        output_image_path = image_path.replace(".png", "_debug.png")
    ret = process_captcha(image_path, output_image_path)
    if not debug:
        os.unlink(image_path)
    return ret

def get_captcha_url(page):
    try:
        captcha = page.locator('input[type="image"][src*="/captcha_show.phtml"]')
        return captcha.get_property('src').json_value()
    except Exception:
        return ''

def grab_captcha(page):
    PADDING = 4
    if not os.path.exists(SAVE_DIR):
        os.mkdir(SAVE_DIR)
    if 'SOLD OUT!' in page.content():
        return
    try:
        captcha = page.locator('input[type="image"][src*="/captcha_show.phtml"]')
        filename = f"{SAVE_DIR}/captcha_{int(datetime.now().timestamp())}_{int(random()*10**6)}.png"
        with open(filename, 'wb') as f:
            f.write(captcha.screenshot(path=filename))
        img = Image.open(filename)
        cropped_img = img.crop((PADDING, PADDING, img.width - PADDING, img.height - PADDING))
        cropped_img.save(filename)
        return filename
    except Exception as err:
        logger.warning("Error while getting captcha canvas")
        logger.exception(err)
        return


def process_captcha(input_image_path, output_image_path=None):
    global LAST_IMAGE_FILE
    image = Image.open(input_image_path).convert("RGB")
    pixels = image.load()

    min_luminance = float("inf")
    click_position = (0, 0)

    # Find the darkest pixel
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]

            # Calculate luminance (brightness)
            luminance = (max(r, g, b) + min(r, g, b)) / 2

            if luminance < min_luminance:
                min_luminance = luminance
                click_position = (x, y)

    if output_image_path:
        debug_image = image.copy()
        draw = ImageDraw.Draw(debug_image)
        dot_radius = 5
        draw.ellipse(
            [
                (click_position[0] - dot_radius, click_position[1] - dot_radius),
                (click_position[0] + dot_radius, click_position[1] + dot_radius),
            ],
            fill="red",
        )
        debug_image.save(output_image_path)
        LAST_IMAGE_FILE = output_image_path
    return click_position


# Example usage
if __name__ == "__main__":
    for image in os.listdir(".captcha"):
        if image.startswith("debug_"):
            continue
        input_image = f".captcha/{image}"
        output_image = f".captcha/debug_{image}"
        print(input_image, process_captcha(input_image, output_image))
