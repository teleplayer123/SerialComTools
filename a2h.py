import sys
import re

def a2h(s):
    h = []
    for i in s[:]:
        h.append("\\x%02x" % ord(i))
    return "".join(h)

def a2h0(s):
    h0 = []
    for i in s[:]:
        h0.append("%02x" % ord(i))
    return "0x"+"".join(h0)


def rev_a2h(s):
    if not re.match(r"^\\x", s):
        hs = a2h(s)
    else:
        hs = s
    rhs = ""
    odd = False
    obit = ""
    r = hs.split("\\x")
    if len(r) % 2 != 0:
        obit = r[0:1]
        r = r[1:]
        odd = True
    for i in range(len(r)-1, -1, -1):
        rhs += "\\x" + r[i]
    if odd:
        rhs += obit[0]
    return rhs

def print_usage():
    print("""Usage:  [options] [string]

            options: -h  string to hex
                     -r  string to hex little endian""")
    sys.exit(0)

flags = {"-h", "-r", "-o"}

if len(sys.argv) < 3:
    print_usage()
f, s = sys.argv[1], sys.argv[2]
if f not in flags:
    print_usage()
if f in {"-h"}:
    print(a2h(str(s)))
elif f in {"-r"}:
    print(rev_a2h(str(s)))
elif f in {"-o"}:
    print(a2h0(str(s)))
else:
    print("Invalid Input")
    sys.exit(0)

