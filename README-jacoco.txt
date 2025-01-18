# Download distribution here or run via ivy as specified below
https://www.jacoco.org/jacoco/

# Can also simply run via ivy which means we don't have to handle download and checksum validation:
java -jar tools/ivy-2.5.2.jar -cache ivy-cache -dependency org.jacoco org.jacoco.cli 0.8.12 -cachepath tmp_cachepath.txt
java -cp `cat tmp_cachepath.txt` org.jacoco.cli.internal.Main

# Documentation of agent and cli usage:
https://www.jacoco.org/jacoco/trunk/doc/agent.html
https://www.jacoco.org/jacoco/trunk/doc/cli.html

1. Run program with agent to produce 'jacoco.exec' file(s).
2. Use CLI to produce coverage report 

JaCoCo Java agent options:
destfile := Path to the output file for execution data
append   := Append to existing destfile or create new
includes := List of class names to include in analysis
excludes := List of class names to exclude in analysis
output   := file (other options: are tcpserver, tcpclient, none)

java -javaagent:[yourpath/]jacocoagent.jar=[option1]=[value1],[option2]=[value2]
java -javaagent:~/mopt/jacoco-0.8.12/lib/jacocoagent.jar=output=file <junit cli runner> <test class>

java\
  -javaagent:~/mopt/jacoco-0.8.12/lib/jacocoagent.jar=output=file\
  -jar junit-platform-console-standalone-<version>.jar\
  <options>

# Generate report from 'jacoco.exec' file
java -jar ~/mopt/jacoco-0.8.12/lib/jacococli.jar\
  report target/jacoco.exec\
  --html ./report\
  --sourcefiles src/main/java\
  --classfiles target/classes

java -jar ~/mopt/jacoco-0.8.12/lib/jacococli.jar report target/jacoco.exec --html ./report --sourcefiles src/main/java --classfiles target/classes

