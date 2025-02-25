using System;
using System.IO;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using OutSystems.ExternalLibraries.SDK;

namespace MyCompany.ExternalLibraries.PythonIntegration
{
    // Expose this interface to OutSystems as an external library
    [OSInterface(
        Name = "PythonRunner",
        Description = "Executes Python code using IronPython",
        IconResourceName = "PythonRunner.icon.png"
    )]
    public interface IPythonRunner
    {
        // Expose this method as an OutSystems Server Action
        [OSAction(
            Description = "Executes the given Python code and returns the standard output",
            ReturnName = "PythonOutput",
            ReturnDescription = "The stdout produced from executing the Python code",
            ReturnType = OSDataType.Text
        )]
        string ExecutePythonProgram(
            [OSParameter(Description = "The Python code to execute", DataType = OSDataType.Text)]
                string code
        );
    }

    public class PythonRunner : IPythonRunner
    {
        // This method executes the provided Python code and returns its stdout as a string.
        public string ExecutePythonProgram(string code)
        {
            if (code == null) // Ensure the input is not null
            {
                throw new ArgumentNullException(nameof(code));
            }

            // Create a new IronPython engine instance
            ScriptEngine engine = Python.CreateEngine();

            // Setup a MemoryStream to capture the stdout output
            MemoryStream outputStream = new MemoryStream();
            // Use a StreamWriter to write to the MemoryStream; AutoFlush ensures immediate writing
            StreamWriter writer = new StreamWriter(outputStream) { AutoFlush = true };
            // Redirect the engine's output to our MemoryStream
            engine.Runtime.IO.SetOutput(outputStream, writer);

            // Execute the provided Python code
            engine.Execute(code);

            // Reset the stream position to the beginning
            outputStream.Seek(0, SeekOrigin.Begin);
            // Read the captured output from the MemoryStream
            using (StreamReader reader = new StreamReader(outputStream))
            {
                string result = reader.ReadToEnd();
                return result;
            }
        }
    }
}
