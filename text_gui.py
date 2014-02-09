#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from webify import Player

if sys.version_info[:2] >= (3,0):
    _inpfn = input
else:
    _inpfn = raw_input

def read(prompt):
    return _inpfn(prompt).strip().lower()

def print_results(res, tr=70):
    fmt = "{id:>5} {t:<"+str(tr)+"} {s}"
    for i, r in enumerate(res):
        title = r.title[:tr] if len(r.title)>tr else r.title
        src   = r.source.name
        print(fmt.format(id=i, t=title,s=src))

if __name__ == "__main__":

    p = Player()

    cmds = {
            "/" : lambda x: p.search(" ".join(x)),
            "n" : lambda x: p.search_change_page(incr= int(x[0]) if len(x)>0 else  1),
            "p" : lambda x: p.search_change_page(incr=-int(x[0]) if len(x)>0 else -1),
            "q" : lambda x: sys.exit(0)
            }

    rets = {
            "/" : print_results,
            "n" : print_results,
            "p" : print_results,
            }
   
    print("Webify")

    while True:
        try:
            inp = read("> ")
        except (EOFError, KeyboardInterrupt) as e:
            sys.exit(1)

        if inp == "":
            continue

        cmdline = inp.split()
        cmd = cmdline[0]
        args = cmdline[1:]

        if cmd in cmds.keys():
            ret = cmds[cmd](args)
            if ret:
                if cmd in rets:
                    rets[cmd](ret)
                else:
                    print("Unhandled return value!")
                    print(ret)
        else:
            print("Unknown command: "+cmd)
