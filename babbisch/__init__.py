from __future__ import with_statement

import sys
import os

# stolen from http://www.language-binding.net/pygccxml/example/example.py.html
# find out the file location within the sources tree
this_module_dir_path = os.path.abspath (os.path.dirname(sys.modules[__name__].__file__))
# find out gccxml location
gccxml_09_path = os.path.join(this_module_dir_path, '..', '..', '..', 'gccxml_bin', 'v09', sys.platform, 'bin')

import pygccxml.parser, pygccxml.declarations


import os.path
from optparse import OptionParser

from babbisch.analyze import Analyzer

USAGE = 'usage: %prog [options] headerfile...'
FORMATS = {
        'json': lambda analyzer: analyzer.to_json(indent=2)
        }

def main():
    parser = OptionParser(usage=USAGE)
    parser.add_option('-f', '--format',
            action='store',
            choices=FORMATS.keys(),
            dest='format',
            default='json',
            help="defines the output format to use [supported: json]",
            )
    parser.add_option('-o',
            action='store',
            dest='output',
            default=None,
            help="defines the output filename [default: stdout]",
            )
    parser.add_option('-I',
            action='append',
            dest='includes',
            default=[],
            help='add PATH to the include path',
            metavar='PATH'
            )

    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error('You have to pass exactly one input file.')
    
    config = pygccxml.parser.config_t(
            gccxml_path=gccxml_09_path,
            include_paths=options.includes,
    )

    # read and analyze source file
    filename = args[0]
    if not os.path.isfile(filename):
        parser.error("'%s' is not a valid filename" % filename)
    else:
        decls = pygccxml.parser.parse([filename], config)
        analyzer = Analyzer(pygccxml.declarations.get_global_namespace(decls))
        analyzer.analyze()
    
    # output
    stuff = FORMATS[options.format](analyzer)
    if options.output is None:
        # just print it
        print stuff
    else:
        with open(options.output, 'w') as f:
            f.write(stuff)

