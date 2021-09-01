#!/usr/bin/python3
"""
Purpose:
    reorder Gramps dot file to minimise crossings in relationship chart

Usage:
    create a relationship graph in Gramps to produce .gv file
    copy .gv file and this .py file to the same directory
    in that directory, run
      $./GrampsCrossing.py yourfile.gv
    output is now more verbose:
        iterations, span, index, nr_cross_best, nr_cross_new, iteration time
    it takes several minutes, depending on file size
    it doesn't alter your .gv file
    it saves optimised files as .dot and .pdf files
    ctrl c stops iterations and dumps current .dot and .pdf
"""

import subprocess
import sys
import signal
import time
import os
import platform


def signal_handler(thesignal, frame):
    print('Ctrl+C pressed! Writing files and aborting...')
    write_files(dot_markup, dot)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# read the dot file and parse into parts
def parse():
    with open(sys.argv[1], mode='r', encoding='utf-8') as f:
        src = f.readlines()
    p1 = 2  # find end of header section
    for i, l in enumerate(src):
        if 'node ' in l:
            p1 = i + 2
            break

    dot_header = src[0:p1]  # parse off header section of input file
    dot_body = src[p1:]
    dot_links = []
    dot_people = []
    dot_spouses = []
    dot_families = []

    j = 0
    while j < len(dot_body):
        l = dot_body[j]
        if ' -> ' in dot_body[j]:
            dot_links.append(l)
        elif l.startswith('  I') or l.startswith('  "I'):
            dot_people.append(l)
        elif l.startswith('  subgraph'):
            for y, k in enumerate(dot_body[j:]):
                if k.startswith('  }'):
                    break
            dot_spouses.append(''.join(dot_body[j:j + y + 1]))
            j += y
        else:
            dot_families.append(l)
        j += 1

    return dot_header, dot_people, dot_families, dot_spouses, dot_links


# function to return number of crossings for given dot file
def crossings(df, command):
    result = subprocess.run(command, capture_output=True, text=True, input=''.join(df), encoding='utf-8')
    line = ''
    for l in result.stderr.split('\n'):  # iterate through output to find line with number of crossings
        if 'crossings' in l:
            line = l
            break
    if line == '':
        print("error processing dot file, no usable output")
        return 0
    p1 = line.find(':')
    p2 = line.find('crossings')
    return int(line[p1 + 1:p2 - 1])


def write_files(df, dot):
    file_base = sys.argv[1]
    file_dot = file_base[:-4] + "1.dot"
    file_pdf = file_base[:-4] + "1.pdf"
    print("Generating output dot file:", file_dot)
    with open(file_dot, 'w', encoding='utf-8') as f:
        f.write(''.join(df))
    print("Generating output pdf file:", file_pdf)
    cmd = [dot, '-v', '-Tpdf', '-o', file_pdf]
    subprocess.run(cmd, capture_output=True, text=True, input=''.join(df), encoding='utf-8')
    totalTime = time.time() - startTime
    print(f"Crossings reduced from {nr_cross_original} to {nr_cross_best},",
          "runtime=%0.2f seconds," % totalTime, f"iterations= {iterations}")
    print("Average iteration time= %0.2f seconds," % (totalTime / iterations),
          "longest iteration time= %0.2f seconds," % longestTime,
          "shortest iteration time= %0.2f seconds" % shortestTime)


# find largest power of 2 less than n
def initial_span(n):
    s = 2
    while n > s:
        s *= 2
    return int(s / 2)


# find path for dot executable in Windows
def dot_path():
    if platform.system() != "Windows":
        return "dot"

    print("Searching Windows for dot.exe ...")
    paths = ["C:\\Program Files\\", "C:\\Program Files (x86)\\"]
    name = "dot.exe"
    for path in paths:
        for root, _, files in os.walk(path):
            if name in files:
                print(f"Found {os.path.join(root, name)}")
                return os.path.join(root, name)
    sys.exit("Error: dot.exe not found")


if __name__ == "__main__":
    startTime = time.time()
    header, people, families, spouses, links = parse()

    nsize = len(people)
    span = initial_span(nsize)
    dot = dot_path()
    cmd = [dot, '-v', '-Tpdf', '-o', os.devnull]

    new_people = []
    nr_cross_best = crossings(header + people + links + spouses + families, cmd)
    print(f"people= {nsize}, initial span= {span}, initial crossings= {nr_cross_best}")
    nr_cross_new = nr_cross_best
    nr_cross_original = nr_cross_best
    iterations = 0
    totalTime = 0
    longestTime = 0
    shortestTime = float("inf")
    while span >= 1:
        for i in range(nsize - span):
            iterationsStartTime = time.time()
            new_people = people[:]
            new_people[i + span], new_people[i] = new_people[i], new_people[i + span]
            dot_markup = header + new_people + links + spouses + families
            nr_cross_new = crossings(dot_markup, cmd)
            iterations += 1
            if nr_cross_new < nr_cross_best:
                people = new_people[:]
                nr_cross_best = nr_cross_new
            iterationTime = time.time() - iterationsStartTime
            if iterationTime < shortestTime:
                shortestTime = iterationTime
            if iterationTime > longestTime:
                longestTime = iterationTime
            print(f"iterations={iterations} span={span} i={i} best_cross={nr_cross_best}",
                  f"current_cross={nr_cross_new}", "time=%0.2f seconds" % iterationTime)
            if nr_cross_best == 0:
                break
        span = int(span / 2)
    write_files(header + people + links + spouses + families, dot)
