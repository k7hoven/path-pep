PEP: NNN
Title: Adding a file system path protocol
Version: $Revision$
Last-Modified: $Date$
Author: Brett Cannon <brett@python.org>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: DD-Mmm-2016
Post-History: DD-Mmm-2016


Abstract
========

This PEP proposes a protocol for classes which represent a file system
path to be able to provide a path in a lower-level
representation/encoding. Changes to Python's standard library are also
proposed to utilize this protocol where appropriate to facilitate the
use of path objects where historically only ``str`` and/or
``bytes`` file system paths are accepted. The goal is to allow users
to use the representation of a file system path that's easiest for
them now as they migrate towards using path objects in the future.


Rationale
=========

Historically in Python, file system paths have been represented as 
strings or bytes. This choice of representation has stemmed from C's 
own decision to represent file system paths as ``const char *`` 
[#libc-open]_. While that is a totally serviceable format to use for 
file system paths, it's not necessarily optimal. At issue is the fact 
that while all file system paths can be represented as strings or 
bytes, not all strings or bytes are meant to represent a file system 
path; having a format and structure to file system paths makes their 
string/bytes representation act as a serialization or encoding. By the 
introduction of ``os.scandir`` in the standard library in Python 3.5, 
there are now also ``DirEntry`` objects which are more 
performance-oriented, but have an interface large compatible with 
pathlib objects.

To help elevate the representation of file system paths from their 
encoding as strings and bytes to a more appropriate object 
representation, the pathlib module [#pathlib]_ was provisionally 
introduced in Python 3.4 through PEP 428. While considered by some as 
an improvement over strings and bytes for file system paths, it has 
suffered from a lack of adoption. Typically the key issue mentioned 
for the low adoption rate has been the lack of support in the standard 
library. This is related to the frequent need of converting path 
objects to and from strings and the difficulty of safely extracting 
the string or bytes representation of the path from a 
``pathlib.PurePath`` or ``DirEntry`` object for use in APIs that don't 
support such objects natively.

The lack of support in the standard library has, on the one hand, 
stemmed from the fact that the pathlib module was provisional. On the 
other hand, the acceptance of this PEP will lead to wide pathlib 
support in the standard library, making way for the removal of the 
module's provisional status. This PEP is also expected to lead to 
pathlib support in third-party modules.

One issue in converting path objects to strings comes from the fact 
that the only way to get a string representation of the path was to 
pass the object to ``str()``. This can pose a problem when done 
blindly as nearly all Python objects have some string representation 
whether they are a path or not, e.g. ``str(None)`` will give a result 
that ``builtins.open()`` [#builtins-open]_ will happily use to create 
a new file.

This PEP then proposes to introduce a new protocol to be followed by 
objects which represent file system paths. Providing a protocol and 
associated type hinting tools allows for clear signalling of what 
objects represent file system paths as well as a function to extract a 
lower-level encoding. This function can be used together with 
older APIs which only support strings or bytes, or be used at the 
interface within newer versions of such APIs.

Discussions regarding path objects that led to this PEP can be found
in multiple threads on the python-ideas mailing list archive
[#python-ideas-archive]_ for the months of March and April 2016 and on
the python-dev mailing list archives [#python-dev-archive]_ during
April 2016.


Proposal
========

This proposal is split into two parts. One part is the proposal of a
protocol for objects to declare and provide support for exposing a
file system path representation. The other part is changes to Python's
standard library to support the new protocol. These changes will also
allow for the pathlib module to drop its provisional status.


Protocol
--------

The following abstract base class defines the protocol for an object
to be considered a path object::

    import abc
    import typing as t


    class PathLike(abc.ABC):

        """Abstract base class for implementing the file system path protocol."""

        @abc.abstractmethod
        def __fspath__(self) -> t.Union[str, bytes]:
            """Return the file system path representation of the object."""
            raise NotImplementedError


Objects representing file system paths will implement the
``__fspath__()`` method which will return the ``str`` or ``bytes``
representation of the path. If the file system path is already
properly encoded as ``bytes`` then that should be returned, otherwise
a ``str`` should be returned as the preferred path representation.


Standard library changes
------------------------

It is expected that most APIs in Python's standard library that
currently accept a file system path will be updated appropriately to
accept path objects (whether that requires code or simply an update
to documentation will vary). The modules mentioned below, though,
deserve specific details as they have either fundamental changes that
empower the ability to use path objects, or entail additions/removal
of APIs.


builtins
''''''''

``open()`` [#builtins-open]_ will be updated to accept path objects.


os
'''

The ``fspath()`` function will be added with the following semantics::

    import typing as t


    def fspath(path: t.Union[PathLike, str]) -> str:
        """Return the string representation of the path.

        If a string is passed in then it is returned unchanged.
        """
        if hasattr(path, '__fspath__'):
            path = path.__fspath__()
        if not isinstance(path, str):
            type_name = type(path).__name__
            raise TypeError("expected a str or path object, not " + type_name)
        return path

The ``os.fsencode()`` [#os-fsencode]_ and
``os.fsdecode()`` [#os-fsdecode]_ functions will be updated to accept
path objects. As both functions coerce their arguments to
``bytes`` and ``str``, respectively, they will be updated to call
``__fspath__()`` as necessary and then peform their appropriate
coercion operations as if the return value from ``__fspath__()`` had
been the original argument to the coercion function in question.

The addition of ``os.fspath()``, the updates to
``os.fsencode()``/``os.fsdecode()``, and the current semantics of
``pathlib.PurePath`` provide the semantics necessary to
get the path representation one prefers. For a path object,
``pathlib.PurePath``/``Path`` can be used. If ``str`` is desired and
no guesses about ``bytes`` encodings is desired to decode to a
``str``, then ``os.fspath()`` can be used. If a ``str`` is desired and
the encoding of ``bytes`` should be assumed to be the default file
system encoding, then ``os.fsdecode()`` should be used. Finally, if a
``bytes`` representation is desired and any strings should be encoded
using the default file system encoding then ``os.fsencode()`` is used.
No function is provided for the case of wanting a ``bytes``
representation but without any automatic encoding to help discourage
the use of multiple ``bytes`` encodings on a single file system. This
PEP recommends using path objects when possible and falling back to
string paths as necessary.

Another way to view this is as a hierarchy of file system path
representations (highest- to lowest-level): path -> str -> bytes. The
functions and classes under discussion can all accept objects on the
same level of the hierarchy, but they vary in whether they promote or
demote objects to another level. The ``pathlib.PurePath`` class can
promote a ``str`` to a path object. The ``os.fspath()`` function can
demote a path object to a string, but only if ``__fspath__()`` returns
a string. The ``os.fsdecode()`` function will demote a path object to
a string or promote a ``bytes`` object to a ``str``. The
``os.fsencode()`` function will demote a path or string object to
``bytes``. There is no function that provides a way to demote a path
object directly to ``bytes`` and not allow demoting strings.

The ``DirEntry`` object [#os-direntry]_ will gain an ``__fspath__()``
method. It will return the value currently found on the ``path``
attribute of ``DirEntry`` instances.


os.path
'''''''

The various path-manipulation functions of ``os.path`` [#os-path]_
will be updated to accept path objects. For polymorphic functions that
accept both bytes and strings, they will be updated to simply use
code very much similar to
``path.__fspath__() if  hasattr(path, '__fspath__') else path``. This
will allow for their pre-existing type-checking code to continue to
function.

During the discussions leading up to this PEP it was suggested that
``os.path`` not be updated using an "explicit is better than implicit"
argument. The thinking was that since ``__fspath__()`` is polymorphic
itself it may be better to have code explicitly request that working
with ``os.path`` extract the path representation from path objects
explicitly. There is also the consideration that adding support this
deep into the low-level OS APIs will lead to code magically supporting
path objects without requiring any documentation updated, leading to
potential complaints when it doesn't work, unbeknownst to the project
author.

But it is the view of the authors that "practicality beats purity" in
this instance. To help facilitate the transition to supporting path
objects, it is better to make the transition as easy as possible than
to worry about unexpected/undocumented duck typing support for
projects.


pathlib
'''''''

The ``PathLike`` ABC as discussed in the Protocol_ section will be
added to the pathlib module [#pathlib]_. The constructor for
``pathlib.PurePath`` and ``pathlib.Path`` will be updated to accept
path objects. Both ``PurePath`` and ``Path`` will continue to not
accept ``bytes`` path representations, and so if ``__fspath__()``
returns ``bytes`` it will raise an exception.

The ``path`` attribute which has yet to be included in a release of
Python will be removed as this PEP makes its usefulness redundant.

The ``open()`` method on ``Path`` objects will be removed. As
``builtins.open()`` [#builtins-open]_ will be updated to accept path
objects, the ``open()`` method becomes redundant.


C API
'''''

The C API will gain an equivalent function to ``os.fspath()`` that
also allows bytes objects through::

    /*
        Return the file system path of the object.

        If the object is str or bytes, then allow it to pass through with
        an incremented refcount. All other types raise a TypeError.
    */
    PyObject *
    PyOS_RawFSPath(PyObject *path)
    {
        if (PyObject_HasAttrString(path, "__fspath__")) {
            path = PyObject_CallMethodObjArgs(path, "__fspath__", NULL);
            if (path == NULL) {
                return NULL;
            }
        }
        else {
            Py_INCREF(path);
        }

        if (!PyUnicode_Check(path) && !PyBytes_Check(path)) {
            Py_DECREF(path);
            return PyErr_Format(PyExc_TypeError,
                                "expected a string, bytes, or path object, not %S",
                                path->ob_type);
        }

        return path;
}


Backwards compatibility
=======================

From the perspective of Python, the only breakage of compatibility
will come from the removal of ``pathlib.Path.open()``. But since
the pathlib module [#pathlib]_ has been provisional until this PEP,
its removal does not break any backwards-compatibility guarantees.
Users of the method can update their code to either call ``str(path)``
on their ``Path`` objects, or they can choose to rely on the
``__fspath__()`` protocol existing in newer releases of Python 3.4,
3.5, and 3.6. In that instance they can use the idiom of
``path.__fspath__() if hasattr(path, '__fspath__') else path`` to get
the path representation from a path object if provided, else use the
provided object as-is.


Open Issues
===========

The name and location of the protocol's ABC
-------------------------------------------

The name of the ABC being proposed to represent the protocol has not
been discussed very much. Another viable name is ``pathlib.PathABC``.
The name can't be ``pathlib.Path`` as that already exists.

It's also an open issue as to whether the ABC belongs in the pathlib,
os, or os.path module.


Type hint for path-like objects
-------------------------------

Creating a proper type hint for  APIs that accept path objects as well
as strings and bytes will probably be needed. It could be as simple
as defining ``typing.Path`` and then having
``typing.PathLike = typing.Union[typing.Path, str, bytes]``, but it
should be properly discussed with the right type hinting experts if
this is the best approach.


Rejected Ideas
==============

Other names for the protocol's function
---------------------------------------

Various names were proposed during discussions leading to this PEP,
including ``__path__``, ``__pathname__``, and ``__fspathname__``. In
the end people seemed to gravitate towards ``__fspath__`` for being
unambiguous without unnecessarily long.


Separate str/bytes methods
--------------------------

At one point it was suggested that ``__fspath__()`` only return
strings and another method named ``__fspathb__()`` be introduced to
return bytes. The thinking that by making ``__fspath__()`` not be
polymorphic it could make dealing with the potential string or bytes
representations easier. But the general consensus was that returning
bytes will more than likely be rare and that the various functions in
the os module are the better abstraction to be promoting over direct
calls to ``__fspath__()``.


Providing a path attribute
--------------------------

To help deal with the issue of ``pathlib.PurePath`` no inheriting from
``str``, originally it was proposed to introduce a ``path`` attribute
to mirror what ``os.DirEntry`` provides. In the end, though, it was
determined that a protocol would provide the same result while not
directly exposing an API that most people will never need to interact
with directly.


Have ``__fspath__()`` only return strings
------------------------------------------

Much of the discussion that led to this PEP revolved around whether
``__fspath__()`` should be polymorphic and return ``bytes`` as well as
``str`` instead of only ``str``. The general sentiment for this view
was that because ``bytes`` are difficult to work with due to their
inherit lack of information of their encoding, it would be better to
forcibly promote the use of ``str`` as the low-level path
representation.

In the end it was decided that using ``bytes`` to represent paths is
simply not going to go away and thus they should be supported to some
degree. For those not wanting the hassle of working with ``bytes``,
``os.fspath()`` is provided.


A generic string encoding mechanism
-----------------------------------

At one point there was discussion of developing a generic mechanism to
extract a string representation of an object that had semantic meaning
(``__str__()`` does not necessarily return anything of semantic
significance beyond what may be helpful for debugging). In the end it
was deemed to lack a motivating need beyond the one this PEP is
trying to solve in a specific fashion.


References
==========

.. [#python-ideas-archive] The python-ideas mailing list archive
   (https://mail.python.org/pipermail/python-ideas/)

.. [#python-dev-archive] The python-dev mailing list archive
   (https://mail.python.org/pipermail/python-dev/)

.. [#libc-open] ``open()`` documention for the C standard library
   (http://www.gnu.org/software/libc/manual/html_node/Opening-and-Closing-Files.html)

.. [#pathlib] The ``pathlib`` module
   (https://docs.python.org/3/library/pathlib.html#module-pathlib)

.. [#builtins-open] The ``builtins.open()`` function
   (https://docs.python.org/3/library/functions.html#open)

.. [#os-fsencode] The ``os.fsencode()`` function
   (https://docs.python.org/3/library/os.html#os.fsencode)

.. [#os-fsdecode] The ``os.fsdecode()`` function
   (https://docs.python.org/3/library/os.html#os.fsdecode)

.. [#os-direntry] The ``os.DirEntry`` class
   (https://docs.python.org/3/library/os.html#os.DirEntry)

.. [#os-path] The ``os.path`` module
   (https://docs.python.org/3/library/os.path.html#module-os.path)


Copyright
=========

This document has been placed in the public domain.



..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:
