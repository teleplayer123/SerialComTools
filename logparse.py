#!/usr/bin/python3

#written by Cole Sashkin

from collections import defaultdict
import datetime
import os
import re
import shutil
import sys


#TODO balancing algorithm for start end pairs


USAGE = """
Usage: 

    logparse.py -l <filename> <start_str> <end_str> <log_type>
        -l  return latency time(s) in seconds, and line number of the search string.

    logparse.py -a <filename> <split_str> <start_str> <end_str> [log_type: default=serial]
        -a  return average of latencies in seconds
            split contents of <filename> with delimiter <split_str> into multiple files in a new directory.
            this option helps accuracy when start and end log lines appear frequently in log.

    logparse.py -r <dirname> <start_str> <end_str> <log_type>
        -r recurses through directory <dirname> and returns average latency in seconds.

    logparse.py -s <filename> <delimiter> <dirname>
        -s  split <filename> into multiple files in directory <dirname> 
            using <delimiter>. returns path to new directory.

    logparse.py -f <filename> <search_str> <log_type>
        -f find specified log line in file that contains a latency value usually in milliseconds
           returns logline index and latency if there is one.

ARGS:

    NOTE: each argument must be passed to command line between quotation marks,
          except for the flag. arguments need to be passed in order as specified in Usage.  
    FLAGS: [-l | -a | -s | -f]
    filename: absolute path to log file to parse.
    start_str: log line representing start timestamp.
    end_str: log line representing end timestamp.
    log_type: should be one of ['logcat' | 'cutecom' | 'serial']
        description: 
            logcat: logcat log file.
            cutecom: cutecom log file configured in cutecom GUI.
            serial: copy and paste cutecom logs from GUI to blank text file.
"""
                    
def get_logstr_tms(filename, search_str, log_type="cutecom"):
    tm = None
    tms = []
    if log_type == "logcat":
        tm_regx = re.compile(r"^[\[\s]*?[\d]{2}-[\d]{2}\s(?P<timestamp>[\d:.]+)[\]]*?")
    elif log_type == "serial":
        tm_regx = re.compile(r"\[(?P<timestamp>[\d]{2}:[\d]{2}:[\d]{2}:[\d]{3})\]|(?P=timestamp)\s\[(?P<date>[\d]{4}-[\d]{2}-[\d]{2})\s(?P<time>[\d]{2}:[\d]{2}:[\d]{2}\.[\d]{3})\s[^\]]*\]")
    elif log_type in {"cutecom", "minicom"}:
        tm_regx = re.compile(r"\[(?P<date>[\d]{4}-[\d]{2}-[\d]{2})\s(?P<timestamp>[\d]{2}:[\d]{2}:[\d]{2}\.[\d]{3})\s[^\]]*\]")
    with open(filename, "r", encoding="latin-1") as fh:
        for i, line in enumerate(fh, start=1):
            for m in re.findall(search_str, line):
                if re.match(r"^-->", line):
                    line = re.sub(r"^-->", "", line) 
                if tm_regx.match(line):
                    try:
                        tm = tm_regx.match(line).group("timestamp")
                    except AttributeError as err:
                        print(err)
                    if tm != None: 
                        tms.append((tm, i))
                    else:
                        continue
                else:
                    continue
    return tms


def split_log(filename, split_str, dirname=None):
    if dirname == None:
        dirname = filename.split(".")[0]
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    fname = filename.split("/")[-1].split(".")[0]
    i = 0
    for chunk in get_chunks(filename, split_str):
        with open(f"{dirname}/{fname}_{i}.log", "w") as fh:
            fh.write(str(chunk))
        i += 1
    return dirname


def get_chunks(filename, s):
    with open(filename, "r", encoding="latin-1") as fh:
        chunks = re.split(s, fh.read())
        for chunk in chunks:
            yield chunk 


