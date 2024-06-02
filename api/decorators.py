def prefixed_key(f):
    """
    Prefixes the string that the decorated method `f` returns with 
    the value of the `prefix` attribute on the owner object `self`.
    """
    def prefixed_method(*args, **kwargs):
        self = args[0]
        key = f(*args, **kwargs)
        return f'{self.prefix}:{key}'

    return prefixed_method
