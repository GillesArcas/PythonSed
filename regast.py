import re


class Regast:
    def __init__(self, regex):
        _, regast = parse_seq(regex, 0)
        # regast may be Seq or Alt
        if isinstance(regast, Seq) and len(regast.list) == 1:
            self.regast = regast.list[0]
        else:
            self.regast = regast

    def __str__(self):
        return str(self.regast)

    def dump(self, indent=0):
        print(' ' * indent, type(self).__name__, sep='')
        indent += 4
        for var in vars(self):
            val = self.__dict__[var]
            print(' ' * (indent - 1), 'var', var, type(val), '[...]' if type(val) == list else val)
            if isinstance(val, list):
                for elem in val:
                    elem.dump(indent + 4)
            elif isinstance(val, Regast):
                val.dump(indent + 4)
            else:
                print(' ' * (indent - 1), val)


class Char(Regast):
    def __init__(self, char):
        self.char = char

    def __str__(self):
        return self.char


class Escaped(Regast):
    def __init__(self, char):
        self.char = char

    def __str__(self):
        return '\\' + self.char


class Any(Regast):
    def __init__(self):
        pass

    def __str__(self):
        return '.'


class Set(Regast):
    def __init__(self, set):
        self.set = set

    def __str__(self):
        return '[%s]' % self.set


class Quantifier(Regast):
    def __init__(self, quantifier, regast):
        self.quantifier = quantifier
        self.regast = regast

    def __str__(self):
        return '%s%s' % (self.regast, self.quantifier)


class Braces(Regast):
    def __init__(self, n1, n2, regast):
        self.n1 = n1
        self.n2 = n2
        self.regast = regast

    def __str__(self):
        if self.n2 is None:
            return '%s{%s}' % (self.regast, self.n1)
        else:
            return '%s{%s,%s}' % (self.regast, self.n1, self.n2)


class Backref(Regast):
    def __init__(self, digit):
        self.digit = digit

    def __str__(self):
        return '\\' + self.digit


class Seq(Regast):
    def __init__(self, nodes):
        self.list = nodes

    def __str__(self):
        return ''.join((str(_) for _ in self.list))


class Group(Regast):
    def __init__(self, nodes):
        self.list = nodes

    def __str__(self):
        return '(%s)' % ''.join((str(_) for _ in self.list))


class Alt(Regast):
    def __init__(self, alt1, alt2):
        self.alt1 = alt1
        self.alt2 = alt2

    def __str__(self):
        return '%s|%s' % (self.alt1, self.alt2)


class Anchor(Regast):
    def __init__(self, char):
        self.char = char

    def __str__(self):
        return self.char


def parse_seq(regexp, i, within_group=False):
    """ regexp must be an extended regexp
    return a couple index, Seq (index last char of the sequence)
    """
    nodes = []
    while i < len(regexp):
        if regexp[i] == '.':
            nodes.append(Any())
            i += 1
        elif regexp[i] == '\\':
            i, regast = parse_slash(regexp, i + 1)
            nodes.append(regast)
            i += 1
        elif regexp[i] == '[':
            i, regast = parse_set(regexp, i + 1)
            nodes.append(regast)
            i += 1
        elif regexp[i] == ']':
            nodes.append(Char(regexp[i]))
            i += 1
        elif regexp[i] == '(':
            i, regast = parse_seq(regexp, i + 1, within_group=True)
            nodes.append(regast)
            i += 1
        elif regexp[i] == ')':
            if within_group:
                return i, Group(nodes)
            else:
                nodes.append(Char(regexp[i]))
                i += 1
        elif regexp[i] == '^':
            if i > 0 and regexp[i-1] not in '(|':
                nodes.append(Char(regexp[i]))
                i += 1
            else:
                nodes.append(Anchor(regexp[i]))
                i += 1
        elif regexp[i] == '$':
            if i < len(regexp) - 1 and regexp[i + 1] not in '|)':
                nodes.append(Char(regexp[i]))
                i += 1
            else:
                nodes.append(Anchor(regexp[i]))
                i += 1
        elif regexp[i] in '+*?':
            if i > 0:
                nodes.append(Quantifier(regexp[i], nodes.pop()))
                i += 1
            else:
                SedException('regexp: nothing to repeat ' + regexp)
        elif regexp[i] in '{':
            if i > 0:
                i, n1, n2 = parse_braces(regexp, i + 1)
                nodes.append(Braces(n1, n2, nodes.pop()))
                i += 1
            else:
                SedException('regexp: nothing to repeat ' + regexp)
        elif regexp[i] in '}':
            nodes.append(Char(regexp[i]))
            i += 1
        elif regexp[i] in '|':
            s1 = Seq(nodes)
            i, s2 = parse_seq(regexp, i + 1)
            return i, Alt(s1, s2)
        else:
            nodes.append(Char(regexp[i]))
            i += 1
    return i, Seq(nodes)


def parse_set(regexp, i):
    """ i first char after opening bracket
    """
    i0 = i
    while i < len(regexp):
        if regexp[i] == ']' and i > 0:
            return i, Set(regexp[i0:i])
        else:
            i += 1
    else:
        raise Exception('No closing bracket')


def parse_slash(regexp, i):
    """ i index of escaped character
    """
    if i == len(regexp):
        return i, Char('\\')
    elif regexp[i] in '0123456789':
        return i, Backref(regexp[i])
    else:
        return i, Escaped(regexp[i])


def parse_braces(regexp, i):
    m = re.match(r'(\d+)}', regexp[i:])
    if m:
        return i + m.end(1), m.group(1), None
    m = re.match(r'(\d+),(\d*)}', regexp[i:])
    if m:
        return i + m.end(2), m.group(1), m.group(2)

    raise Exception('Invalid content of {}')


class SedException(Exception):
    def __init__(self, message):
        self.message = 'sed.py error: %s' % message


if __name__ == "__main__":
    tests = (
        'a',
        'abc',
        '^abc',
        'a^b',
        'abc$',
        'a$c',
        '.',
        '...',
        'a.b.',
        'a[0-9]bc',
        'a[^0-9]bc',
        'a[]0-9]bc',
        'a]c',
        'a(bcd)e',
        'a(b(c)d)e',
        'a((b(c)d)ef(gh))',
        '[12](abc[0-9]def)[]a-z]',
        r'a\(b',
        r'\a\(\b\\',
        r'\1\2\3',
        r'\14\25\36',
        'abc*',
        'abc+',
        'abc?',
        'abc{3}de',
        'abc{3,}de',
        'abc{3,5}de',
        'abc*?+{5,9}',
        'abc|def',
        'abc|def|ghi',
    )

    for test in tests:
        r = Regast(test)
        print('pass' if str(r) == test else 'fail', '~%s~%s~' % (test, r))

    regast = Regast('abc|def|ghi')
    regast.dump()
