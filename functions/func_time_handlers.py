import re

import func_errors

TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([mhdw])")
TIME_DICT = {"h": 60, "m": 1, "d": 1440, "w": 10080}


def time_converter(input_time: str) -> int:
    # time_converter: Converts arguments to minutes
    if not input_time.__contains__("m") and not input_time.__contains__("h") and not input_time.__contains__("d") \
            and not input_time.__contains__("w"):
        raise func_errors.WrongDateFormat(
            "Please make sure you have followed the correct date format:"
            "\nw -> Week\nd -> Day\nh -> Hours\nm -> Minutes")
    else:
        matches = TIME_REGEX.findall(input_time.lower())
        time = 0
        for value, list_index in matches:
            try:
                time += TIME_DICT[list_index] * float(value)
            except KeyError:
                raise func_errors.WrongDateFormat(
                    "Please make sure you have followed the correct date format:"
                    "\nw -> Week\nd -> Day\nh -> Hours\nm -> Minutes")
            except ValueError:
                raise func_errors.WrongDateFormat(
                    "Please make sure you have followed the correct date format:"
                    "\nw -> Week\nd -> Day\nh -> Hours\nm -> Minutes")
        return time


