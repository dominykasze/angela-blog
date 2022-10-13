from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask import abort
from functools import wraps


# Creating a decorator function. A decorator is a function that wraps and replaces another function.
# Since the original function is replaced, you need to remember to copy the original function’s information
# to the new function. This can be done wraps from functools

def admin_only(function):
    # Copying the original functions information to the new function
    @wraps(function)
    # Creating a new, decorated function
    def decorated_function(*args, **kwargs):
        # if current_user:
        # Which checks if the current user id is equal to 1
        if current_user.id == 1:
            # And if it is, the decorated function runs the original function
            return function(*args, **kwargs)
        # Otherwise, it runs the abort function which renders an error on screen
        return abort(403)
    return decorated_function

# def admin_only(function):
#     def wrapper_function():
#         if current_user.id == 1:
#             return function()
#         return abort()
#     return wrapper_function()

