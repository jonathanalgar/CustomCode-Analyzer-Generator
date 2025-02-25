using CCAGTestGenerator.Core.Parsers;

namespace CCAGTestGenerator.Core.Commands
{
    /// <summary>
    /// The command handler for <c>--report</c>, which analyzes a source file
    /// and YAML without generating tests. Shows information such as method name,
    /// parameters, and YAML test specification details.
    /// </summary>
    public static class ReportCommand
    {
        /// <summary>
        /// Executes the report command, parsing the library and YAML to present a summary
        /// of the method name, parameters, and YAML action/params.
        /// </summary>
        /// <param name="args">CLI arguments</param>
        public static async Task Execute(string[] args)
        {
            if (args.Length != 3)
            {
                Console.WriteLine(
                    "Usage: CCAGTestGenerator --report <source-file> <test-cases-yaml>"
                );
                return;
            }

            string sourceFilePath = args[1];
            string yamlFilePath = args[2];

            string sourceCode = await File.ReadAllTextAsync(sourceFilePath);
            string yamlContent = await File.ReadAllTextAsync(yamlFilePath);

            // Parse the library info and the YAML action parameters.
            var libInfo = LibraryParser.ParseLibrary(sourceCode);
            var (yamlActionName, yamlParams) = TestCaseParser.ParseYamlActionParams(yamlContent);

            Console.WriteLine($"C# method name: {libInfo.MethodName}");
            Console.WriteLine("C# parameters:");
            foreach (var (pName, pType) in libInfo.Parameters)
            {
                Console.WriteLine($"  - {pName} ({pType})");
            }
            Console.WriteLine();
            Console.WriteLine($"YAML method name: {yamlActionName}");
            Console.WriteLine("YAML parameters:");
            foreach (var param in yamlParams)
            {
                Console.WriteLine($"  - {param}");
            }
        }
    }
}
