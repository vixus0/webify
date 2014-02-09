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

if __name__ == "__main__":

    p = Player()

    cmds = {
            "/":        lambda x: p.search(" ".join(x)),
            "n":        lambda x: p.search_change_page(incr= int(x[0]) if len(x)>0 else  1),
            "p":        lambda x: p.search_change_page(incr=-int(x[0]) if len(x)>0 else -1),
            "exit":     lambda x: sys.exit(0)
            }

    rets = {
            "/":        print_results,
            "n":        print_results,
            "p":        print_results,
            }
   
    print("Webify")

    while True:
        try:
            inp = read("> ")
        except (EOFError, KeyboardInterrupt) as e:
            sys.exit(1)

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
