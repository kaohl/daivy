#!/bin/env python3

import os
from pathlib import Path
import subprocess
import tempfile

# Generate 'jacoco.exec'
#java -javaagent:jacoco-0.8.12/lib/jacocoagent.jar=output=file -jar junit-5/junit-platform-console-standalone-1.11.4.jar --class-path target/classes:target/test-classes --select-class org.jacop.ExampleBasedTest

# Generate report/*
#java -jar ~/mopt/jacoco-0.8.12/lib/jacococli.jar report jacoco.exec --html ./report-2 --sourcefiles src/main/java --classfiles target/classes

def resolve_path_relative_cwd(path):
    cwd  = Path(os.getcwd())
    path = Path(path)

    if not (cwd.is_absolute() and path.is_absolute()):
        raise ValueError("Path is not absolute:", str(path))

    tmp = cwd
    res = None
    i   = 0
    while len(tmp.parts) > 0:
        try:
            res = path.relative_to(tmp)
            break
        except:
            tmp = tmp.parent
            i   = i + 1
    return ('../'*i) + str(res)

def resolve_jar(coord):
    paths = resolve_classpath(coord, ["master"])
    print("--- Paths ---")
    for p in paths:
        print("Path", p)
    print("-"*13)
    return paths

def resolve_classpath(coord, confs = ["default"]):
    classpath = []
    DAIVY_HOME = os.environ['DAIVY_HOME']
    with tempfile.TemporaryDirectory(dir = Path(os.getcwd()) / 'temp') as tempdir:
        with tempfile.NamedTemporaryFile(delete_on_close=False, dir = tempdir) as classpath_file:
            classpath_file.close()
            cmd = " ".join([
                '${DAIVY_HOME}/ivy_cache_resolver.py',
                '-m',
                coord,
                '--classpath',
                '--classpath-file',
                classpath_file.name,
                '--confs',
                ",".join(confs)
            ])
            subprocess.run(
                cmd,
                shell      = True,
                executable = '/bin/bash',
                cwd        = DAIVY_HOME
            )

            with open(classpath_file.name, 'r') as cpf:
                classpath.extend(cpf.readlines())
    return classpath

# Generalize test coverage report generation.
def coverage(project, context_folder, jacoco_options, junit_options):
    # All source projects have the same layout so we should
    # only need the project ID and a context folder for
    # building. And also jacoco and junit options.
    #
    # Use <context>/jacoco.exec as destfile
    # Use <context>/report as report folder
    pass

def _main():

    # Example to be executed from top-level of JaCoP source distribution.

    jacoco_agent     = "org.jacoco:org.jacoco.agent:0.8.12"
    jacoco_cli       = "org.jacoco:org.jacoco.cli:0.8.12"
    junit_standalone = "org.junit.platform:junit-platform-console-standalone:1.11.4"

    # JaCoCo jars from ivy are not primed with executable manifests.
    #agent_jar = resolve_jar("org.jacoco:org.jacoco.agent:0.8.12")[0]
    #cli_jar   = resolve_jar("org.jacoco:org.jacoco.cli:0.8.12")[0]
    agent_jar = "tools/jacoco-0.8.12/lib/jacocoagent.jar"
    cli_jar   = "tools/jacoco-0.8.12/lib/jacococli.jar"
    junit_jar = resolve_jar(junit_standalone)[0]
    
    print("Agent", agent_jar)
    print("Cli  ", cli_jar)
    print("JUnit", junit_jar)

    # Run tests with jacocoagent to get 'jacoco.exec'.

    destfile = "jacoco.exec"
    output   = "report"

    jacoco_options = [
        "output=file",
        "destfile=" + destfile
    ]
    junit_options = [
        "--class-path",
        "target/classes:target/test-classes",
        "--select-class",
        "org.jacop.ExampleBasedTest"
    ]    
    cmd = " ".join([
        "java",
        "-javaagent:" + agent_jar + "=" + ",".join(jacoco_options),
        "-jar",
        junit_jar,
    ]) + " " + " ".join(junit_options)
    subprocess.run(
        cmd,
        shell      = True,
        executable = '/bin/bash'
    )

    # Generate report using jacococli.

    cmd_jacoco_cli = " ".join([
        "java",
        "-jar",
        cli_jar,
        "report",
        destfile,
        "--html",
        output,
        "--sourcefiles",
        "src/main/java",
        "--classfiles",
        "target/classes",
    ])
    subprocess.run(
        cmd_jacoco_cli,
        shell      = True,
        executable = '/bin/bash'
    )

if __name__ == '__main__':
    _main()

