import re
import os
import cv2
import numpy as np
import socket
import struct
import json
from PIL import Image
from datetime import datetime
import pytz, tzlocal
from glob import glob
from pathlib import Path
from itertools import combinations

REGEX_NODE = re.compile(r'(-?[A-Za-z]+)(-?\d+)')


def random_normal_distribution_int(a, b, n=3):
    """Generate a normal distribution int within the interval. Use the average value of several random numbers to
    simulate normal distribution.

    Args:
        a (int): The minimum of the interval.
        b (int): The maximum of the interval.
        n (int): The amount of numbers in simulation. Default to 3.

    Returns:
        int
    """
    if a < b:
        output = np.mean(np.random.randint(a, b, size=n))
        return int(output.round())
    else:
        return b


def random_rectangle_point(area, n=3):
    """Choose a random point in an area.

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        n (int): The amount of numbers in simulation. Default to 3.

    Returns:
        tuple(int): (x, y)
    """
    x = random_normal_distribution_int(area[0], area[2], n=n)
    y = random_normal_distribution_int(area[1], area[3], n=n)
    return x, y


def random_rectangle_vector(vector, box, random_range=(0, 0, 0, 0), padding=15):
    """Place a vector in a box randomly.

    Args:
        vector: (x, y)
        box: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        random_range (tuple): Add a random_range to vector. (x_min, y_min, x_max, y_max).
        padding (int):

    Returns:
        tuple(int), tuple(int): start_point, end_point.
    """
    vector = np.array(vector) + random_rectangle_point(random_range)
    vector = np.round(vector).astype(int)
    half_vector = np.round(vector / 2).astype(int)
    box = np.array(box) + np.append(np.abs(half_vector) + padding, -np.abs(half_vector) - padding)
    center = random_rectangle_point(box)
    start_point = center - half_vector
    end_point = start_point + vector
    return tuple(start_point), tuple(end_point)


