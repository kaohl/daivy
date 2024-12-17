# Download distribution here or run via ivy as specified below(EclEmma seems to be an eclipse plugin).
https://www.jacoco.org/jacoco/

# Can also simply run via ivy which means we don't have to handle download and checksum validation:
java -jar tools/ivy-2.5.2.jar -cache ivy-cache -dependency org.jacoco org.jacoco.cli 0.8.12 -cachepath tmp_cachepath.txt
java -cp `cat tmp_cachepath.txt` org.jacoco.cli.internal.Main

# Documentation of cli usage:
https://www.jacoco.org/jacoco/trunk/doc/cli.html

