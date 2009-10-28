# -*- coding: utf-8 -*-

import operator

from .odict import odict

import pygccxml.declarations

def format_tag(something):
    """
        if *something* is None, return "!None". Otherwise,
        return *something*.
    """
    if something is None:
        return '!None'
    else:
        return something

def format_coord(coord):
    if coord is not None:
        return {'file': coord.file_name, 'line': coord.line}
    else:
        return None

def format_type(type, objects):
    return type

class Object(object):
    def __init__(self, coord, tag):
        self.coord = coord
        self.tag = tag

    def __repr__(self):
        return '<%s at 0x%x "%s">' % (
                self.__class__.__name__,
                id(self),
                self.tag)

    def get_state(self, objects):
        return {'coord': self.coord,
                'tag': self.tag,
                'class': self.__class__.__name__
                }

class Type(Object):
    pass

class Typedef(Object):
    def __init__(self, coord, tag, target):
        Object.__init__(self, coord, tag)
        self.target = target

    def get_state(self, objects):
        state = Object.get_state(self, objects)
        state.update({
            'target': format_type(self.target, objects)
            })
        return state

class Array(Object):
    def __init__(self, coord, type, size=None):
        tag = 'ARRAY(%s, %s)' % (type.tag, format_tag(size))
        Object.__init__(self, coord, tag)
        self.type = type
        self.size = size

    def get_state(self, objects):
        state = Object.get_state(self, objects)
        state.update({
            'type': format_type(self.type, objects),
            'size': self.size
            })
        return state

class PrimitiveType(Type):
    pass

class Compound(Type):
    modifier = '%s'

    def __init__(self, coord, name, members=()):
        Type.__init__(self, coord, type(self).modifier % format_tag(name))
        self.name = name
        self.members = odict()
        self.add_members(members)

    def add_members(self, members):
        if not members:
            return
        if not isinstance(members, odict):
            members = odict(members)
        self.members.update(members)

    def add_member(self, name, type):
        self.members[name] = type

    def get_state(self, objects):
        state = Type.get_state(self, objects)
        state.update({
            'name': self.name,
            'members': [(name, format_type(typ, objects))
                for name, typ in self.members.iteritems()
                ]
            })
        return state

class Struct(Compound):
    modifier = 'STRUCT(%s)'

    def add_member(self, name, type, bitsize):
        self.members[name] = (type, bitsize)

    def get_state(self, objects):
        state = Type.get_state(self, objects)
        state.update({
            'name': self.name,
            'members': [(name, typ, bitsize)
                for name, (typ, bitsize) in self.members.iteritems()
                ]
            })
        return state

class Enum(Compound):
    modifier = 'ENUM(%s)'

    def add_member(self, name, value):
        self.members[name] = value

    def get_state(self, objects):
        state = Type.get_state(self, objects)
        state.update({
            'name': self.name,
            'members': self.members.items()
            })
        return state

class Union(Compound):
    modifier = 'UNION(%s)'

class Pointer(Type):
    def __init__(self, coord, type):
        Type.__init__(self, coord, 'POINTER(%s)' % format_tag(type.tag))
        self.type = type

    def get_state(self, objects):
        state = Type.get_state(self, objects)
        state.update({
            'type': format_type(self.type, objects)
            })
        return state

class Function(Object):
    def __init__(self, coord, name, rettype, arguments, varargs=False, storage=None):
        Object.__init__(self, coord, format_tag(name))
        if storage is None:
            storage = []
        self.name = name
        self.rettype = rettype
        self.arguments = arguments
        self.varargs = varargs
        self.storage = storage

    def get_state(self, objects):
        state = Object.get_state(self, objects)
        # only include arguments that are not well-known,
        # otherwise just use the tag as value.
        arguments = []
        for name, type in self.arguments.iteritems():
            arguments.append((name, format_type(type, objects)))
        # same for rettype
        rettype = format_type(self.rettype, objects)
        state.update({
            'name': self.name,
            'rettype': rettype,
            'arguments': arguments,
            'varargs': self.varargs,
            'storage': self.storage,
            })
        return state

class FunctionType(Object):
    def __init__(self, coord, rettype, argtypes, varargs=False):
        # construct the tag
        tag = 'FUNCTIONTYPE(%s)' % (', '.join(a.tag for a in ([rettype] + argtypes)))

        Object.__init__(self, coord, tag)
        self.rettype = rettype
        self.argtypes = argtypes
        self.varargs = varargs

    def get_state(self, objects):
        state = Object.get_state(self, objects)
        # only include argtypes that are not well-known,
        # otherwise just use the tag as value.
        argtypes = []
        for type in self.argtypes:
            argtypes.append(format_type(type, objects))
        # same for rettype
        rettype = format_type(self.rettype, objects)
        state.update({
            'rettype': rettype,
            'argtypes': argtypes,
            'varargs': self.varargs
            })
        return state

