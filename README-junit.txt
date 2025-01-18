# JUnit 5
https://mvnrepository.com/artifact/org.junit.platform/junit-platform-console-standalone

java -jar junit-platform-console-standalone-<version>.jar <options>

*** The vintage engine is included in junit-platform-console-standalone

# JUnit 5 Vintage (Run JUnit 3 and 4 test in JUnit 5 platform.)
https://mvnrepository.com/artifact/org.junit.vintage/junit-vintage-engine

# JUnit 4 (Try Junit 5 Vintage Engine before using this.)

java -cp junit.jar org.junit.runner.JUnitCore <test class>

# JUnit 3 (Try JUnit 5 Vintage Engine before using this.)

java -cp junit.jar junit.textui.TestRunner <test class>

