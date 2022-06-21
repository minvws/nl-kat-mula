import functools

import pydantic


class ValidationError(Exception):
    pass


def exception_handler(func):
    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pydantic.error_wrappers.ValidationError as e:
            raise ValidationError("Not able to parse response from external service.")

    return inner_function
