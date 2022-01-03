#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import textwrap

parallel = False
rows, columns = os.popen('stty size', 'r').read().split()
rows = int(rows)
columns = int(columns) - 4
colors = False

def help():
    print("\n    ".join(textwrap.wrap("usage: python3 ./automator [-help] [-parallel] [-config] [-<variables>]", columns)))
    print()
    print("====Defined parameters====")
    print("\n    ".join(textwrap.wrap("-help: print the help (this screen) and exit.", columns)))
    print("\n    ".join(textwrap.wrap("-config: the config file in which are described the programs to run and the options to run them (explained below). The default configuration file is \"config.json\".", columns)))
    print("\n    ".join(textwrap.wrap("-parallel: run the different programs described in the config file in parallel.", columns)))
    print("\n    ".join(textwrap.wrap("-color: color the output differently for each program.", columns)))
    print("\n    ".join(textwrap.wrap("The -help, -parallel and -color are the only parameters that do not expect values.", columns)))
    print()
    print("====Configuration file====")
    print("\n    ".join(textwrap.wrap("The configuration file is composed of a JSON list containing dictionaries with currently 3 keys:", columns)))
    print("\n        ".join(textwrap.wrap("        - binary: The location of the binary to run.", columns)))
    print("\n        ".join(textwrap.wrap("        - arguments: The arguments to provide to the binary.", columns)))
    print("\n        ".join(textwrap.wrap("        - output: The desired file in which you the output of the binary.", columns)))
    print()
    print("====Variable====")
    print("\n    ".join(textwrap.wrap("The arguments of the configuration file can be composed of variables which are wroten using a $ sign like so: \"$foo\".", columns)))
    print("\n    ".join(textwrap.wrap("The variable name will be substituted to its content before running the binary.", columns)))
    print("\n    ".join(textwrap.wrap("The variables and their values are defined like so: \"-foo bar\" or \"-foo=bar\".", columns)))

def parse_arguments():
    equal = re.compile('=')
    variables = {}
    arguments = enumerate(sys.argv[1:])
    for i, elt in arguments:
        if elt[0] == '-':
            if elt == "-help":
                help()
                exit(0)
            if elt == "-parallel":
                global parallel
                parallel = True
                continue
            if elt == "-color":
                global colors
                colors = True
                continue
            if equal.search(elt):
                variable = elt.split('=')
                variables[variable[0][1:]] = variable[1]
            else:
                try:
                    variables[elt[1:]] = next(arguments)[1]
                except StopIteration:
                    break
        else:
            print("Error while parsing arguments")
            exit(1)
    return variables

def eval_arguments(configs, variables):
    dollar = re.compile('\$[^ ]*')
    for program in configs:
        if not "arguments" in program:
            continue
        argument_location = dollar.search(program["arguments"])
        while argument_location:
            try:
                program["arguments"] = program["arguments"].replace(argument_location.group(), variables[argument_location.group()[1:]], 1)
                argument_location = dollar.search(program["arguments"])
            except KeyError:
                print(f"\"{argument_location.group()[1:]}\" not found in the arguments.")
                exit(1)

def run(configs):
    print(f"Run in parallel: {parallel}")
    i = 31
    for program in configs:
        command = [program["binary"]]
        if "arguments" in program:
            command += program["arguments"].split(" ")
        if not "output" in program:
            if colors:
                print("\033[{}m{}\033[0m".format(i, ' '.join(command)))
                i += 1
            else:
                print(' '.join(command))
        else:
            print(' '.join(command))
        if "output" in program:
            with open(program["output"], "w") as output:
                output.write(f'> {" ".join(command)}\n\n')
                process = subprocess.Popen(command, stdout=output)
        else:
            process = subprocess.Popen(command, stdout=subprocess.PIPE)
        if not parallel:
            # print output
            process.wait()
            if not "output" in program:
                if colors:
                    i -= 1
                    print("\033[{}m{}\033[0m".format(i, process.stdout.read().decode()))
                    i += 1
                else:
                    print(process.stdout.read().decode())
        else:
            program["process"] = process

variables = parse_arguments()

config_source = "./config.json"
if ("config" in  variables):
    config_source = variables["config"]
try:
    with open(config_source, "r") as config_file:
        raw_configs = config_file.read()
except FileNotFoundError:
    print("Config file not found, using default one.")
    try:
        with open("/opt/automator/config.json", "r") as config_file:
            raw_configs = config_file.read()
    except FileNotFoundError:
        print("Default config file not found, exiting.")
        exit(1)

configs = json.loads(raw_configs)

eval_arguments(configs, variables)

run(configs)

if parallel:
    # add poll of output in variable and print with color

    new_configs = configs
    while len(new_configs) > 0:
        i = 31
        new_configs = []
        for program in configs:
            if "output" in program:
                continue
            out = (b"".join(program["process"].stdout.readlines(1024))).decode()
            if colors:
                print(f"\033[{i}m{out}\033[0m", end='')
            else:
                print(out, end='')
            if program["process"].poll() is None:
                new_configs.append(program)
            i += 1
