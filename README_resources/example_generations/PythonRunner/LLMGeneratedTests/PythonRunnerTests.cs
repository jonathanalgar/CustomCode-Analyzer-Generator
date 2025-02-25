using System;
using MyCompany.ExternalLibraries.PythonIntegration;
using Xunit;

namespace MyCompany.ExternalLibraries.Tests
{
    public class PythonRunnerTests
    {
        [Fact]
        public void ExecutePythonProgram_WithSimplePrint_ReturnsOutput()
        {
            // Arrange: create an instance of PythonRunner
            IPythonRunner runner = new PythonRunner();
            // Python code that prints a simple message
            string code = "print('Hello from IronPython')";

            // Act: execute the Python code
            string output = runner.ExecutePythonProgram(code);

            // Assert: verify that the output contains the expected message
            Assert.Contains("Hello from IronPython", output);
        }

        [Fact]
        public void ExecutePythonProgram_WithNoOutput_ReturnsEmptyString()
        {
            // Arrange: create an instance of PythonRunner
            IPythonRunner runner = new PythonRunner();
            // Python code that does not produce any output
            string code = "a = 10";

            // Act: execute the Python code
            string output = runner.ExecutePythonProgram(code);

            // Assert: output should be empty when nothing is printed
            Assert.True(string.IsNullOrEmpty(output) || string.IsNullOrWhiteSpace(output));
        }

        [Fact]
        public void ExecutePythonProgram_WithNullInput_ThrowsArgumentNullException()
        {
            // Arrange: create an instance of PythonRunner
            IPythonRunner runner = new PythonRunner();

            // Act & Assert: passing a null input should throw ArgumentNullException
            Assert.Throws<ArgumentNullException>(() => runner.ExecutePythonProgram(null));
        }
    }
}
