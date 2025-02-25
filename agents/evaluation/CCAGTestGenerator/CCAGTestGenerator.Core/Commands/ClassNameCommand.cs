using CCAGTestGenerator.Core.Parsers;

namespace CCAGTestGenerator.Core.Commands
{
    /// <summary>
    /// The command handler for the <c>--classname</c> flag, which extracts and prints the derived class name
    /// from a specified C# source file decorated with <c>[OSInterface]</c>.
    /// </summary>
    public static class ClassNameCommand
    {
        /// <summary>
        /// Executes the <c>--classname</c> command by parsing the source file to retrieve the interface
        /// and class information, then writes the resulting class name to the console.
        /// </summary>
        /// <param name="args">CLI arguments</param>
        public static async Task Execute(string[] args)
        {
            // Expected usage: --classname <source-file>
            if (args.Length != 2)
            {
                Console.WriteLine("Usage: CCAGTestGenerator --classname <source-file>");
                return;
            }

            string sourceFilePath = args[1];
            string sourceCode = await File.ReadAllTextAsync(sourceFilePath);
            var libInfo = LibraryParser.ParseLibrary(sourceCode);
            Console.WriteLine(libInfo.ClassName);
        }
    }
}
