def handle_sensitive_image(image):
    """
    Args:
        image:

    Returns:
        np.ndarray:
    """
    # Paint UID to black
    try:
        image[680:720, 0:180, :] = 0
    except Exception as e:
        print(f"Error handling sensitive image: {e}")
    return image


def handle_sensitive_logs(logs):
    return logs
