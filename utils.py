import re
import serial
import subprocess
import datetime
from time import perf_counter, sleep, time
import functools
from random import randrange

def pad(data, block_size=16):
    pad_len = block_size - len(data) % block_size
    if type(data) not in {bytes, bytearray}:
        data = data.encode()
    return data + pad_len * bytes([pad_len])

def unpad(padded_data, block_size=16):
    pdata_len = len(padded_data)
    pad_len = padded_data[-1]
    if pdata_len % block_size:
        raise ValueError("data not padded properly")
    return padded_data[:-pad_len].decode()

bfh = lambda: bytes.fromhex

def int_to_hex(i, length=1):
    bs = length - len(i)

def cmd_res(cmd):
    p = subprocess.Popen([arg for arg in str(cmd).split()], stdin=subprocess.PIPE)
    p.wait()
    if p.returncode >= 0:
        return 0
    else:
        return -1

def check_err(msg, ret):
    if ret != 0:
        print(f"ERROR: {msg}")
    else:
        print("success")
    
RED = lambda s: "\033[91m {}\033[00m".format(s)
GREEN = lambda s: "\033[92m {}\033[00m".format(s)
YELLOW = lambda s: "\033[93m {}\033[00m".format(s)
CYAN = lambda s: "\033[96m {}\033[00m".format(s)
LIGHTPURPLE = lambda s: "\033[94m {}\033[00m".format(s)
PURPLE = lambda s: "\033[95m {}\033[00m".format(s)
GRAY = lambda s: "\033[97m {}\033[00m".format(s)
BLACK = lambda s: "\033[98m {}\033[00m".format(s)

TODAY = datetime.datetime.now().strftime("%m-%d-%Y")
NOW = datetime.datetime.now().strftime('%H-%M-%S')

log_time_format = "%(asctime)s - %(module)s - %(levelname)s - %(message)s"

def timer(duration):
    start = perf_counter()
    while True:
        end = perf_counter()
        if int(end - start) >= duration:
            break

class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        sleep(0.5)

    def flush_port(self):
        self.port.flush()

    def write_no_crlf(self, cmd):
        self.port.write(str(cmd).encode())
        sleep(0.5)
        self.port.flush()
        sleep(0.5)

    def read_response(self, size=None, decode=True):
        res = None
        if not self.port.is_open:
            self.port.open()
        if size is None:
            msg = self.port.readlines()
            if decode == True:
                res = [str(m.decode()) for m in msg]
                res = [m.strip("\r\n") for m in res if m.find("\r\n")]
            else:
                res = bytearray([b for b in msg])
        elif type(size) == int:
            msg = self.port.read(size)
            if decode == True:
                res = msg.decode()
            else:
                res = msg
        else:
            raise ValueError("size must be an integer or None")
        return res

    def read_lines(self, end=None):
        if not self.port.is_open:
            self.port.open()
        while True:
            data = self.port.readline().decode()
            if end is not None:
                if re.match(end, data):
                    break
            elif len(data) < 1:
                break
            else:
                self.queue.append(data)

def cmd_ret(cmd):
    res = None
    p = subprocess.Popen([arg for arg in str(cmd).split()])
    while True:
        sleep(1)
        res = p.poll()
        if res is not None:
            break
    if res >= 0:
        return 0
    else:
        return -1

def memo(func):
    cache = {}
    @functools.wraps(func)
    def wrap(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrap

def sqrt(x):
    return x**(1/2)

def mean(seq):
    return sum(seq) / len(seq)

def variance(values):
    return sum([i - mean(values)**2 for i in values])

def standard_deviation(x):
    return sqrt(variance(x))

def covariance(x, y):
    covar = 0.0
    for i in range(len(x)):
        covar += (x[i] - mean(x)) * (y[i] - mean(y))
    return covar

def transpose(matrix):
    size = len(matrix) 
    res = [[matrix[y][x] for y in range(size)] for x in range(size)]
    return res

def phi(n):
    result = 1
    for i in range(2, n):
        if(gcd(i, n) == 1):
            result += 1
    return result

def pi():
    return 3.141592653589793

def e():
    x = 1.0
    for i in range(1,16):
        x += 1/factorial(i)
    return x

def exp(x):
    return e()**x

@memo
def gcd(a,b):
    if a == 0:
        return b
    return gcd(b % a, a)

@memo
def factorial(n):
    if n < 1:
        return 1
    return n * factorial(n-1)

def binomial_permutations(n, k):
    return factorial(n) / (factorial(k) * factorial(n - k))

def factorial_iter(n):
    x = 1
    for i in range(1, n+1):
        x *= i
    return x

def factors(n):
    f = []
    for i in range(2, n):
        if n % i == 0:
            f.append(i)
    return f

def sigmoid(x):
    return 1 / (1 + exp(-x))

def sigmoid_derivative(x):
    return x * (1 - x)

def cohens_kappa(tp, tn, fp, fn):
        po = (tp + tn) / (tp + fp + fn + tn)
        py = ((tp + fp) / (tp + fp + fn + tn)) * ((tp + fn) / (tp + fp + fn + tn))
        pn = ((fn + tn) / (tp + fp + fn + tn)) * ((fp + tn) / (tp + fp + fn + tn))
        pe = py + pn
        return (po - pe) / (1 - pe) * 100.0

def run_time(func):
    @functools.wraps(func)
    def wrap(*args):
        start = time()
        val = func(*args)
        end = time()
        n = start - end
        return f"time: {n}, value: {val}"
    return wrap

def cross_validation(inputs, n_folds):
    data = list(inputs)
    fold_size = len(inputs) // n_folds
    folds = []
    for _ in range(n_folds):
        fold = []
        while len(fold) < fold_size:
            i = randrange(len(data))
            fold.append(data.pop(i))
        folds.append(fold)
    return sum(folds, [])

def confusion_matrix(actual, predicted):
        matrix = {"positive": {}, "negative": {}}
        tp, fp, fn, tn = 0, 0, 0, 0
        for i in range(len(actual)):
            if actual[i] == predicted[i] and actual[i] == 1:
                tp += 1
            if actual[i] != predicted[i] and actual[i] == 0:
                fp += 1
            if actual[i] != predicted[i] and actual[i] == 1:
                fn += 1
            if actual[i] == predicted[i] and actual[i] == 0:
                tn += 1
        matrix["positive"]["predict_pos"] = tp
        matrix["positive"]["predict_neg"] = fn
        matrix["negative"]["predict_pos"] = fp
        matrix["negative"]["predict_neg"] = tn
        return matrix

def dot(x, y):
    return sum(i * j for i, j in zip(x, y))

def range_primes(n=20):
    p = []
    for i in range(2, n):
        if factors(i) == []:
            p.append(i)
    return p

def prime_factors(n):
    primes = range_primes(n)
    i = 2
    f = []
    while n % 2 == 0:
        f.append(i)
        n /= i
    for j in primes:
        while n % j == 0:
            f.append(j)
            n /= j
    return f

def prime_fact(n, primes):
    p = {}
    p[n] = []
    total = 1
    for i in primes:
        if n % i == 0:
            if i <= n: 
                p[n].append(i)
                total *= i
    return p 

def fizz_buzz_encode(x: int):
    if x % 15 == 0:
        return [0, 0, 0, 1]
    elif x % 5 == 0:
        return [0, 0, 1, 0]
    elif x % 3 == 0:
        return [0, 1, 0, 0]
    else:
        return [1, 0, 0, 0]

def binary_encode(x: int):
    binary = []
    for _ in range(10):
        binary.append(x % 2)
        x = x // 2
    return binary