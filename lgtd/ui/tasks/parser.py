from functools import partial


class ParseError(Exception):
    pass


def _add_argument(parse_func, *args, **kwargs):
    def wrapper(f):
        if not hasattr(f, 'arguments'):
            f.arguments = []
        f.arguments.insert(0, dict(
            parse_func=parse_func, args=args, kwargs=kwargs)
        )

        return f
    return wrapper


def parse_option(long_name, short_name, parsed, unparsed, noparse):
    name = long_name[2:]
    try:
        index = next(
            i for i, arg in enumerate(unparsed)
            if arg in (short_name, long_name)
        )
        return parsed + [(name, True)], \
            unparsed[:index] + unparsed[index+1:], noparse
    except StopIteration:
        return parsed + [(name, False)], unparsed, noparse


def option(long_name, short_name, help=None):
    return _add_argument(parse_option, long_name, short_name, help=help)


def parse_remainder(name, blank, parsed, unparsed, noparse):
    if not blank and not unparsed and not noparse:
        raise ParseError('Argument {} may not be empty'.format(name))

    return parsed + [(name, ' '.join(unparsed + noparse))], [], []


def remainder(name, blank=False, help=None):
    return _add_argument(parse_remainder, name, blank, help=help)


def parse_positional(name, type_, default, required,
                     parsed, unparsed, noparse):
    if required and default:
        raise ParseError('Argument {} is required and has default'.format(
            name))

    while unparsed and not unparsed[0]:
        unparsed = unparsed[1:]

    if unparsed:
        try:
            value = type_(unparsed[0])
        except Exception:
            raise ParseError('Bad value for argument {} of {}'.format(
                name, type_))

        return parsed + [(name, value)], unparsed[1:], noparse
    else:
        if required:
            raise ParseError('Required argument {} not provided'.format(name))
        else:
            return parsed + [(name, default)], [], noparse


def positional(name, type_=str, default=None, required=True, help=None):
    return _add_argument(
        parse_positional, name, type_, default, required, help=help)


def _split_args(args):
    try:
        index = next(i for i, arg in enumerate(args) if arg == '--')
        return args[:index], args[index+1:]
    except StopIteration:
        return args, []


def parse_args(args, syntax):
    parsed = []
    unparsed, noparse = _split_args(args)

    for token in syntax:
        func = partial(token['parse_func'], *token['args'])
        parsed, unparsed, noparse = func(parsed, unparsed, noparse)

    if unparsed or noparse:
        raise ParseError('Extra arguments: {}'.format(
            ' '.join(unparsed + noparse)))

    return dict(parsed)
