#!/usr/bin/python3
"""
Author: Peter Hewett
Contributors: Filipe Correia, Maurice Snell
Copyright GPL 2012 - 2021
edited: 10 March 2014
edited: V0.4 18 August 2014, Maurice Snell:
- Made Windows compatible, not restested on *nix but should still work.
- Increased & clarified output messages
- Fixed bug with writing output when user cancels optimisation.
 edited: 15 Jan 2019 PWH: converted to python3
 edited: v0.9 24 Aug 2021 PWH: fixed bug with pdf export
 edited: v0.10 26 Aug 2021 PWH: add dot path for Windows

 reorder Gramps dot file to minimise crossings in relationship chart
 usage:
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
def crossings(df, dot):
    cmd = [dot, '-v', '-Tpdf', '-o', os.devnull]
    result = subprocess.run(cmd, capture_output=True, text=True, input=''.join(df), encoding='utf-8')
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
    print(f"Crossings reduced from {nr_cross_original} to {nr_cross_best},",
          "runtime=%0.2f seconds," % (time.time() - startTime), f"iterations= {iterations}")
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
# might not work if multiple versions of Gramps are installed in Windows
def dot_path():
    path = "dot"
    if platform.system() == "Windows":
        path = "C:\\Program Files\\"
        directories = os.listdir(path)
        for app in directories:
            if app[:5] == "Gramp":
                path += app + "\\dot.exe"
                break
    return path


if __name__ == "__main__":
    startTime = time.time()
    header, people, families, spouses, links = parse()

    nsize = len(people)
    span = initial_span(nsize)
    dot = dot_path()

    new_people = []
    nr_cross_best = crossings(header + people + links + spouses + families, dot)
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
            tmp = new_people[i]
            new_people[i] = new_people[i + span]
            new_people[i + span] = tmp
            dot_markup = header + new_people + links + spouses + families
            nr_cross_new = crossings(dot_markup, dot)
            iterationTime = time.time() - iterationsStartTime
            if iterationTime < shortestTime:
                shortestTime = iterationTime
            if iterationTime > longestTime:
                longestTime = iterationTime
            totalTime += iterationTime
            iterations += 1
            print(f"iterations={iterations} span={span} i={i} best_cross={nr_cross_best}",
                  f"current_cross={nr_cross_new}", "time=%0.2f seconds" % iterationTime)
            if nr_cross_new < nr_cross_best:
                people = new_people[:]
                nr_cross_best = nr_cross_new
            if nr_cross_best == 0:
                break
        span = int(span / 2)
    write_files(header + people + links + spouses + families, dot)
