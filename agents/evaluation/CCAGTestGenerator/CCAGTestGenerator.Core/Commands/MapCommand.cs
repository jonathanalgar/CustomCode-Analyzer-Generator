using CCAGTestGenerator.Core.Parsers;

namespace CCAGTestGenerator.Core.Commands
{
    /// <summary>
    /// The command handler for the <c>--map</c> flag. Reports how many OSAction
    /// methods are present in the interface, and how many parameters each method has.
    /// </summary>
    public static class MapCommand
    {
        public static async Task Execute(string[] args)
        {
            /// <summary>
            /// Executes the map command, printing the action parameter counts
            /// in a format like <c>1(4)</c> meaning 1 method with 4 parameters.
            /// </summary>
            /// <param name="args">CLI arguments</param>
            if (args.Length != 2)
            {
                Console.WriteLine("Usage: CCAGTestGenerator --map <source-file>");
                return;
            }

            string sourceFilePath = args[1];
            string sourceCode = await File.ReadAllTextAsync(sourceFilePath);

            string map = LibraryMapper.GetActionParamMap(sourceCode);
            Console.WriteLine(map);
        }
    }
}
