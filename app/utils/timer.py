from func_timeout import FunctionTimedOut, func_timeout


# Wrapper function to handle timeout
def timeout_handler(default_value, timeout, func, *args, **kwargs):
    try:
        result = func_timeout(timeout, func, args=args, kwargs=kwargs)
    except FunctionTimedOut:
        print("⏲️ Function timed out!\n")
        result = default_value
    return result