TYPES = ('void',
         'signed char',
         'unsigned char',
         'signed byte',
         'unsigned byte',
         'signed short',
         'unsigned short',
         'signed int',
         'unsigned int',
         'signed long',
         'unsigned long',
         'long long',
         'unsigned long long',
         'float',
         'double',
         'long double',
         )

SYNONYMS = {
        'char': 'signed char',
        'byte': 'signed byte',
        'short': 'signed short',
        'int': 'signed int',
        'unsigned': 'int',

        'long': 'signed long',
        'long int': 'signed long',
        'unsigned long int': 'unsigned long',

        'long long int': 'long long',
        'signed long long int': 'long long',
        'unsigned long long int': 'unsigned long long',

        'short int': 'short',
        'signed short int': 'short',
        'unsigned short int': 'unsigned short',
        }

def _get_builtins():
    d = dict((name, PrimitiveType(None, name)) for name in TYPES)
    for synonym, of in SYNONYMS.iteritems():
        d[synonym] = d[of]
    return d

BUILTINS = _get_builtins()
del TYPES
del SYNONYMS
del _get_builtins

class AnalyzingError(Exception):
    pass

class ImplementationError(AnalyzingError):
    pass

class Analyzer(object):
    def __init__(self, namespace):
        self.namespace = namespace
        self.objects = odict()

    def to_json(self, **kwargs):
        import json
        return json.dumps(
                self.objects.items(),
                default=lambda obj: obj.get_state(self.objects),
                **kwargs)

    def analyze(self):
        self.analyze_classes()
        self.analyze_enumerations()
        self.analyze_typedefs()
        self.analyze_functions()

    def analyze_classes(self):
        """
            analyze all classes (structs, to be exact, but gccxml handles structs as classes
            because C++ also does).
        """
        for class_ in self.namespace.classes():
            self.analyze_class(class_)

    def analyze_enumerations(self):
        for enum in self.namespace.enumerations():
            self.analyze_enum(enum)

    def analyze_typedefs(self):
        for typedef in self.namespace.typedefs():
            self.analyze_typedef(typedef)

    def analyze_functions(self):
        for function in self.namespace.free_functions():
            self.analyze_function(function)

    def resolve_type(self, type):
        if isinstance(type, pygccxml.declarations.fundamental_t):
            return type.CPPNAME
        elif isinstance(type, pygccxml.declarations.pointer_t):
            return 'POINTER(%s)' % type.base
        elif isinstance(type, pygccxml.declarations.declarated_t):
            return self.resolve_type(type.declaration) # TODO: not sure about that
        elif isinstance(type, (pygccxml.declarations.class_declaration_t, pygccxml.declarations.class_t)):
            # classes are structs.
            return 'STRUCT(%s)' % type.name
        elif isinstance(type, pygccxml.declarations.typedef_t):
            # the type name of a typedef'ed type is the type name.
            return type.name
        elif isinstance(type, pygccxml.declarations.array_t):
            return 'ARRAY(%s, %s)' % (self.resolve_type(type.base), format_tag(type.size))
        elif isinstance(type, pygccxml.declarations.volatile_t):
            return 'VOLATILE(%s)' % self.resolve_type(type.base)
        elif isinstance(type, pygccxml.declarations.enumeration_t):
            return 'ENUM(%s)' % type.name
        elif isinstance(type, pygccxml.declarations.restrict_t):
            return 'RESTRICT(%s)' % self.resolve_type(type.base)
        elif isinstance(type, pygccxml.declarations.const_t):
            return 'CONST(%s)' % self.resolve_type(type.base)
        else:
            print vars(type)
            raise ImplementationError("Unknown type: %r (%r)" % (type, type.__class__))

    def analyze_class(self, class_):
        obj = Struct(format_coord(class_.location), class_.name)
        # add all members, but only variables, because all other stuff
        # is evil C++ stuff.
        for member in class_.get_members():
            if isinstance(member, pygccxml.declarations.variable_t):
                type_tag = self.resolve_type(member.type)
                obj.add_member(member.name, type_tag, member.bits)
        # add it to the objects
        self.objects[obj.name] = obj

    def analyze_enum(self, enum):
        obj = Enum(format_coord(enum.location), enum.name)
        for value in enum.values:
            obj.add_member(value[0], value[1])
        self.objects[obj.name] = obj

    def analyze_typedef(self, typedef):
        obj = Typedef(
                format_coord(typedef.location),
                typedef.name,
                self.resolve_type(typedef.type)
                )
        self.objects[obj.tag] = obj

    def analyze_function(self, function):
        arguments = odict()
        varargs = True
        for arg in function.arguments:
            if arg.ellipsis:
                varargs = True
            else:
                arguments[arg.name] = self.resolve_type(arg.type)
        rettype = None
        if function.return_type:
            rettype = self.resolve_type(function.return_type)
        self.objects[function.name] = Function(
                format_coord(function.location),
                function.name,
                rettype,
                arguments,
                varargs,
                ('extern',) if function.has_extern else None
                )

