import re
def with_equ(src, **kw):
    for k, v in kw.items():
        src, n = re.subn(r'(?m)^(\.equ\s+%s\s*,\s*)[^;\n]+' % k, r'\g<1>%s' % v, src)
        assert n == 1, k
    return src
