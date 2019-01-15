#!/usr/bin/python3
#
# Peter Hewett, Filipe Correia
# Copyright GPL 2012 - 2019
# edited: 10 March 2014
# edited: V0.4 18th August 2014, Maurice Snell:
#	Made Windows compatible, not restested on *nix but should still work.
#	Increased & clarified output messages
#	Fixed bug with writing output when user cancels optimisation.
# edited: 15 Jan 2019 PWH: converted to python3
#
# reorder Gramps dot file to minimise crossings in relationship chart
# usage:
#    create a relationship graph in Gramps to produce .gv file
#    copy .gv file and this .py file to the same directory
#    in that directory, run
#      $./GrampsCrossing.py yourfile.gv
#    output is now more verbose:
#        iterations, span, index, nr_cross_best, nr_cross_new, iteration time
#    it takes several minutes, depending on file size
#    it doesn't alter your .gv file
#    it leaves optimised files as gcf1.dot and gcf1.pdf
#    ctrl c stops iterations and dumps current gcf1.dot and gcf1.pdf
#
import math
import subprocess
import sys
import signal
import time
import os

dot_markup = ""


def signal_handler(thesignal, frame):
    print('Ctrl+C pressed! Writing files and aborting...')
    write_files(dot_markup)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# read the dot file and parse into parts
def parse():
    with open(sys.argv[1], 'r') as f:
        src = f.readlines()
    f.close()

    # find end of header section
    for i, l in enumerate(src):
        if 'node ' in l:
            p1 = i + 2
            break

    # parse input file
    dot_header = src[0:p1]
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
def crossings(df, output_files=False):
    if output_files:
        print("Generating output DOT.")
        cmd = 'dot -v -Tpdf > gcf1.pdf'
        f = open('gcf1.dot', 'w')
        f.write(''.join(df))
        f.close()
        print("Generating output PDF.")
    else:
        cmd = 'dot -v -Tpdf > ' + os.devnull  # silent, now more portable including Windows

    result = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
        result.stdin.write(''.join(df).encode())
        result.stdin.close()
    except IOError as e:
        print("Exception raised in subprocess call")
        print(e)
        print(''.join(list(result.stderr)))

    for l in result.stderr:
        if 'crossings' in l.decode():
            break
    line = l.decode()
    p1 = line.find(':')
    p2 = line.find('crossings')
    if not output_files:
        # On Windows this was causing memory issues by leaving multiple instances hanging.
        result.terminate()
    return int(line[p1 + 1:p2 - 1])


def write_files(dot_markup):
    crossings(dot_markup, output_files=True)
    print("Crossings reduced from", nr_cross_original, "to", nr_cross_best,
          "runtime=%0.3f seconds" % (time.time() - startTime), "iterations=%d" % iterations)
    print("Average iteration time=%0.3f seconds" % (totalTime / iterations),
          "longest iteration time=%0.3f seconds" % longestTime, "shortest iteration time=%0.3f seconds" % shortestTime)


if __name__ == "__main__":
    startTime = time.time()
    header, people, families, spouses, links = parse()

    nsize = len(people)
    span = int(2 ** int(math.log(nsize - 1) / math.log(2)))

    new_people = []
    nr_cross_best = crossings(header + people + links + spouses + families)
    print("people=" + str(nsize), "initial span=" + str(span), "initial crossings =" + str(nr_cross_best))
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
            nr_cross_new = crossings(dot_markup)
            iterationTime = time.time() - iterationsStartTime
            if iterationTime < shortestTime:
                shortestTime = iterationTime
            if iterationTime > longestTime:
                longestTime = iterationTime
            totalTime += iterationTime
            iterations += 1
            print("iterations=%d span=%d i=%d nr_cross_best=%d nr_cross_new=%d time=%0.3fs" % (
            iterations, span, i, nr_cross_best, nr_cross_new, iterationTime))
            if nr_cross_new < nr_cross_best:
                people = new_people[:]
                nr_cross_best = nr_cross_new
            if nr_cross_best == 0:
                break
        span = int(span / 2)
    write_files(header + people + links + spouses + families)