def random_rectangle_vector_opted(
        vector, box, random_range=(0, 0, 0, 0), padding=15, whitelist_area=None, blacklist_area=None):
    """
    Place a vector in a box randomly.

    When emulator/game stuck, it treats a swipe as a click, clicking at the end of swipe path.
    To prevent this, random results need to be filtered.

    Args:
        vector: (x, y)
        box: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        random_range (tuple): Add a random_range to vector. (x_min, y_min, x_max, y_max).
        padding (int):
        whitelist_area: (list[tuple[int]]):
            A list of area that safe to click. Swipe path will end there.
        blacklist_area: (list[tuple[int]]):
            If none of the whitelist_area satisfies current vector, blacklist_area will be used.
            Delete random path that ends in any blacklist_area.

    Returns:
        tuple(int), tuple(int): start_point, end_point.
    """
    vector = np.array(vector) + random_rectangle_point(random_range)
    vector = np.round(vector).astype(int)
    half_vector = np.round(vector / 2).astype(int)
    box_pad = np.array(box) + np.append(np.abs(half_vector) + padding, -np.abs(half_vector) - padding)
    box_pad = area_offset(box_pad, half_vector)
    segment = int(np.linalg.norm(vector) // 70) + 1

    def in_blacklist(end):
        if not blacklist_area:
            return False
        for x in range(segment + 1):
            point = - vector * x / segment + end
            for area in blacklist_area:
                if point_in_area(point, area, threshold=0):
                    return True
        return False

    if whitelist_area:
        for area in whitelist_area:
            area = area_limit(area, box_pad)
            if all([x > 0 for x in area_size(area)]):
                end_point = random_rectangle_point(area)
                for _ in range(10):
                    if in_blacklist(end_point):
                        continue
                    return point_limit(end_point - vector, box), point_limit(end_point, box)

    for _ in range(100):
        end_point = random_rectangle_point(box_pad)
        if in_blacklist(end_point):
            continue
        return point_limit(end_point - vector, box), point_limit(end_point, box)

    end_point = random_rectangle_point(box_pad)
    return point_limit(end_point - vector, box), point_limit(end_point, box)


def random_line_segments(p1, p2, n, random_range=(0, 0, 0, 0)):
    """Cut a line into multiple segments.

    Args:
        p1: (x, y).
        p2: (x, y).
        n: Number of slice.
        random_range: Add a random_range to points.

    Returns:
        list[tuple]: [(x0, y0), (x1, y1), (x2, y2)]
    """
    return [tuple((((n - index) * p1 + index * p2) / n).astype(int) + random_rectangle_point(random_range))
            for index in range(0, n + 1)]


def ensure_time(second, n=3, precision=3):
    """Ensure to be time.

    Args:
        second (int, float, tuple): time, such as 10, (10, 30), '10, 30'
        n (int): The amount of numbers in simulation. Default to 5.
        precision (int): Decimals.

    Returns:
        float:
    """
    if isinstance(second, tuple):
        multiply = 10 ** precision
        result = random_normal_distribution_int(second[0] * multiply, second[1] * multiply, n) / multiply
        return round(result, precision)
    elif isinstance(second, str):
        if ',' in second:
            lower, upper = second.replace(' ', '').split(',')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        if '-' in second:
            lower, upper = second.replace(' ', '').split('-')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        else:
            return int(second)
    else:
        return second


def ensure_int(*args):
    """
    Convert all elements to int.
    Return the same structure as nested objects.

    Args:
        *args:

    Returns:
        list:
    """

    def to_int(item):
        try:
            return int(item)
        except TypeError:
            result = [to_int(i) for i in item]
            if len(result) == 1:
                result = result[0]
            return result

    return to_int(args)


def area_offset(area, offset):
    """
    Move an area.

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        offset: (x, y).

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
    """
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    x, y = offset
    return upper_left_x + x, upper_left_y + y, bottom_right_x + x, bottom_right_y + y


def area_pad(area, pad=10):
    """
    Inner offset an area.

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        pad (int):

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
    """
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    return upper_left_x + pad, upper_left_y + pad, bottom_right_x - pad, bottom_right_y - pad


def limit_in(x, lower, upper):
    """
    Limit x within range (lower, upper)

    Args:
        x:
        lower:
        upper:

    Returns:
        int, float:
    """
    return max(min(x, upper), lower)


def area_limit(area1, area2):
    """
    Limit an area in another area.

    Args:
        area1: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        area2: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
    """
    x_lower, y_lower, x_upper, y_upper = area2
    return (
        limit_in(area1[0], x_lower, x_upper),
        limit_in(area1[1], y_lower, y_upper),
        limit_in(area1[2], x_lower, x_upper),
        limit_in(area1[3], y_lower, y_upper),
    )


def area_size(area):
    """
    Area size or shape.

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).

    Returns:
        tuple: (x, y).
    """
    return (
        max(area[2] - area[0], 0),
        max(area[3] - area[1], 0)
    )


def area_center(area):
    """
    Get the center of an area

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)

    Returns:
        tuple: (x, y)
    """
    x1, y1, x2, y2 = area
    return (x1 + x2) / 2, (y1 + y2) / 2


def point_limit(point, area):
    """
    Limit point in an area.

    Args:
        point: (x, y).
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).

    Returns:
        tuple: (x, y).
    """
    return (
        limit_in(point[0], area[0], area[2]),
        limit_in(point[1], area[1], area[3])
    )


def point_in_area(point, area, threshold=5):
    """

    Args:
        point: (x, y).
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        threshold: int

    Returns:
        bool:
    """
    return area[0] - threshold < point[0] < area[2] + threshold and area[1] - threshold < point[1] < area[3] + threshold


def area_in_area(area1, area2, threshold=5):
    """

    Args:
        area1: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        area2: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        threshold: int

    Returns:
        bool:
    """
    return area2[0] - threshold <= area1[0] \
        and area2[1] - threshold <= area1[1] \
        and area1[2] <= area2[2] + threshold \
        and area1[3] <= area2[3] + threshold


def area_cross_area(area1, area2, threshold=5):
    """

    Args:
        area1: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        area2: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
        threshold: int

    Returns:
        bool:
    """
    # https://www.yiiven.cn/rect-is-intersection.html
    xa1, ya1, xa2, ya2 = area1
    xb1, yb1, xb2, yb2 = area2
    return abs(xb2 + xb1 - xa2 - xa1) <= xa2 - xa1 + xb2 - xb1 + threshold * 2 \
        and abs(yb2 + yb1 - ya2 - ya1) <= ya2 - ya1 + yb2 - yb1 + threshold * 2


def float2str(n, decimal=3):
    """
    Args:
        n (float):
        decimal (int):

    Returns:
        str:
    """
    return str(round(n, decimal)).ljust(decimal + 2, "0")


def point2str(x, y, length=4):
    """
    Args:
        x (int, float):
        y (int, float):
        length (int): Align length.

    Returns:
        str: String with numbers right aligned, such as '( 100,  80)'.
    """
    return '(%s, %s)' % (str(int(x)).rjust(length), str(int(y)).rjust(length))


def col2name(col):
    """
    Convert a zero indexed column cell reference to a string.

    Args:
       col: The cell column. Int.

    Returns:
        Column style string.

    Examples:
        0 -> A, 3 -> D, 35 -> AJ, -1 -> -A
    """

    col_neg = col < 0
    if col_neg:
        col_num = -col
    else:
        col_num = col + 1  # Change to 1-index.
    col_str = ''

    while col_num:
        # Set remainder from 1 .. 26
        remainder = col_num % 26

        if remainder == 0:
            remainder = 26

        # Convert the remainder to a character.
        col_letter = chr(remainder + 64)

        # Accumulate the column letters, right to left.
        col_str = col_letter + col_str

        # Get the next order of magnitude.
        col_num = int((col_num - 1) / 26)

    if col_neg:
        return '-' + col_str
    else:
        return col_str


def name2col(col_str):
    """
    Convert a cell reference in A1 notation to a zero indexed row and column.

    Args:
       col_str:  A1 style string.

    Returns:
        row, col: Zero indexed cell row and column indices.
    """
    # Convert base26 column string to number.
    expn = 0
    col = 0
    col_neg = col_str.startswith('-')
    col_str = col_str.strip('-').upper()

    for char in reversed(col_str):
        col += (ord(char) - 64) * (26 ** expn)
        expn += 1

    if col_neg:
        return -col
    else:
        return col - 1  # Convert 1-index to zero-index


def node2location(node):
    """
    See location2node()

    Args:
        node (str): Example: 'E3'

    Returns:
        tuple[int]: Example: (4, 2)
    """
    res = REGEX_NODE.search(node)
    if res:
        x, y = res.group(1), res.group(2)
        y = int(y)
        if y > 0:
            y -= 1
        return name2col(x), y
    else:
        # Whatever
        return ord(node[0]) % 32 - 1, int(node[1:]) - 1


def location2node(location):
    """
    Convert location tuple to an Excel-like cell.
    Accept negative values also.

         -2   -1    0    1    2    3
    -2 -B-2 -A-2  A-2  B-2  C-2  D-2
    -1 -B-1 -A-1  A-1  B-1  C-1  D-1
     0  -B1  -A1   A1   B1   C1   D1
     1  -B2  -A2   A2   B2   C2   D2
     2  -B3  -A3   A3   B3   C3   D3
     3  -B4  -A4   A4   B4   C4   D4

    # To generate the table above
    index = range(-2, 4)
    row = '   ' + ' '.join([str(i).rjust(4) for i in index])
    print(row)
    for y in index:
        row = str(y).rjust(2) + ' ' + ' '.join([location2node((x, y)).rjust(4) for x in index])
        print(row)

    def check(node):
        return point2str(*node2location(location2node(node)), length=2)
    row = '   ' + ' '.join([str(i).rjust(8) for i in index])
    print(row)
    for y in index:
        row = str(y).rjust(2) + ' ' + ' '.join([check((x, y)).rjust(4) for x in index])
        print(row)

    Args:
        location (tuple[int]):

    Returns:
        str:
    """
    x, y = location
    if y >= 0:
        y += 1
    return col2name(x) + str(y)


def load_image(file, area=None):
    """
    Load an image like pillow and drop alpha channel.

    Args:
        file (str):
        area (tuple):

    Returns:
        np.ndarray:
    """
    image = Image.open(file)
    if area is not None:
        image = image.crop(area)
    image = np.array(image)
    channel = image.shape[2] if len(image.shape) > 2 else 1
    if channel > 3:
        image = image[:, :, :3].copy()
    return image


def save_image(image, file):
    """
    Save an image like pillow.

    Args:
        image (np.ndarray):
        file (str):
    """
    # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    # cv2.imwrite(file, image)
    Image.fromarray(image).save(file)


def crop(image, area, copy=True):
    """
    Crop image like pillow, when using opencv / numpy.
    Provides a black background if cropping outside of image.

    Args:
        image (np.ndarray):
        area:
        copy (bool):

    Returns:
        np.ndarray:
    """
    x1, y1, x2, y2 = map(int, map(round, area))
    h, w = image.shape[:2]
    border = np.maximum((0 - y1, y2 - h, 0 - x1, x2 - w), 0)
    x1, y1, x2, y2 = np.maximum((x1, y1, x2, y2), 0)
    image = image[y1:y2, x1:x2]
    if sum(border) > 0:
        image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
    if copy:
        image = image.copy()
    return image


def resize(image, size):
    """
    Resize image like pillow image.resize(), but implement in opencv.
    Pillow uses PIL.Image.NEAREST by default.

    Args:
        image (np.ndarray):
        size: (x, y)

    Returns:
        np.ndarray:
    """
    return cv2.resize(image, size, interpolation=cv2.INTER_NEAREST)


def image_channel(image):
    """
    Args:
        image (np.ndarray):

    Returns:
        int: 0 for grayscale, 3 for RGB.
    """
    return image.shape[2] if len(image.shape) == 3 else 0


def image_size(image):
    """
    Args:
        image (np.ndarray):

    Returns:
        int, int: width, height
    """
    shape = image.shape
    return shape[1], shape[0]


def image_paste(image, background, origin):
    """
    Paste an image on background.
    This method does not return a value, but instead updates the array "background".

    Args:
        image:
        background:
        origin: Upper-left corner, (x, y)
    """
    x, y = origin
    w, h = image_size(image)
    background[y:y + h, x:x + w] = image


def rgb2gray(image):
    """
    gray = ( MAX(r, g, b) + MIN(r, g, b)) / 2

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Shape (height, width)
    """
    # r, g, b = cv2.split(image)
    # return cv2.add(
    #     cv2.multiply(cv2.max(cv2.max(r, g), b), 0.5),
    #     cv2.multiply(cv2.min(cv2.min(r, g), b), 0.5)
    # )
    r, g, b = cv2.split(image)
    maximum = cv2.max(r, g)
    cv2.max(maximum, b, dst=maximum)
    cv2.convertScaleAbs(maximum, alpha=0.5, dst=maximum)
    cv2.min(r, g, dst=r)
    cv2.min(r, b, dst=r)
    cv2.convertScaleAbs(r, alpha=0.5, dst=r)
    # minimum = r
    cv2.add(maximum, r, dst=maximum)
    return maximum


def rgb2hsv(image):
    """
    Convert RGB color space to HSV color space.
    HSV is Hue Saturation Value.

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Hue (0~360), Saturation (0~100), Value (0~100).
    """
    image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(float)
    image *= (360 / 180, 100 / 255, 100 / 255)
    return image


def rgb2yuv(image):
    """
    Convert RGB to YUV color space.

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Shape (height, width)
    """
    image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
    return image


def rgb2luma(image):
    """
    Convert RGB to the Y channel (Luminance) in YUV color space.

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Shape (height, width)
    """
    image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
    luma, _, _ = cv2.split(image)
    return luma


def get_color(image, area):
    """Calculate the average color of a particular area of the image.

    Args:
        image (np.ndarray): Screenshot.
        area (tuple): (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)

    Returns:
        tuple: (r, g, b)
    """
    temp = crop(image, area, copy=False)
    color = cv2.mean(temp)
    return color[:3]


def get_bbox(image, threshold=0):
    """
    A numpy implementation of the getbbox() in pillow.

    Args:
        image (np.ndarray): Screenshot.
        threshold (int): Color <= threshold will be considered black

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
    """
    if image_channel(image) == 3:
        image = np.max(image, axis=2)
    x = np.where(np.max(image, axis=0) > threshold)[0]
    y = np.where(np.max(image, axis=1) > threshold)[0]
    return x[0], y[0], x[-1] + 1, y[-1] + 1


def get_bbox_reversed(image, threshold=0):
    """
    Similar to `get_bbox` but for black contents on white background.

    Args:
        image (np.ndarray): Screenshot.
        threshold (int): Color >= threshold will be considered white

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
    """
    if image_channel(image) == 3:
        image = np.min(image, axis=2)
    x = np.where(np.min(image, axis=0) < threshold)[0]
    y = np.where(np.min(image, axis=1) < threshold)[0]
    return x[0], y[0], x[-1] + 1, y[-1] + 1


def color_similarity(color1, color2):
    """
    Args:
        color1 (tuple): (r, g, b)
        color2 (tuple): (r, g, b)

    Returns:
        int:
    """
    diff = np.array(color1).astype(int) - np.array(color2).astype(int)
    diff = np.max(np.maximum(diff, 0)) - np.min(np.minimum(diff, 0))
    return diff


def color_similar(color1, color2, threshold=10):
    """Consider two colors are similar, if tolerance lesser or equal threshold.
    Tolerance = Max(Positive(difference_rgb)) + Max(- Negative(difference_rgb))
    The same as the tolerance in Photoshop.

    Args:
        color1 (tuple): (r, g, b)
        color2 (tuple): (r, g, b)
        threshold (int): Default to 10.

    Returns:
        bool: True if two colors are similar.
    """
    # print(color1, color2)
    diff = np.array(color1).astype(int) - np.array(color2).astype(int)
    diff = np.max(np.maximum(diff, 0)) - np.min(np.minimum(diff, 0))
    return diff <= threshold


def color_similar_1d(image, color, threshold=10):
    """
    Args:
        image (np.ndarray): 1D array.
        color: (r, g, b)
        threshold(int): Default to 10.

    Returns:
        np.ndarray: bool
    """
    diff = image.astype(int) - color
    diff = np.max(np.maximum(diff, 0), axis=1) - np.min(np.minimum(diff, 0), axis=1)
    return diff <= threshold


def color_similarity_2d(image, color):
    """
    Args:
        image: 2D array.
        color: (r, g, b)

    Returns:
        np.ndarray: uint8
    """
    # r, g, b = cv2.split(cv2.subtract(image, (*color, 0)))
    # positive = cv2.max(cv2.max(r, g), b)
    # r, g, b = cv2.split(cv2.subtract((*color, 0), image))
    # negative = cv2.max(cv2.max(r, g), b)
    # return cv2.subtract(255, cv2.add(positive, negative))
    diff = cv2.subtract(image, (*color, 0))
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    positive = r
    cv2.subtract((*color, 0), image, dst=diff)
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    negative = r
    cv2.add(positive, negative, dst=positive)
    cv2.subtract(255, positive, dst=positive)
    return positive


def extract_letters(image, letter=(255, 255, 255), threshold=128):
    """Set letter color to black, set background color to white.

    Args:
        image: Shape (height, width, channel)
        letter (tuple): Letter RGB.
        threshold (int):

    Returns:
        np.ndarray: Shape (height, width)
    """
    # r, g, b = cv2.split(cv2.subtract(image, (*letter, 0)))
    # positive = cv2.max(cv2.max(r, g), b)
    # r, g, b = cv2.split(cv2.subtract((*letter, 0), image))
    # negative = cv2.max(cv2.max(r, g), b)
    # return cv2.multiply(cv2.add(positive, negative), 255.0 / threshold)
    diff = cv2.subtract(image, (*letter, 0))
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    positive = r
    cv2.subtract((*letter, 0), image, dst=diff)
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    negative = r
    cv2.add(positive, negative, dst=positive)
    cv2.convertScaleAbs(positive, alpha=255.0 / threshold, dst=positive)
    return positive


def extract_white_letters(image, threshold=128):
    """Set letter color to black, set background color to white.
    This function will discourage color pixels (Non-gray pixels)

    Args:
        image: Shape (height, width, channel)
        threshold (int):

    Returns:
        np.ndarray: Shape (height, width)
    """
    # minimum = cv2.min(cv2.min(r, g), b)
    # maximum = cv2.max(cv2.max(r, g), b)
    # return cv2.multiply(cv2.add(maximum, cv2.subtract(maximum, minimum)), 255.0 / threshold)
    r, g, b = cv2.split(cv2.subtract((255, 255, 255, 0), image))
    maximum = cv2.max(r, g)
    cv2.max(maximum, b, dst=maximum)
    cv2.convertScaleAbs(maximum, alpha=0.5, dst=maximum)
    cv2.min(r, g, dst=r)
    cv2.min(r, b, dst=r)
    cv2.convertScaleAbs(r, alpha=0.5, dst=r)
    minimum = r
    cv2.subtract(maximum, minimum, dst=minimum)
    cv2.add(maximum, minimum, dst=maximum)
    cv2.convertScaleAbs(maximum, alpha=255.0 / threshold, dst=maximum)
    return maximum


def color_mapping(image, max_multiply=2):
    """
    Mapping color to 0-255.
    Minimum color to 0, maximum color to 255, multiply colors by 2 at max.

    Args:
        image (np.ndarray):
        max_multiply (int, float):

    Returns:
        np.ndarray:
    """
    image = image.astype(float)
    low, high = np.min(image), np.max(image)
    multiply = min(255 / (high - low), max_multiply)
    add = (255 - multiply * (low + high)) / 2
    # image = cv2.add(cv2.multiply(image, multiply), add)
    cv2.multiply(image, multiply, dst=image)
    cv2.add(image, add, dst=image)
    image[image > 255] = 255
    image[image < 0] = 0
    return image.astype(np.uint8)


def image_left_strip(image, threshold, length):
    """
    In `DAILY:200/200` strip `DAILY:` and leave `200/200`

    Args:
        image (np.ndarray): (height, width)
        threshold (int):
            0-255
            The first column with brightness lower than this
            will be considered as left edge.
        length (int):
            Strip this length of image after the left edge

    Returns:
        np.ndarray:
    """
    brightness = np.mean(image, axis=0)
    match = np.where(brightness < threshold)[0]

    if len(match):
        left = match[0] + length
        total = image.shape[1]
        if left < total:
            image = image[:, left:]
    return image


def red_overlay_transparency(color1, color2, red=247):
    """Calculate the transparency of red overlay.

    Args:
        color1: origin color.
        color2: changed color.
        red(int): red color 0-255. Default to 247.

    Returns:
        float: 0-1
    """
    return (color2[0] - color1[0]) / (red - color1[0])


def color_bar_percentage(image, area, prev_color, reverse=False, starter=0, threshold=30):
    """
    Args:
        image:
        area:
        prev_color:
        reverse: True if bar goes from right to left.
        starter:
        threshold:

    Returns:
        float: 0 to 1.
    """
    image = crop(image, area, copy=False)
    image = image[:, ::-1, :] if reverse else image
    length = image.shape[1]
    prev_index = starter

    for _ in range(1280):
        bar = color_similarity_2d(image, color=prev_color)
        index = np.where(np.any(bar > 255 - threshold, axis=0))[0]
        if not index.size:
            return prev_index / length
        else:
            index = index[-1]
        if index <= prev_index:
            return index / length
        prev_index = index

        prev_row = bar[:, prev_index] > 255 - threshold
        if not prev_row.size:
            return prev_index / length
        prev_color = np.mean(image[:, prev_index], axis=0)

    return 0.

def str2int(ss):
    neg_mul = 1
    if ss.strip().startswith('-'):
        neg_mul = -1
    try:
        return int("".join([n for n in ss if n.isdigit()])) * neg_mul
    except ValueError:
        return None

def check_connection(addr, timeout:float=3):
    """
    Check if a port is available on the given IP address.

    Args:
        addr (str): The address to check, in the format "ip:port".

    Returns:
        bool: True if the port is available, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        ip, port = addr.split(':')
        result = sock.connect_ex((ip, int(port)))
        return result == 0

def get_lnk_dest(file):
    try:
        with open(file, 'rb') as stream:
            content = stream.read()
        # skip first 20 bytes (HeaderSize and LinkCLSID)
        # read the LinkFlags structure (4 bytes)
        lflags = struct.unpack('I', content[0x14:0x18])[0]
        position = 0x18
        # if the HasLinkTargetIDList bit is set then skip the stored IDList 
        # structure and header
        if (lflags & 0x01) == 1:
            position = struct.unpack('H', content[0x4C:0x4E])[0] + 0x4E
        last_pos = position
        position += 0x04
        # get how long the file information is (LinkInfoSize)
        length = struct.unpack('I', content[last_pos:position])[0]
        # skip 12 bytes (LinkInfoHeaderSize, LinkInfoFlags, and VolumeIDOffset)
        position += 0x0C
        # go to the LocalBasePath position
        lbpos = struct.unpack('I', content[position:position+0x04])[0]
        position = last_pos + lbpos
        # read the string at the given position of the determined length
        size= (length + last_pos) - position - 0x02
        temp = struct.unpack('c' * size, content[position:position+size])
        return ''.join([chr(ord(a)) for a in temp])
    except Exception as e:
        print(f"Error reading {file}: {e}")
        return None

def get_start_menu_programs(filter:str=''):
    path = Path(os.getenv('PROGRAMDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
    return [get_lnk_dest(p) for p in path.glob('**/*.lnk') if p.is_file() and filter.lower() in p.name.lower()]

import psutil, time, subprocess, platform

def pids_listening_on(port: int, proto: str = "tcp") -> set[int]:
    """
    Return PIDs that have a LISTEN socket on the given port.
    Requires sufficient privileges to see other users' sockets.
    """
    proto = proto.lower()
    kinds = {
        "tcp": ("tcp", "tcp4", "tcp6"),
        "udp": ("udp", "udp4", "udp6"),
    }[proto]

    pids = set()
    for kind in kinds:
        try:
            for c in psutil.net_connections(kind=kind):
                if c.laddr and c.laddr.port == port:
                    # tcp: only kill listeners by default
                    if proto == "tcp":
                        if getattr(c, "status", None) in ("LISTEN", "LISTENING", None):
                            if c.pid:
                                pids.add(c.pid)
                    else:
                        # udp has no LISTEN state
                        if c.pid:
                            pids.add(c.pid)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return pids

def kill_process_tree(pid: int, grace: float = 5.0) -> None:
    """Terminate a process and its children; escalate to kill after a grace period."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    children = proc.children(recursive=True)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    try:
        proc.terminate()
    except psutil.NoSuchProcess:
        pass

    gone, alive = psutil.wait_procs(children + [proc], timeout=grace)
    for p in alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass

def kill_by_port(port: int, proto: str = "tcp", grace: float = 5.0) -> list[int]:
    """
    Find processes listening on `port` and kill their trees.
    Returns list of PIDs targeted. Falls back to OS tools if psutil can’t see them.
    """
    pids = pids_listening_on(port, proto=proto)

    # Fallbacks if nothing found (limited privileges):
    if not pids:
        system = platform.system()
        try:
            if system == "Windows":
                # netstat -ano | findstr :<port>
                out = subprocess.check_output(
                    ["netstat", "-ano"], text=True, errors="ignore"
                )
                for line in out.splitlines():
                    if f":{port} " in line and "LISTEN" in line.upper():
                        parts = line.split()
                        pid = int(parts[-1])
                        pids.add(pid)
            else:
                # lsof -iTCP:<port> -sTCP:LISTEN -t
                out = subprocess.check_output(
                    ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                    text=True, errors="ignore"
                )
                for line in out.split():
                    pids.add(int(line.strip()))
        except Exception:
            pass
    for pid in list(pids):
        kill_process_tree(pid, grace=grace)
    return sorted(pids)

def get_all_instance_addresses() -> dict[str, str]:
    files = glob('./config/*.json')
    ret = {}
    for file in files:
        if 'template' in file:
            continue
        fp = None
        depth = 0
        while not fp:
            try:
                fp = open(file, 'r')
            except Exception as e:
                print(f'Error opening {file}: e')
                depth += 1
                if depth > 30:
                    print('Wait limit excessed, given up')
                    break
                time.sleep(1)
        if not fp:
            continue
        try:
            data = json.load(fp)
        finally:
            fp.close()
        try:
            addr = data['Alas']['Playwright']['RemoteDebuggingAddress']
        except KeyError:
            continue
        ret[Path(file).stem] = addr
    return ret

def kill_remote_browser(config_name) -> list[int]:
    config = {}
    with open(f'config/{config_name}.json', 'r') as fp:
        config = json.load(fp)
    addr = config.get('Alas', {}).get('Playwright', {}).get('RemoteDebuggingAddress', '')
    if not addr:
        return []
    return kill_by_port(int(addr.split(':')[-1]))

def _lcs2(a: str, b: str) -> str:
    """Longest common substring (contiguous) between two strings."""
    if not a or not b:
        return ""
    n, m = len(a), len(b)
    dp = [0] * (m + 1)
    best_len = 0
    best_end = 0  # end index in 'a' (exclusive)
    for i in range(1, n + 1):
        prev = 0
        for j in range(1, m + 1):
            tmp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
                if dp[j] > best_len:
                    best_len = dp[j]
                    best_end = i
            else:
                dp[j] = 0
            prev = tmp
    return a[best_end - best_len:best_end]

def lcs(strings) -> str:
    """LCS across many strings via pairwise reduction"""
    it = iter(strings)
    try:
        acc = next(it)
    except StopIteration:
        return ""
    for s in it:
        acc = _lcs2(acc, s)
        if not acc:
            break
    return acc

def lcs_enum(items, min_len=3, include_singletons=True):
    """
    Enumerate common tokens by pairwise LCS.
    - Always returns tokens that occur in >=2 items.
    - If include_singletons=True, also includes each item's best word (count may be 1).
    Sorted by: frequency desc, length desc, lexicographic.
    """
    word_pat = re.compile(rf'\b[0-9A-Za-z]{{{min_len},}}\b')
    candidate_words = set()
    for a, b in combinations(items, 2):
        s = _lcs2(a, b)
        for w in word_pat.findall(s):
            candidate_words.add(w)

    def count_occurrences(token: str) -> int:
        pat = re.compile(rf'\b{re.escape(token)}\b')
        return sum(1 for name in items if pat.search(name))

    counts = {w: count_occurrences(w) for w in candidate_words}
    scored = [(c, len(w), w) for w, c in counts.items() if c >= 2]
    if include_singletons:
        def best_word(name: str) -> str:
            cands = word_pat.findall(name)
            if not cands:
                return ""
            cands.sort(key=lambda x: (-len(x), x))
            return cands[0]
        for name in items:
            tok = best_word(name)
            if not tok:
                continue
            c = count_occurrences(tok)  # may be 1
            scored.append((c, len(tok), tok))
    best = {}
    for c, L, w in scored:
        if w not in best or (c, L) > (best[w][0], best[w][1]):
            best[w] = (c, L, w)
    ordered = sorted(best.values(), key=lambda t: (-t[0], -t[1], t[2]))
    return [w for _, _, w in ordered]

def _shingles(s: str, k: int = 3) -> set:
    s = s.lower()
    return {s[i:i+k] for i in range(max(0, len(s)-k+1))} if s else set()

def jaccard_sim(a: str, b: str, k: int = 3) -> float:
    A, B = _shingles(a, k), _shingles(b, k)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0

def group_by_similarity(items, sim_threshold: float = 0.55, k: int = 3):
    """
    Greedy single-linkage clustering:
    put an item into the group where it has the highest max-sim to any member,
    if that similarity >= threshold; otherwise start a new group.
    """
    groups: list[list[str]] = []
    for name in items:
        best_idx, best_sim = -1, 0.0
        for idx, grp in enumerate(groups):
            # single-linkage: compare against the *closest* member in the group
            s = max(jaccard_sim(name, g, k) for g in grp)
            if s > best_sim:
                best_sim, best_idx = s, idx
        if best_sim >= sim_threshold:
            groups[best_idx].append(name)
        else:
            groups.append([name])
    return groups

_word_pat = re.compile(r"\b[0-9A-Za-z]{3,}\b")

def _best_word_in(s: str, min_len: int = 3) -> str:
    """
    From a substring (which may include spaces), pick the longest single word
    of length >= min_len. Returns '' if none.
    """
    cands = _word_pat.findall(s)
    if not cands:
        return ""
    cands.sort(key=lambda w: (-len(w), w))
    return cands[0] if len(cands[0]) >= min_len else ""

def cluster_lcs(
        items: list[str],
        sim_threshold: float = 0.2,
        k: int = 3,
        min_len: int = 3,
        include_singletons: bool = True
    ) -> list[str]:
    """
    1) Cluster names by Jaccard similarity on 3-grams.
    2) For each cluster (size>=2), compute LCS across members.
    3) Snap LCS to a single 'word' token and keep those that appear in >=2 items.
    4) Deduplicate results and sort by (cluster size desc, token length desc, lex).
    """
    groups = group_by_similarity(items, sim_threshold=sim_threshold, k=k)

    results = []
    for grp in groups:
        if len(grp) >= 2:
            raw = lcs(grp)
            token = _best_word_in(raw, min_len=min_len)
            if not token:
                continue
            pat = re.compile(rf"\b{re.escape(token)}\b")
            count = sum(1 for name in grp if pat.search(name))
            if count >= 2:
                results.append((len(grp), len(token), token))
        elif include_singletons and len(grp) == 1:
            name = grp[0]
            token = _best_word_in(name, min_len=min_len)
            if not token:
                token = name.strip()  # fallback if no >=min_len word token
            if token:
                results.append((1, len(token), token))

    # Dedupe by token (keep the best-scoring tuple)
    best = {}
    for size, tlen, tok in results:
        if tok not in best or (size, tlen) > (best[tok][0], best[tok][1]):
            best[tok] = (size, tlen, tok)

    ordered = sorted(best.values(), key=lambda x: (-x[0], -x[1], x[2]))
    return [tok for _, _, tok in ordered]

def lcs_multi(
    items, min_len=3, sim_threshold=0.2,
    k=3, include_singletons=True
    ) -> list[str]:
    '''
    Find the longest common substrings (LCS) across multiple strings.
    Has 2 modes and some args will only apply to one of them. (see code for details)
    Used to optimize searches for similar names in a list of items.

    Args:
        items (list[str]): List of strings to find LCS in.
        min_len (int): Minimum length of the substring to consider.
        sim_threshold (float): Jaccard similarity threshold for clustering.
        k (int): Size of the n-grams for Jaccard similarity.
        include_singletons (bool): If True, include single items as results.

    Returns:
        list[str]: List of longest common substrings found in the items.
    '''
    n = len(items)
    if n == 0:
        return []

    avg_len = max(1, sum(len(s) for s in items) // n)

    N_star = 12
    if avg_len >= 20:   # long names
        N_star = 4
    if avg_len >= 12:   # medium
        N_star = 6
    if avg_len >= 6:    # short-ish
        N_star = 8

    if n <= N_star:
        # Small n -> Pairwise-LCS (simpler; lower constant cost)
        return lcs_enum(items, min_len=min_len, include_singletons=include_singletons)
    else:
        # Larger n -> Cluster->LCS (better asymptotics)
        return cluster_lcs(
            items, sim_threshold=sim_threshold, k=k,
            min_len=min_len, include_singletons=include_singletons
        )
