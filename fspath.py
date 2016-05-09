import abc

class FSPathABC(abc.ABC):

    """Abstract base class for implementing the file system path protocol."""

    @abc.abstractmethod
    def __fspath__(self):
        """Return the file system path representation of the object."""
        raise NotImplementedError


def fspath(path, *, type_constraint = str):
    """Return the string representation of the path.

    If a string is passed in, it is returned unchanged. 
    Otherwise, the __fspath__ method will be invoked to provide 
    a string or byte string representation. The return
    value (pathstring) will satisfy the requirement 

        isinstance(pathstring, type_constraint)

    or otherwise an exception is raised.
    """
    if isinstance(path, type_constraint):
        return path
    if hasattr(path, '__fspath__'):
        pathstring = path.__fspath__()
    else:
        raise TypeError("path must implement __fspath__() or be an instance of type_constraint")
    if not isinstance(pathstring, type_constraint):
        type_name = type(pathstring).__name__
        raise TypeError("__fspath__() must return a str or bytes, not " + type_name)
    return pathstring