def parse_log_datetime_latency(filename, search_str, log_type="cutecom"):
    tm_dict = defaultdict(dict)
    if log_type in {"cutecom", "minicom"}:
        tm_regx = re.compile(r"\[(?P<date>[\d]{4}-[\d]{2}-[\d]{2})\s(?P<timestamp>[\d]{2}:[\d]{2}:[\d]{2}\.[\d]{3})\s[^\]]*\]")
    elif log_type == "serial":
        tm_regx = re.compile(r"\[(?P<timestamp>[\d]{2}:[\d]{2}:[\d]{2}:[\d]{3})\]|(?P=timestamp)\s\[(?P<date>[\d]{4}-[\d]{2}-[\d]{2})\s(?P<time>[\d]{2}:[\d]{2}:[\d]{2}\.[\d]{3})\s[^\]]*\]")
    elif log_type == "logcat":
        tm_regx = re.compile(r"^[\[\s]*?[\d]{2}-[\d]{2}\s(?P<timestamp>[\d:.]+)[\]]*?\s")
    with open(filename, "r", encoding="latin-1") as fh:
        for i, line in enumerate(fh, start=1):
            for m in re.findall(search_str, line):
                try:
                    tm = tm_regx.match(line).group("timestamp")
                    lat = re.findall(r"latency=[\d\w]*", line)
                    if len(lat) > 0:
                        tm_dict[search_str][f"line: {str(i)}"] = {"Timestamp": tm, "Latency": lat}
                    else:
                        tm_dict[search_str][f"line: {str(i)}"] = tm
                except AttributeError as err:
                    print(err)
    return tm_dict


def log_time_diff_gen(filename, start_str, end_str, log_type="cutecom"):
    first_list = get_logstr_tms(filename, start_str, log_type)
    second_list = get_logstr_tms(filename, end_str, log_type)
    for first, second in zip(first_list, second_list):
        tm1 = first[0].split(":")
        tm2 = second[0].split(":")
        if log_type != "serial":
            sec1, msec1 = tm1[-1].split(".")
            sec2, msec2 = tm2[-1].split(".")
        else:
            sec1, msec1 = tm1[-2], tm1[-1]
            sec2, msec2 = tm2[-2], tm2[-1]
        t1 = datetime.time(int(tm1[0]), int(tm1[1]), int(sec1), int(msec1))
        t2 = datetime.time(int(tm2[0]), int(tm2[1]), int(sec2), int(msec2))
        td1 = datetime.timedelta(hours=t1.hour, minutes=t1.minute, seconds=t1.second, microseconds=t1.microsecond).total_seconds()
        td2 = datetime.timedelta(hours=t2.hour, minutes=t2.minute, seconds=t2.second, microseconds=t2.microsecond).total_seconds()
        diff = td2 - td1
        yield diff


def recursive_latency(dirname, start_str, end_str, log_type):
    times = []
    paths = []
    for path, _, filenames in os.walk(dirname):
        for filename in filenames:
            paths.append(os.path.join(path, filename))
    for filename in paths:
        times.append([time for time in log_time_diff_gen(filename, start_str, end_str, log_type) if time > 0])
    return times


def main():
    times = []
    res = None
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)
    flag = sys.argv[1]
    if re.match(r"^-l$", flag):
        fn = sys.argv[2]
        arg1 = sys.argv[3]
        arg2 = sys.argv[4]
        log_type = sys.argv[5]
        res = log_time_diff_gen(fn, arg1, arg2, log_type=log_type)
        for r in res:
            if r > 0:
                times.append(r)
            else:
                print("Results contain negative values, try using '-a' flag instead.")
        res = sum(times)/len(times)
    elif re.match(r"^-a$", str(flag)):
        fn = sys.argv[2]
        split_str = sys.argv[3]
        arg1 = sys.argv[4]
        arg2 = sys.argv[5]
        if len(sys.argv) < 7:
            log_type = "cutecom"
        else:
            log_type = sys.argv[6]
        dirname = split_log(fn, split_str)
        res = recursive_latency(dirname, arg1, arg2, log_type)
        res = sum(sum(res, [])) / len(sum(res, []))
        dirname = os.path.join(os.getcwd(), dirname)
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
    elif re.match(r"^-r$", flag):
        dirname = sys.argv[2]
        arg1 = sys.argv[3]
        arg2 = sys.argv[4]
        log_type = sys.argv[5]
        res = recursive_latency(dirname, arg1, arg2, log_type)
        res = sum(sum(res, [])) / len(sum(res, []))
    elif re.match(r"^-s$", flag):
        fn = sys.argv[2]
        arg1 = sys.argv[3]
        dirname = sys.argv[4]
        split_log(fn, arg1, dirname)
        res = f"Logs to parse are in directory {dirname}"
    elif re.match(r"^-f$", flag):
        fn = sys.argv[2]
        arg1 = sys.argv[3]
        log_type = sys.argv[4]
        res = parse_log_datetime_latency(fn, arg1, log_type)
    else:
        print(USAGE)
        sys.exit(0)
    return res



if __name__ == "__main__":
    result = main()
    print(result)